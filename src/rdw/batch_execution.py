from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, cast

from rdw.execution import ExecutionResult, execute_fixture
from rdw.io import append_jsonl, atomic_write_text
from rdw.lifecycle import load_task_status_view
from rdw.yaml_io import YamlMapping, YamlValue, dump_yaml, load_yaml_mapping

ExecutorTaskState = Literal[
    "queued",
    "leased",
    "running",
    "succeeded",
    "retry-wait",
    "needs-review",
    "failed",
    "cancelled",
    "reconcile-required",
    "paused",
]
BatchExecutorState = Literal[
    "idle",
    "running",
    "pause-requested",
    "paused",
    "cancel-requested",
    "cancelled",
    "completed",
    "completed-with-failures",
    "recovery-required",
]
FailurePolicy = Literal["continue", "stop"]

EXECUTOR_TASK_STATES = frozenset(
    {
        "queued",
        "leased",
        "running",
        "succeeded",
        "retry-wait",
        "needs-review",
        "failed",
        "cancelled",
        "reconcile-required",
        "paused",
    }
)
EXECUTOR_BATCH_STATES = frozenset(
    {
        "idle",
        "running",
        "pause-requested",
        "paused",
        "cancel-requested",
        "cancelled",
        "completed",
        "completed-with-failures",
        "recovery-required",
    }
)
RETRYABLE_FAILURE_CATEGORIES = frozenset({"rate_limited", "network", "provider"})
TERMINAL_EXECUTOR_TASK_STATES = frozenset({"succeeded", "cancelled", "reconcile-required"})


class BatchLeaseConflictError(ValueError):
    """Raised when another executor lease is still live."""


@dataclass(frozen=True)
class BatchExecutionPolicy:
    max_concurrency: int = 1
    max_attempts: int = 2
    retry_backoff_seconds: tuple[int, ...] = (5, 30)
    task_timeout_seconds: int = 900
    batch_timeout_seconds: int = 3600
    max_tasks: int = 100
    max_total_attempts: int = 100
    failure_policy: FailurePolicy = "continue"

    def __post_init__(self) -> None:
        if self.max_concurrency != 1:
            raise ValueError("serial batch executor requires max_concurrency: 1")
        if not 1 <= self.max_attempts <= 3:
            raise ValueError("max_attempts must be between 1 and 3")
        if any(seconds < 0 for seconds in self.retry_backoff_seconds) or (
            self.max_attempts > 1 and not self.retry_backoff_seconds
        ):
            raise ValueError("retry_backoff_seconds must contain non-negative values")
        if self.task_timeout_seconds <= 0:
            raise ValueError("task_timeout_seconds must be positive")
        if self.batch_timeout_seconds <= 0:
            raise ValueError("batch_timeout_seconds must be positive")
        if not 1 <= self.max_tasks <= 100:
            raise ValueError("max_tasks must be between 1 and 100")
        if not 1 <= self.max_total_attempts <= 100:
            raise ValueError("max_total_attempts must be between 1 and 100")
        if self.failure_policy not in {"continue", "stop"}:
            raise ValueError("failure_policy must be continue or stop")

    @classmethod
    def from_mapping(cls, value: YamlValue | None) -> BatchExecutionPolicy:
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise ValueError("execution policy must be a mapping")
        max_concurrency = _policy_int(value.get("max_concurrency"), "max_concurrency", 1)
        max_attempts = _policy_int(value.get("max_attempts"), "max_attempts", 2)
        retry_backoff = value.get("retry_backoff_seconds")
        if retry_backoff is None:
            backoff = (5, 30)
        elif isinstance(retry_backoff, list) and all(
            isinstance(item, int) and not isinstance(item, bool) for item in retry_backoff
        ):
            backoff = tuple(cast(int, item) for item in retry_backoff)
        else:
            raise ValueError("retry_backoff_seconds must be a list of integers")
        failure_policy_value = value.get("failure_policy", "continue")
        if failure_policy_value not in {"continue", "stop"}:
            raise ValueError("failure_policy must be continue or stop")
        return cls(
            max_concurrency=max_concurrency,
            max_attempts=max_attempts,
            retry_backoff_seconds=backoff,
            task_timeout_seconds=_policy_int(
                value.get("task_timeout_seconds"), "task_timeout_seconds", 900
            ),
            batch_timeout_seconds=_policy_int(
                value.get("batch_timeout_seconds"), "batch_timeout_seconds", 3600
            ),
            max_tasks=_policy_int(value.get("max_tasks"), "max_tasks", 100),
            max_total_attempts=_policy_int(
                value.get("max_total_attempts"), "max_total_attempts", 100
            ),
            failure_policy=cast(FailurePolicy, failure_policy_value),
        )

    def as_dict(self) -> YamlMapping:
        return {
            "max_concurrency": self.max_concurrency,
            "max_attempts": self.max_attempts,
            "retry_backoff_seconds": list(self.retry_backoff_seconds),
            "task_timeout_seconds": self.task_timeout_seconds,
            "batch_timeout_seconds": self.batch_timeout_seconds,
            "max_tasks": self.max_tasks,
            "max_total_attempts": self.max_total_attempts,
            "failure_policy": self.failure_policy,
        }


