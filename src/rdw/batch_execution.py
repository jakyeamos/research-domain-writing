from __future__ import annotations

import time
import uuid
from pathlib import Path

from rdw.batch_events import EventWriter as _EventWriter
from rdw.batch_events import replay_batch_events as replay_batch_events
from rdw.batch_leases import acquire_lease as _acquire_lease
from rdw.batch_leases import mark_unknown_attempts as _mark_unknown_attempts
from rdw.batch_leases import release_lease as _release_lease
from rdw.batch_models import (
    EXECUTOR_BATCH_STATES as EXECUTOR_BATCH_STATES,
)
from rdw.batch_models import (
    EXECUTOR_TASK_STATES as EXECUTOR_TASK_STATES,
)
from rdw.batch_models import (
    RETRYABLE_FAILURE_CATEGORIES as RETRYABLE_FAILURE_CATEGORIES,
)
from rdw.batch_models import (
    TERMINAL_EXECUTOR_TASK_STATES as TERMINAL_EXECUTOR_TASK_STATES,
)
from rdw.batch_models import (
    BatchEventProjection as BatchEventProjection,
)
from rdw.batch_models import (
    BatchExecutionPolicy as BatchExecutionPolicy,
)
from rdw.batch_models import (
    BatchExecutionResult as BatchExecutionResult,
)
from rdw.batch_models import (
    BatchExecutorState as BatchExecutorState,
)
from rdw.batch_models import (
    BatchLease as _BatchLease,
)
from rdw.batch_models import (
    BatchLeaseConflictError as BatchLeaseConflictError,
)
from rdw.batch_models import (
    BatchTaskProjection as BatchTaskProjection,
)
from rdw.batch_models import (
    ExecutorTaskState as ExecutorTaskState,
)
from rdw.batch_models import (
    FailurePolicy as FailurePolicy,
)
from rdw.batch_models import (
    FixtureBatchPlan as FixtureBatchPlan,
)
from rdw.batch_projection import apply_event_projection as _apply_event_projection
from rdw.batch_projection import cancel_queued_tasks as _cancel_queued_tasks
from rdw.batch_projection import finalize_batch as _finalize_batch
from rdw.batch_projection import initialize_executor as _initialize_executor
from rdw.batch_projection import pause_queued_tasks as _pause_queued_tasks
from rdw.batch_projection import record_batch_state as _record_batch_state
from rdw.batch_projection import record_task_state as _record_task_state
from rdw.batch_projection import result_from_summary as _result_from_summary
from rdw.batch_projection import resume_paused_tasks as _resume_paused_tasks
from rdw.batch_support import backoff_for_attempt as _backoff_for_attempt
from rdw.batch_support import batch_id as _batch_id
from rdw.batch_support import batch_state as _batch_state
from rdw.batch_support import bool_value as _bool_value
from rdw.batch_support import executor_mapping as _executor_mapping
from rdw.batch_support import future_iso as _future_iso
from rdw.batch_support import int_value as _int_value
from rdw.batch_support import load_json_mapping as _load_json_mapping
from rdw.batch_support import load_summary as _load_summary
from rdw.batch_support import optional_string as _optional_string
from rdw.batch_support import required_string as _required_string
from rdw.batch_support import task_ids as _task_ids
from rdw.batch_support import task_rows as _task_rows
from rdw.batch_support import task_state as _task_state
from rdw.batch_support import total_attempts as _total_attempts
from rdw.batch_support import write_summary as _write_summary
from rdw.execution import ExecutionResult, execute_fixture
from rdw.lifecycle import load_task_status_view
from rdw.yaml_io import load_yaml_mapping

__all__ = [
    "BatchEventProjection",
    "BatchExecutionPolicy",
    "BatchExecutionResult",
    "BatchExecutorState",
    "BatchLeaseConflictError",
    "BatchTaskProjection",
    "ExecutorTaskState",
    "FailurePolicy",
    "FixtureBatchPlan",
    "EXECUTOR_BATCH_STATES",
    "EXECUTOR_TASK_STATES",
    "RETRYABLE_FAILURE_CATEGORIES",
    "TERMINAL_EXECUTOR_TASK_STATES",
    "execute_batch",
    "load_fixture_batch_plan",
    "replay_batch_events",
    "request_batch_cancel",
    "request_batch_pause",
]


