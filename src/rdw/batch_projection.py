from __future__ import annotations

from pathlib import Path

from rdw.batch_events import EventWriter, replay_batch_events
from rdw.batch_models import (
    EXECUTOR_TASK_STATES,
    BatchExecutionPolicy,
    BatchExecutionResult,
    BatchExecutorState,
    BatchTaskProjection,
    ExecutorTaskState,
)
from rdw.batch_support import (
    batch_id,
    batch_state,
    bool_value,
    executor_mapping,
    int_value,
    now_iso,
    optional_string,
    refresh_summary_counts,
    set_optional_row_value,
    task_rows,
    task_state,
    write_summary,
    write_task_executor_state,
)
from rdw.lifecycle import load_task_status_view
from rdw.yaml_io import YamlMapping


def apply_event_projection(batch_dir: Path, summary: YamlMapping) -> None:
    projection = replay_batch_events(batch_dir)
    if projection.batch_state == "idle" and not projection.tasks:
        return
    executor = executor_mapping(summary)
    if projection.batch_state != "idle":
        executor["state"] = projection.batch_state
    for row in task_rows(summary):
        task_id = str(row.get("task_id") or "")
        task = projection.tasks.get(task_id)
        if task is None:
            continue
        row["executor_state"] = task.state
        row["attempts"] = task.attempts
        set_optional_row_value(row, "attempt_id", task.attempt_id)
        set_optional_row_value(row, "last_error", task.last_error)
        set_optional_row_value(row, "receipt_path", task.receipt_path)
        set_optional_row_value(row, "next_retry_at", task.next_retry_at)
        set_optional_row_value(row, "failure_category", task.failure_category)
        set_optional_row_value(row, "adapter_status", task.adapter_status)
        row["retryable"] = task.retryable
        write_task_executor_state(
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
    refresh_summary_counts(summary)
    write_summary(batch_dir, summary)


def initialize_executor(
    batch_dir: Path,
    summary: YamlMapping,
    policy: BatchExecutionPolicy,
) -> None:
    executor = summary.get("executor")
    if not isinstance(executor, dict):
        executor = {
            "state": "idle",
            "policy": policy.as_dict(),
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        summary["executor"] = executor
    else:
        executor.setdefault("policy", policy.as_dict())
        executor.setdefault("state", "idle")
    for row in task_rows(summary):
        task_id = str(row.get("task_id") or "")
        status = load_task_status_view(batch_dir / "tasks" / task_id).status
        current = row.get("executor_state")
        if not isinstance(current, str) or current not in EXECUTOR_TASK_STATES:
            current = "succeeded" if status == "final-done" else "queued"
            row["executor_state"] = current
            row["attempts"] = int_value(row.get("attempts"), 0)
            write_task_executor_state(
                batch_dir / "tasks" / task_id,
                task_state(current, default="queued"),
                attempts=int_value(row.get("attempts"), 0),
            )
    refresh_summary_counts(summary)
    write_summary(batch_dir, summary)


def record_batch_state(
    summary: YamlMapping,
    state: BatchExecutorState,
    writer: EventWriter,
    *,
    reason: str | None = None,
    lease_id: str | None = None,
    policy: YamlMapping | None = None,
) -> None:
    executor = executor_mapping(summary)
    fields: dict[str, object] = {"state": state}
    if reason:
        fields["reason"] = reason
    if lease_id:
        fields["lease_id"] = lease_id
    writer.append("batch-state", **fields)
    executor["state"] = state
    executor["updated_at"] = now_iso()
    if reason:
        executor["reason"] = reason
    if lease_id:
        executor["lease_id"] = lease_id
    if policy is not None:
        executor["policy"] = policy
    refresh_summary_counts(summary)
    write_summary(writer.batch_dir, summary)


def record_task_state(
    batch_dir: Path,
    summary: YamlMapping,
    row: YamlMapping,
    state: ExecutorTaskState,
    writer: EventWriter,
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
    attempts = attempt_number if attempt_number is not None else int_value(row.get("attempts"), 0)
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
        "retryable": (
            retryable if retryable is not None else bool_value(row.get("retryable"), False)
        ),
    }
    writer.append("task-state", **fields)
    row["executor_state"] = state
    row["attempts"] = attempts
    set_optional_row_value(row, "attempt_id", attempt_id)
    set_optional_row_value(row, "receipt_path", receipt_path)
    set_optional_row_value(row, "next_retry_at", next_retry_at)
    set_optional_row_value(row, "adapter_status", adapter_status)
    set_optional_row_value(row, "last_error", last_error)
    set_optional_row_value(row, "failure_category", failure_category)
    row["retryable"] = fields["retryable"] if isinstance(fields["retryable"], bool) else False
    write_task_executor_state(
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
    refresh_summary_counts(summary)
    write_summary(batch_dir, summary)


def resume_paused_tasks(batch_dir: Path, summary: YamlMapping, writer: EventWriter) -> None:
    for row in task_rows(summary):
        if task_state(row.get("executor_state"), default="queued") == "paused":
            record_task_state(batch_dir, summary, row, "queued", writer)


def pause_queued_tasks(batch_dir: Path, summary: YamlMapping, writer: EventWriter) -> None:
    for row in task_rows(summary):
        if task_state(row.get("executor_state"), default="queued") == "queued":
            record_task_state(batch_dir, summary, row, "paused", writer)


def cancel_queued_tasks(batch_dir: Path, summary: YamlMapping, writer: EventWriter) -> None:
    for row in task_rows(summary):
        if task_state(row.get("executor_state"), default="queued") in {
            "queued",
            "paused",
            "retry-wait",
        }:
            record_task_state(batch_dir, summary, row, "cancelled", writer)
    record_batch_state(summary, "cancelled", writer, reason="cancel reached safe boundary")


def finalize_batch(summary: YamlMapping, writer: EventWriter) -> None:
    state = batch_state(executor_mapping(summary).get("state"), default="running")
    if state in {"paused", "cancelled", "recovery-required", "completed-with-failures"}:
        write_summary(writer.batch_dir, summary)
        return
    rows = task_rows(summary)
    states = [task_state(row.get("executor_state"), default="queued") for row in rows]
    if any(task_executor_state == "reconcile-required" for task_executor_state in states):
        record_batch_state(
            summary, "recovery-required", writer, reason="unknown attempt requires reconciliation"
        )
    elif any(task_executor_state in {"failed", "needs-review"} for task_executor_state in states):
        record_batch_state(
            summary,
            "completed-with-failures",
            writer,
            reason="tasks require review or failed",
        )
    elif any(task_executor_state == "cancelled" for task_executor_state in states):
        record_batch_state(summary, "cancelled", writer, reason="tasks cancelled")
    elif rows and all(task_executor_state == "succeeded" for task_executor_state in states):
        record_batch_state(summary, "completed", writer, reason="all tasks completed")
    else:
        record_batch_state(summary, "completed-with-failures", writer, reason="tasks remain queued")


def result_from_summary(
    summary: YamlMapping,
    batch_dir: Path,
    *,
    dry_run: bool = False,
) -> BatchExecutionResult:
    executor = summary.get("executor")
    executor_mapping_value = executor if isinstance(executor, dict) else {}
    state = batch_state(executor_mapping_value.get("state"), default="idle")
    tasks: list[BatchTaskProjection] = []
    for row in task_rows(summary):
        task_id = str(row.get("task_id") or "")
        task_executor_state = task_state(
            row.get("executor_state"),
            default="succeeded" if str(row.get("status") or "") == "final-done" else "queued",
        )
        tasks.append(
            BatchTaskProjection(
                task_id=task_id,
                state=task_executor_state,
                attempts=int_value(row.get("attempts"), 0),
                attempt_id=optional_string(row.get("attempt_id")),
                last_error=optional_string(row.get("last_error")),
                receipt_path=optional_string(row.get("receipt_path")),
                next_retry_at=optional_string(row.get("next_retry_at")),
                retryable=bool_value(row.get("retryable"), False),
                failure_category=optional_string(row.get("failure_category")),
                adapter_status=optional_string(row.get("adapter_status")),
            )
        )
    completed = sum(task.state == "succeeded" for task in tasks)
    needs_review = sum(task.state == "needs-review" for task in tasks)
    failed = sum(task.state == "failed" for task in tasks)
    cancelled = sum(task.state == "cancelled" for task in tasks)
    return BatchExecutionResult(
        batch_id=batch_id(summary, batch_dir),
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