@dataclass(frozen=True)
class FixtureBatchPlan:
    batch_id: str
    fixtures: dict[str, Path]
    policy: BatchExecutionPolicy


@dataclass(frozen=True)
class BatchTaskProjection:
    task_id: str
    state: ExecutorTaskState
    attempts: int = 0
    attempt_id: str | None = None
    last_error: str | None = None
    receipt_path: str | None = None
    next_retry_at: str | None = None
    retryable: bool = False
    failure_category: str | None = None
    adapter_status: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "state": self.state,
            "attempts": self.attempts,
            "attempt_id": self.attempt_id,
            "last_error": self.last_error,
            "receipt_path": self.receipt_path,
            "next_retry_at": self.next_retry_at,
            "retryable": self.retryable,
            "failure_category": self.failure_category,
            "adapter_status": self.adapter_status,
        }


@dataclass(frozen=True)
class BatchEventProjection:
    batch_state: BatchExecutorState
    tasks: dict[str, BatchTaskProjection]
    applied_event_ids: tuple[str, ...]
    duplicate_event_ids: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "batch_state": self.batch_state,
            "tasks": {task_id: task.as_dict() for task_id, task in self.tasks.items()},
            "applied_event_ids": list(self.applied_event_ids),
            "duplicate_event_ids": list(self.duplicate_event_ids),
        }


@dataclass(frozen=True)
class BatchExecutionResult:
    batch_id: str
    state: BatchExecutorState
    task_count: int
    completed: int
    needs_review: int
    failed: int
    cancelled: int
    total_attempts: int
    tasks: tuple[BatchTaskProjection, ...]
    dry_run: bool = False
    recovery_required: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "batch_id": self.batch_id,
            "state": self.state,
            "task_count": self.task_count,
            "completed": self.completed,
            "needs_review": self.needs_review,
            "failed": self.failed,
            "cancelled": self.cancelled,
            "total_attempts": self.total_attempts,
            "tasks": [task.as_dict() for task in self.tasks],
            "dry_run": self.dry_run,
            "recovery_required": self.recovery_required,
        }


@dataclass(frozen=True)
class _BatchLease:
    lease_id: str
    batch_id: str
    acquired_at: str
    expires_at: str


@dataclass
class _EventWriter:
    batch_dir: Path
    batch_id: str
    operation_id: str
    sequence: int = 0

    def append(self, event_type: str, **fields: object) -> dict[str, object]:
        self.sequence += 1
        payload: dict[str, object] = {
            "at": _now_iso(),
            "batch_id": self.batch_id,
            "event_type": event_type,
            "operation_id": self.operation_id,
            "sequence": self.sequence,
            **fields,
        }
        payload["event_id"] = _event_id(payload)
        append_jsonl(self.batch_dir / "batch-log.jsonl", payload)
        return payload


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