def load_fixture_batch_plan(
    fixture_map_path: Path,
    batch_dir: Path,
    *,
    policy: BatchExecutionPolicy | None = None,
) -> FixtureBatchPlan:
    fixture_map_path = fixture_map_path.resolve()
    if not fixture_map_path.is_file():
        raise ValueError(f"fixture map not found: {fixture_map_path}")
    summary = _load_summary(batch_dir)
    fixture_map = load_yaml_mapping(fixture_map_path)
    batch_id = _required_string(fixture_map, "batch_id")
    expected_batch_id = str(summary.get("batch_id") or batch_dir.name)
    if batch_id != expected_batch_id:
        raise ValueError(
            f"fixture map batch_id does not match batch: {batch_id} != {expected_batch_id}"
        )
    raw_fixtures = fixture_map.get("fixtures")
    if not isinstance(raw_fixtures, dict):
        raise ValueError("fixture map fixtures must be a mapping")
    task_ids = _task_ids(summary)
    unknown = sorted(set(str(key) for key in raw_fixtures) - set(task_ids))
    missing = sorted(set(task_ids) - set(str(key) for key in raw_fixtures))
    if unknown:
        raise ValueError(f"fixture map contains unknown task ids: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"fixture map is missing task ids: {', '.join(missing)}")
    fixtures: dict[str, Path] = {}
    for task_id in task_ids:
        reference = raw_fixtures.get(task_id)
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError(f"fixture map path must be a non-empty string: {task_id}")
        fixture_path = Path(reference)
        if not fixture_path.is_absolute():
            fixture_path = fixture_map_path.parent / fixture_path
        fixture_path = fixture_path.resolve()
        if not fixture_path.is_file():
            raise ValueError(f"fixture not found for {task_id}: {fixture_path}")
        fixtures[task_id] = fixture_path
    configured_policy = policy
    if configured_policy is None:
        configured_policy = BatchExecutionPolicy.from_mapping(
            fixture_map.get("execution", fixture_map.get("policy"))
        )
    return FixtureBatchPlan(batch_id=batch_id, fixtures=fixtures, policy=configured_policy)


def execute_batch(
    batch_dir: Path,
    fixture_map_path: Path,
    *,
    root: Path | None = None,
    resume: bool = False,
    reclaim_lease: bool = False,
    dry_run: bool = False,
    policy: BatchExecutionPolicy | None = None,
) -> BatchExecutionResult:
    batch_dir = batch_dir.resolve()
    summary = _load_summary(batch_dir)
    plan = load_fixture_batch_plan(fixture_map_path, batch_dir, policy=policy)
    if len(plan.fixtures) > plan.policy.max_tasks:
        raise ValueError(
            f"batch has {len(plan.fixtures)} tasks but max_tasks is {plan.policy.max_tasks}"
        )
    if dry_run:
        return _result_from_summary(summary, batch_dir, dry_run=True)

    lease, unknown_attempts = _acquire_lease(
        batch_dir,
        plan.batch_id,
        reclaim=reclaim_lease,
    )
    try:
        summary = _load_summary(batch_dir)
        _apply_event_projection(batch_dir, summary)
        _initialize_executor(batch_dir, summary, plan.policy)
        if unknown_attempts:
            return _result_from_summary(summary, batch_dir)
        if _mark_unknown_attempts(batch_dir, plan.batch_id):
            return _result_from_summary(_load_summary(batch_dir), batch_dir)
        return _run_batch(
            batch_dir,
            plan,
            root=(root or fixture_map_path.parent).resolve(),
            resume=resume,
            lease=lease,
        )
    finally:
        _release_lease(batch_dir, lease)


def request_batch_pause(batch_dir: Path) -> BatchExecutionResult:
    batch_dir = batch_dir.resolve()
    summary = _load_summary(batch_dir)
    _apply_event_projection(batch_dir, summary)
    _initialize_executor(batch_dir, summary, BatchExecutionPolicy())
    executor = _executor_mapping(summary)
    state = _batch_state(executor.get("state"), default="idle")
    if state in {"cancelled", "completed", "completed-with-failures"}:
        raise ValueError(f"cannot pause terminal batch state: {state}")
    writer = _EventWriter(batch_dir, _batch_id(summary, batch_dir), f"pause-{uuid.uuid4().hex}")
    target_state: BatchExecutorState = (
        "paused" if state in {"idle", "paused"} else "pause-requested"
    )
    _record_batch_state(summary, target_state, writer, reason="pause requested")
    if target_state == "paused":
        for row in _task_rows(summary):
            if _task_state(row.get("executor_state"), default="queued") == "queued":
                _record_task_state(batch_dir, summary, row, "paused", writer)
        _write_summary(batch_dir, summary)
    return _result_from_summary(summary, batch_dir)


def request_batch_cancel(batch_dir: Path) -> BatchExecutionResult:
    batch_dir = batch_dir.resolve()
    summary = _load_summary(batch_dir)
    _apply_event_projection(batch_dir, summary)
    _initialize_executor(batch_dir, summary, BatchExecutionPolicy())
    executor = _executor_mapping(summary)
    state = _batch_state(executor.get("state"), default="idle")
    if state in {"cancelled", "completed"}:
        raise ValueError(f"cannot cancel terminal batch state: {state}")
    writer = _EventWriter(batch_dir, _batch_id(summary, batch_dir), f"cancel-{uuid.uuid4().hex}")
    active = any(
        _task_state(row.get("executor_state"), default="queued") in {"leased", "running"}
        for row in _task_rows(summary)
    )
    target_state: BatchExecutorState = "cancel-requested" if active else "cancelled"
    _record_batch_state(summary, target_state, writer, reason="cancel requested")
    if not active:
        for row in _task_rows(summary):
            task_state = _task_state(row.get("executor_state"), default="queued")
            if task_state in {"queued", "paused", "retry-wait"}:
                _record_task_state(batch_dir, summary, row, "cancelled", writer)
        _record_batch_state(summary, "cancelled", writer, reason="cancel completed")
        _write_summary(batch_dir, summary)
    return _result_from_summary(summary, batch_dir)


def _run_batch(
    batch_dir: Path,
    plan: FixtureBatchPlan,
    *,
    root: Path,
    resume: bool,
    lease: _BatchLease,
) -> BatchExecutionResult:
    summary = _load_summary(batch_dir)
    writer = _EventWriter(batch_dir, plan.batch_id, f"execute-{uuid.uuid4().hex}")
    executor = _executor_mapping(summary)
    current_state = _batch_state(executor.get("state"), default="idle")
    if current_state in {"completed", "cancelled", "recovery-required"} and not resume:
        return _result_from_summary(summary, batch_dir)
    if current_state == "recovery-required":
        return _result_from_summary(summary, batch_dir)
    if current_state == "paused":
        if not resume:
            return _result_from_summary(summary, batch_dir)
        _resume_paused_tasks(batch_dir, summary, writer)
    elif current_state == "pause-requested":
        _record_batch_state(summary, "paused", writer, reason="pause reached safe boundary")
        _pause_queued_tasks(batch_dir, summary, writer)
        return _result_from_summary(summary, batch_dir)
    elif current_state == "cancel-requested":
        _cancel_queued_tasks(batch_dir, summary, writer)
        return _result_from_summary(summary, batch_dir)

    _record_batch_state(
        summary,
        "running",
        writer,
        lease_id=lease.lease_id,
        policy=plan.policy.as_dict(),
    )
    started = time.monotonic()
    for row in _task_rows(summary):
        control_state = _batch_state(_executor_mapping(summary).get("state"), default="running")
        if control_state in {"pause-requested", "paused"}:
            _record_batch_state(summary, "paused", writer, reason="pause reached safe boundary")
            _pause_queued_tasks(batch_dir, summary, writer)
            break
        if control_state in {"cancel-requested", "cancelled"}:
            _cancel_queued_tasks(batch_dir, summary, writer)
            break
        if time.monotonic() - started >= plan.policy.batch_timeout_seconds:
            _record_batch_state(summary, "completed-with-failures", writer, reason="batch timeout")
            break

        task_id = str(row.get("task_id") or "")
        task_executor_state = _task_state(row.get("executor_state"), default="queued")
        if task_executor_state in TERMINAL_EXECUTOR_TASK_STATES:
            continue
        if task_executor_state == "needs-review" and not resume:
            continue
        if task_executor_state == "failed" and (
            not resume or not _bool_value(row.get("retryable"), False)
        ):
            continue
        if task_executor_state == "paused":
            if not resume:
                continue
            _record_task_state(batch_dir, summary, row, "queued", writer)
        task_status = load_task_status_view(batch_dir / "tasks" / task_id).status
        if task_status == "final-done":
            _record_task_state(batch_dir, summary, row, "succeeded", writer)
            continue
        if task_status == "qa-failed" and not resume:
            _record_task_state(
                batch_dir,
                summary,
                row,
                "needs-review",
                writer,
                last_error="task is qa-failed; resume is required",
            )
            continue

        attempts = _int_value(row.get("attempts"), 0)
        while attempts < plan.policy.max_attempts:
            total_attempts = _total_attempts(summary)
            if total_attempts >= plan.policy.max_total_attempts:
                _record_task_state(
                    batch_dir,
                    summary,
                    row,
                    "failed",
                    writer,
                    last_error="max_total_attempts reached",
                    failure_category="executor",
                    retryable=False,
                )
                _record_batch_state(
                    summary,
                    "completed-with-failures",
                    writer,
                    reason="max_total_attempts reached",
                )
                break

            attempts += 1
            attempt_id = f"batch-{uuid.uuid4().hex}"
            _record_task_state(
                batch_dir,
                summary,
                row,
                "leased",
                writer,
                attempt_id=attempt_id,
                attempt_number=attempts,
            )
            _record_task_state(
                batch_dir,
                summary,
                row,
                "running",
                writer,
                attempt_id=attempt_id,
                attempt_number=attempts,
            )
            task_started = time.monotonic()
            try:
                result = execute_fixture(
                    batch_dir / "tasks" / task_id,
                    plan.fixtures[task_id],
                    root=root,
                    resume=resume or attempts > 1,
                    attempt_id=attempt_id,
                )
            except ValueError as exc:
                _record_task_state(
                    batch_dir,
                    summary,
                    row,
                    "failed",
                    writer,
                    attempt_id=attempt_id,
                    attempt_number=attempts,
                    last_error=str(exc),
                    failure_category="receipt_invalid",
                    retryable=False,
                )
                break
            except Exception as exc:
                _record_task_state(
                    batch_dir,
                    summary,
                    row,
                    "reconcile-required",
                    writer,
                    attempt_id=attempt_id,
                    attempt_number=attempts,
                    last_error=f"executor exception left attempt outcome unknown: {exc}",
                    failure_category="unknown_attempt",
                    retryable=False,
                )
                _record_batch_state(
                    summary,
                    "recovery-required",
                    writer,
                    reason="executor exception requires explicit attempt reconciliation",
                )
                break

            if time.monotonic() - task_started > plan.policy.task_timeout_seconds:
                _record_task_state(
                    batch_dir,
                    summary,
                    row,
                    "reconcile-required",
                    writer,
                    attempt_id=attempt_id,
                    attempt_number=attempts,
                    receipt_path=str(result.receipt_path) if result.receipt_path else None,
                    adapter_status=result.adapter_status,
                    last_error="task timeout exceeded; inspect the immutable receipt before retrying",
                    failure_category="timeout",
                    retryable=False,
                )
                _record_batch_state(
                    summary,
                    "recovery-required",
                    writer,
                    reason="task timeout requires explicit attempt reconciliation",
                )
                break

            failure = _receipt_failure(result)
            if result.adapter_status == "succeeded":
                _record_task_state(
                    batch_dir,
                    summary,
                    row,
                    "succeeded",
                    writer,
                    attempt_id=result.attempt_id,
                    attempt_number=attempts,
                    receipt_path=str(result.receipt_path) if result.receipt_path else None,
                    adapter_status=result.adapter_status,
                    retryable=False,
                )
                break
            if result.adapter_status == "incomplete":
                _record_task_state(
                    batch_dir,
                    summary,
                    row,
                    "needs-review",
                    writer,
                    attempt_id=result.attempt_id,
                    attempt_number=attempts,
                    receipt_path=str(result.receipt_path) if result.receipt_path else None,
                    adapter_status=result.adapter_status,
                    last_error="fixture outcome requires review",
                )
                break
            if result.adapter_status == "cancelled":
                _record_task_state(
                    batch_dir,
                    summary,
                    row,
                    "cancelled",
                    writer,
                    attempt_id=result.attempt_id,
                    attempt_number=attempts,
                    receipt_path=str(result.receipt_path) if result.receipt_path else None,
                    adapter_status=result.adapter_status,
                    last_error=failure[1],
                    failure_category=failure[0],
                    retryable=False,
                )
                _record_batch_state(summary, "cancelled", writer, reason="adapter cancelled task")
                break

            category, message, retryable = failure
            retryable = retryable and category in RETRYABLE_FAILURE_CATEGORIES
            if retryable and attempts < plan.policy.max_attempts:
                backoff = _backoff_for_attempt(plan.policy, attempts)
                _record_task_state(
                    batch_dir,
                    summary,
                    row,
                    "retry-wait",
                    writer,
                    attempt_id=result.attempt_id,
                    attempt_number=attempts,
                    receipt_path=str(result.receipt_path) if result.receipt_path else None,
                    adapter_status=result.adapter_status,
                    last_error=message,
                    failure_category=category,
                    retryable=True,
                    next_retry_at=_future_iso(backoff),
                )
                if backoff:
                    time.sleep(backoff)
                _record_task_state(
                    batch_dir,
                    summary,
                    row,
                    "queued",
                    writer,
                    attempt_id=result.attempt_id,
                    attempt_number=attempts,
                    last_error=message,
                    failure_category=category,
                    retryable=True,
                    next_retry_at=None,
                )
                if time.monotonic() - started >= plan.policy.batch_timeout_seconds:
                    _record_batch_state(
                        summary,
                        "completed-with-failures",
                        writer,
                        reason="batch timeout",
                    )
                    break
                continue
            _record_task_state(
                batch_dir,
                summary,
                row,
                "failed",
                writer,
                attempt_id=result.attempt_id,
                attempt_number=attempts,
                receipt_path=str(result.receipt_path) if result.receipt_path else None,
                adapter_status=result.adapter_status,
                last_error=message,
                failure_category=category,
                retryable=retryable,
            )
            if plan.policy.failure_policy == "stop":
                _record_batch_state(
                    summary,
                    "completed-with-failures",
                    writer,
                    reason="failure_policy=stop",
                )
            break

        if _batch_state(_executor_mapping(summary).get("state"), default="running") in {
            "completed-with-failures",
            "cancelled",
            "paused",
            "recovery-required",
        }:
            break

    _finalize_batch(summary, writer)
    return _result_from_summary(summary, batch_dir)


def _receipt_failure(result: ExecutionResult) -> tuple[str, str, bool]:
    if result.receipt_path is None or not result.receipt_path.is_file():
        return "receipt_missing", "adapter did not produce a receipt", False
    try:
        receipt = _load_json_mapping(result.receipt_path)
    except ValueError:
        return "receipt_invalid", "adapter receipt is not valid JSON", False
    failure = receipt.get("failure")
    if not isinstance(failure, dict):
        return "adapter_failure", f"fixture outcome: {result.adapter_status}", False
    category = _optional_string(failure.get("category")) or "adapter_failure"
    message = (
        _optional_string(failure.get("message")) or f"fixture outcome: {result.adapter_status}"
    )
    retryable = _bool_value(failure.get("retryable"), False)
    return category, message, retryable