def replay_batch_events(batch_dir: Path) -> BatchEventProjection:
    records = _read_event_records(batch_dir)
    batch_state: BatchExecutorState = "idle"
    tasks: dict[str, BatchTaskProjection] = {}
    applied: list[str] = []
    duplicates: list[str] = []
    seen: set[str] = set()
    for record in records:
        event_id = str(record["event_id"])
        if event_id in seen:
            duplicates.append(event_id)
            continue
        seen.add(event_id)
        applied.append(event_id)
        event_type = str(record.get("event_type") or "")
        if event_type == "batch-state":
            batch_state = _batch_state(record.get("state"), default=batch_state)
        elif event_type == "task-state":
            task_id = str(record.get("task_id") or "")
            if not task_id:
                continue
            previous = tasks.get(task_id)
            state = _task_state(record.get("state"), default="queued")
            attempts = max(
                previous.attempts if previous else 0,
                _int_value(record.get("attempt_number"), 0),
            )
            tasks[task_id] = BatchTaskProjection(
                task_id=task_id,
                state=state,
                attempts=attempts,
                attempt_id=_event_optional(
                    record, "attempt_id", previous.attempt_id if previous else None
                ),
                last_error=_event_optional(
                    record, "last_error", previous.last_error if previous else None
                ),
                receipt_path=_event_optional(
                    record, "receipt_path", previous.receipt_path if previous else None
                ),
                next_retry_at=_event_optional(
                    record, "next_retry_at", previous.next_retry_at if previous else None
                ),
                retryable=_bool_value(
                    record.get("retryable"), previous.retryable if previous else False
                ),
                failure_category=_event_optional(
                    record, "failure_category", previous.failure_category if previous else None
                ),
                adapter_status=_event_optional(
                    record, "adapter_status", previous.adapter_status if previous else None
                ),
            )
    return BatchEventProjection(
        batch_state=batch_state,
        tasks=tasks,
        applied_event_ids=tuple(applied),
        duplicate_event_ids=tuple(duplicates),
    )


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
        task_state = _task_state(row.get("executor_state"), default="queued")
        if task_state in TERMINAL_EXECUTOR_TASK_STATES:
            continue
        if task_state == "needs-review" and not resume:
            continue
        if task_state == "failed" and (not resume or not _bool_value(row.get("retryable"), False)):
            continue
        if task_state == "paused":
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


def _finalize_batch(summary: YamlMapping, writer: _EventWriter) -> None:
    state = _batch_state(_executor_mapping(summary).get("state"), default="running")
    if state in {"paused", "cancelled", "recovery-required", "completed-with-failures"}:
        _write_summary(writer.batch_dir, summary)
        return
    rows = _task_rows(summary)
    states = [_task_state(row.get("executor_state"), default="queued") for row in rows]
    if any(task_state == "reconcile-required" for task_state in states):
        _record_batch_state(
            summary, "recovery-required", writer, reason="unknown attempt requires reconciliation"
        )
    elif any(task_state in {"failed", "needs-review"} for task_state in states):
        _record_batch_state(
            summary, "completed-with-failures", writer, reason="tasks require review or failed"
        )
    elif any(task_state == "cancelled" for task_state in states):
        _record_batch_state(summary, "cancelled", writer, reason="tasks cancelled")
    elif rows and all(task_state == "succeeded" for task_state in states):
        _record_batch_state(summary, "completed", writer, reason="all tasks completed")
    else:
        _record_batch_state(
            summary, "completed-with-failures", writer, reason="tasks remain queued"
        )


def _apply_event_projection(batch_dir: Path, summary: YamlMapping) -> None:
    projection = replay_batch_events(batch_dir)
    if projection.batch_state == "idle" and not projection.tasks:
        return
    executor = _executor_mapping(summary)
    if projection.batch_state != "idle":
        executor["state"] = projection.batch_state
    for row in _task_rows(summary):
        task_id = str(row.get("task_id") or "")
        task = projection.tasks.get(task_id)
        if task is None:
            continue
        row["executor_state"] = task.state
        row["attempts"] = task.attempts
        _set_optional_row_value(row, "attempt_id", task.attempt_id)
        _set_optional_row_value(row, "last_error", task.last_error)
        _set_optional_row_value(row, "receipt_path", task.receipt_path)
        _set_optional_row_value(row, "next_retry_at", task.next_retry_at)
        _set_optional_row_value(row, "failure_category", task.failure_category)
        _set_optional_row_value(row, "adapter_status", task.adapter_status)
        row["retryable"] = task.retryable
        _write_task_executor_state(
            batch_dir / "tasks" / task_id,
            task.state,
            attempts=task.attempts,
            attempt_id=task.attempt_id,
            receipt_path=task.receipt_path,
            next_retry_at=task.next_retry_at,
            adapter_status=task.adapter_status,
            last_error=task.last_error,
            failure_category=task.failure_category,
            retryable=task.retryable,
        )
    _refresh_summary_counts(summary)
    _write_summary(batch_dir, summary)


def _initialize_executor(
    batch_dir: Path,
    summary: YamlMapping,
    policy: BatchExecutionPolicy,
) -> None:
    executor = summary.get("executor")
    if not isinstance(executor, dict):
        executor = {
            "state": "idle",
            "policy": policy.as_dict(),
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        summary["executor"] = executor
    else:
        executor.setdefault("policy", policy.as_dict())
        executor.setdefault("state", "idle")
    for row in _task_rows(summary):
        task_id = str(row.get("task_id") or "")
        status = load_task_status_view(batch_dir / "tasks" / task_id).status
        current = row.get("executor_state")
        if not isinstance(current, str) or current not in EXECUTOR_TASK_STATES:
            current = "succeeded" if status == "final-done" else "queued"
            row["executor_state"] = current
            row["attempts"] = _int_value(row.get("attempts"), 0)
            _write_task_executor_state(
                batch_dir / "tasks" / task_id,
                cast(ExecutorTaskState, current),
                attempts=_int_value(row.get("attempts"), 0),
            )
    _refresh_summary_counts(summary)
    _write_summary(batch_dir, summary)


def _record_batch_state(
    summary: YamlMapping,
    state: BatchExecutorState,
    writer: _EventWriter,
    *,
    reason: str | None = None,
    lease_id: str | None = None,
    policy: YamlMapping | None = None,
) -> None:
    executor = _executor_mapping(summary)
    fields: dict[str, object] = {"state": state}
    if reason:
        fields["reason"] = reason
    if lease_id:
        fields["lease_id"] = lease_id
    writer.append("batch-state", **fields)
    executor["state"] = state
    executor["updated_at"] = _now_iso()
    if reason:
        executor["reason"] = reason
    if lease_id:
        executor["lease_id"] = lease_id
    if policy is not None:
        executor["policy"] = policy
    _refresh_summary_counts(summary)
    _write_summary(writer.batch_dir, summary)


def _record_task_state(
    batch_dir: Path,
    summary: YamlMapping,
    row: YamlMapping,
    state: ExecutorTaskState,
    writer: _EventWriter,
    *,
    attempt_id: str | None = None,
    attempt_number: int | None = None,
    receipt_path: str | None = None,
    next_retry_at: str | None = None,
    adapter_status: str | None = None,
    last_error: str | None = None,
    failure_category: str | None = None,
    retryable: bool | None = None,
) -> None:
    task_id = str(row.get("task_id") or "")
    attempts = attempt_number if attempt_number is not None else _int_value(row.get("attempts"), 0)
    fields: dict[str, object] = {
        "task_id": task_id,
        "state": state,
        "attempt_id": attempt_id,
        "attempt_number": attempts,
        "receipt_path": receipt_path,
        "next_retry_at": next_retry_at,
        "adapter_status": adapter_status,
        "last_error": last_error,
        "failure_category": failure_category,
        "retryable": retryable
        if retryable is not None
        else _bool_value(row.get("retryable"), False),
    }
    writer.append("task-state", **fields)
    row["executor_state"] = state
    row["attempts"] = attempts
    _set_optional_row_value(row, "attempt_id", attempt_id)
    _set_optional_row_value(row, "receipt_path", receipt_path)
    _set_optional_row_value(row, "next_retry_at", next_retry_at)
    _set_optional_row_value(row, "adapter_status", adapter_status)
    _set_optional_row_value(row, "last_error", last_error)
    _set_optional_row_value(row, "failure_category", failure_category)
    row["retryable"] = fields["retryable"] if isinstance(fields["retryable"], bool) else False
    _write_task_executor_state(
        batch_dir / "tasks" / task_id,
        state,
        attempts=attempts,
        attempt_id=attempt_id,
        receipt_path=receipt_path,
        next_retry_at=next_retry_at,
        adapter_status=adapter_status,
        last_error=last_error,
        failure_category=failure_category,
        retryable=bool(row["retryable"]),
    )
    _refresh_summary_counts(summary)
    _write_summary(batch_dir, summary)


def _resume_paused_tasks(batch_dir: Path, summary: YamlMapping, writer: _EventWriter) -> None:
    for row in _task_rows(summary):
        if _task_state(row.get("executor_state"), default="queued") == "paused":
            _record_task_state(batch_dir, summary, row, "queued", writer)


def _pause_queued_tasks(batch_dir: Path, summary: YamlMapping, writer: _EventWriter) -> None:
    for row in _task_rows(summary):
        if _task_state(row.get("executor_state"), default="queued") == "queued":
            _record_task_state(batch_dir, summary, row, "paused", writer)


def _cancel_queued_tasks(batch_dir: Path, summary: YamlMapping, writer: _EventWriter) -> None:
    for row in _task_rows(summary):
        if _task_state(row.get("executor_state"), default="queued") in {
            "queued",
            "paused",
            "retry-wait",
        }:
            _record_task_state(batch_dir, summary, row, "cancelled", writer)
    _record_batch_state(summary, "cancelled", writer, reason="cancel reached safe boundary")


def _mark_unknown_attempts(batch_dir: Path, batch_id: str) -> bool:
    summary = _load_summary(batch_dir)
    writer = _EventWriter(batch_dir, batch_id, f"reclaim-{uuid.uuid4().hex}")
    found = False
    for row in _task_rows(summary):
        task_id = str(row.get("task_id") or "")
        status_details = _task_executor_details(batch_dir / "tasks" / task_id)
        state_value = row.get("executor_state")
        if not isinstance(state_value, str):
            state_value = status_details.get("state")
        state = _task_state(state_value, default="queued")
        attempt_id = _optional_string(row.get("attempt_id")) or _optional_string(
            status_details.get("attempt_id")
        )
        if state in {"leased", "running", "retry-wait"} and attempt_id:
            found = True
            _record_task_state(
                batch_dir,
                summary,
                row,
                "reconcile-required",
                writer,
                attempt_id=attempt_id,
                attempt_number=_int_value(
                    row.get("attempts"), _int_value(status_details.get("attempts"), 0)
                ),
                receipt_path=_optional_string(row.get("receipt_path"))
                or _optional_string(status_details.get("receipt_path")),
                last_error="attempt outcome is unknown; inspect the immutable receipt before retrying",
                failure_category="unknown_attempt",
                retryable=False,
            )
    if found:
        _record_batch_state(
            summary,
            "recovery-required",
            writer,
            reason="unknown attempt requires explicit reconciliation",
        )
    return found


def _task_executor_details(task_dir: Path) -> dict[str, object]:
    status_path = task_dir / "status.json"
    if not status_path.is_file():
        return {}
    status = _load_json_mapping(status_path)
    executor = status.get("executor")
    return dict(executor) if isinstance(executor, dict) else {}


def _acquire_lease(batch_dir: Path, batch_id: str, *, reclaim: bool) -> tuple[_BatchLease, bool]:
    lease_path = batch_dir / "executor-lease.json"
    unknown_attempts = False
    if lease_path.exists():
        existing = _load_json_mapping(lease_path)
        expires_at = _parse_iso(_optional_string(existing.get("expires_at")))
        if expires_at is None:
            raise ValueError(f"invalid executor lease: {lease_path}")
        if expires_at > datetime.now(UTC):
            raise BatchLeaseConflictError(
                f"batch executor lease is active until {existing.get('expires_at')}; wait or use a separate batch"
            )
        if not reclaim:
            raise BatchLeaseConflictError(
                "batch executor lease is expired; pass --reclaim-lease to recover explicitly"
            )
        unknown_attempts = _mark_unknown_attempts(batch_dir, batch_id)
        lease_path.unlink()

    acquired_at = _now_iso()
    expires_at = (datetime.now(UTC) + timedelta(seconds=300)).replace(microsecond=0)
    lease = _BatchLease(
        lease_id=f"lease-{uuid.uuid4().hex}",
        batch_id=batch_id,
        acquired_at=acquired_at,
        expires_at=expires_at.isoformat().replace("+00:00", "Z"),
    )
    payload = {
        "lease_id": lease.lease_id,
        "batch_id": lease.batch_id,
        "pid": os.getpid(),
        "acquired_at": lease.acquired_at,
        "expires_at": lease.expires_at,
    }
    try:
        file_descriptor = os.open(lease_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise BatchLeaseConflictError("batch executor lease was acquired concurrently") from exc
    return lease, unknown_attempts


def _release_lease(batch_dir: Path, lease: _BatchLease) -> None:
    lease_path = batch_dir / "executor-lease.json"
    if not lease_path.exists():
        return
    current = _load_json_mapping(lease_path)
    if str(current.get("lease_id") or "") == lease.lease_id:
        lease_path.unlink()


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


def _result_from_summary(
    summary: YamlMapping,
    batch_dir: Path,
    *,
    dry_run: bool = False,
) -> BatchExecutionResult:
    executor = summary.get("executor")
    executor_mapping = executor if isinstance(executor, dict) else {}
    state = _batch_state(executor_mapping.get("state"), default="idle")
    tasks: list[BatchTaskProjection] = []
    for row in _task_rows(summary):
        task_id = str(row.get("task_id") or "")
        task_state = _task_state(
            row.get("executor_state"),
            default="succeeded" if str(row.get("status") or "") == "final-done" else "queued",
        )
        tasks.append(
            BatchTaskProjection(
                task_id=task_id,
                state=task_state,
                attempts=_int_value(row.get("attempts"), 0),
                attempt_id=_optional_string(row.get("attempt_id")),
                last_error=_optional_string(row.get("last_error")),
                receipt_path=_optional_string(row.get("receipt_path")),
                next_retry_at=_optional_string(row.get("next_retry_at")),
                retryable=_bool_value(row.get("retryable"), False),
                failure_category=_optional_string(row.get("failure_category")),
                adapter_status=_optional_string(row.get("adapter_status")),
            )
        )
    completed = sum(task.state == "succeeded" for task in tasks)
    needs_review = sum(task.state == "needs-review" for task in tasks)
    failed = sum(task.state == "failed" for task in tasks)
    cancelled = sum(task.state == "cancelled" for task in tasks)
    return BatchExecutionResult(
        batch_id=_batch_id(summary, batch_dir),
        state=state,
        task_count=len(tasks),
        completed=completed,
        needs_review=needs_review,
        failed=failed,
        cancelled=cancelled,
        total_attempts=sum(task.attempts for task in tasks),
        tasks=tuple(tasks),
        dry_run=dry_run,
        recovery_required=state == "recovery-required"
        or any(task.state == "reconcile-required" for task in tasks),
    )


def _refresh_summary_counts(summary: YamlMapping) -> None:
    rows = _task_rows(summary)
    completed = 0
    needs_review = 0
    failed = 0
    cancelled = 0
    pending = 0
    reconcile_required = 0
    for row in rows:
        state = _task_state(row.get("executor_state"), default="queued")
        if state == "succeeded":
            completed += 1
        elif state == "needs-review":
            needs_review += 1
        elif state == "failed":
            failed += 1
        elif state == "cancelled":
            cancelled += 1
        elif state == "reconcile-required":
            reconcile_required += 1
        else:
            pending += 1
    summary["task_count"] = len(rows)
    summary["completed"] = completed
    summary["needs_review"] = needs_review
    summary["failed"] = failed
    summary["cancelled"] = cancelled
    summary["pending"] = pending
    summary["reconcile_required"] = reconcile_required
    executor = summary.get("executor")
    if isinstance(executor, dict):
        executor["total_attempts"] = _total_attempts(summary)
        executor["updated_at"] = _now_iso()


def _total_attempts(summary: YamlMapping) -> int:
    return sum(_int_value(row.get("attempts"), 0) for row in _task_rows(summary))


def _write_summary(batch_dir: Path, summary: YamlMapping) -> None:
    atomic_write_text(batch_dir / "summary.yaml", dump_yaml(summary))


def _write_task_executor_state(
    task_dir: Path,
    state: ExecutorTaskState,
    *,
    attempts: int,
    attempt_id: str | None = None,
    receipt_path: str | None = None,
    next_retry_at: str | None = None,
    adapter_status: str | None = None,
    last_error: str | None = None,
    failure_category: str | None = None,
    retryable: bool = False,
) -> None:
    status_path = task_dir / "status.json"
    status = _load_json_mapping(status_path)
    executor = status.get("executor")
    executor_mapping: dict[str, object] = dict(executor) if isinstance(executor, dict) else {}
    executor_mapping.update(
        {
            "state": state,
            "attempts": attempts,
            "updated_at": _now_iso(),
            "retryable": retryable,
        }
    )
    _set_optional_object(executor_mapping, "attempt_id", attempt_id)
    _set_optional_object(executor_mapping, "receipt_path", receipt_path)
    _set_optional_object(executor_mapping, "next_retry_at", next_retry_at)
    _set_optional_object(executor_mapping, "adapter_status", adapter_status)
    _set_optional_object(executor_mapping, "last_error", last_error)
    _set_optional_object(executor_mapping, "failure_category", failure_category)
    status["executor"] = executor_mapping
    atomic_write_text(status_path, json.dumps(status, indent=2) + "\n")


def _load_summary(batch_dir: Path) -> YamlMapping:
    summary_path = batch_dir / "summary.yaml"
    if not summary_path.is_file():
        raise ValueError(f"not a planned batch run: {batch_dir} (missing summary.yaml)")
    return load_yaml_mapping(summary_path)


def _task_rows(summary: YamlMapping) -> list[YamlMapping]:
    tasks = summary.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("batch summary tasks must be a list")
    rows = [item for item in tasks if isinstance(item, dict)]
    if len(rows) != len(tasks):
        raise ValueError("batch summary tasks must contain mappings")
    return rows


def _task_ids(summary: YamlMapping) -> list[str]:
    ids = [str(row.get("task_id") or "") for row in _task_rows(summary)]
    if any(not task_id for task_id in ids):
        raise ValueError("batch summary contains a task without task_id")
    return ids


def _executor_mapping(summary: YamlMapping) -> dict[str, YamlValue]:
    executor = summary.get("executor")
    if not isinstance(executor, dict):
        executor = {}
        summary["executor"] = executor
    return executor


def _batch_id(summary: YamlMapping, batch_dir: Path) -> str:
    return str(summary.get("batch_id") or batch_dir.name)


def _read_event_records(batch_dir: Path) -> list[dict[str, object]]:
    log_path = batch_dir / "batch-log.jsonl"
    if not log_path.is_file():
        return []
    records: list[dict[str, object]] = []
    for line_number, line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            loaded: object = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid batch event JSON at line {line_number}: {log_path}") from exc
        if not isinstance(loaded, dict):
            raise ValueError(f"batch event must be a mapping at line {line_number}: {log_path}")
        record: dict[str, object] = {str(key): value for key, value in loaded.items()}
        event_id = record.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            event_id = f"legacy-{hashlib.sha256(line.strip().encode('utf-8')).hexdigest()}"
            record["event_id"] = event_id
        records.append(record)
    return records


def _event_id(payload: dict[str, object]) -> str:
    identity = {key: value for key, value in payload.items() if key != "at"}
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return f"evt-{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def _task_state(value: object, *, default: ExecutorTaskState) -> ExecutorTaskState:
    if isinstance(value, str) and value in EXECUTOR_TASK_STATES:
        return cast(ExecutorTaskState, value)
    return default


def _batch_state(value: object, *, default: BatchExecutorState) -> BatchExecutorState:
    if isinstance(value, str) and value in EXECUTOR_BATCH_STATES:
        return cast(BatchExecutorState, value)
    return default


def _backoff_for_attempt(policy: BatchExecutionPolicy, attempt_number: int) -> int:
    index = min(max(attempt_number - 1, 0), len(policy.retry_backoff_seconds) - 1)
    return policy.retry_backoff_seconds[index]


def _set_optional_row_value(row: YamlMapping, key: str, value: str | None) -> None:
    if value is None:
        row.pop(key, None)
    else:
        row[key] = value


def _set_optional_object(mapping: dict[str, object], key: str, value: object | None) -> None:
    if value is None:
        mapping.pop(key, None)
    else:
        mapping[key] = value


def _load_json_mapping(path: Path) -> dict[str, object]:
    try:
        loaded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON mapping: {path}") from exc
    if not isinstance(loaded, dict):
        raise ValueError(f"JSON root must be a mapping: {path}")
    return {str(key): value for key, value in loaded.items()}


def _required_string(mapping: YamlMapping, key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing or empty field: {key}")
    return value


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _event_optional(record: dict[str, object], key: str, previous: str | None) -> str | None:
    if key in record:
        return _optional_string(record.get(key))
    return previous


def _bool_value(value: object, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _int_value(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return default


def _policy_int(value: YamlValue | None, key: str, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _future_iso(seconds: int) -> str:
    return (
        (datetime.now(UTC) + timedelta(seconds=seconds))
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
