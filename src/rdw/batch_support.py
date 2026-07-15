from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from rdw.batch_models import (
    EXECUTOR_BATCH_STATES,
    EXECUTOR_TASK_STATES,
    BatchExecutionPolicy,
    BatchExecutorState,
    ExecutorTaskState,
)
from rdw.io import atomic_write_text
from rdw.yaml_io import YamlMapping, YamlValue, dump_yaml, load_yaml_mapping


def load_summary(batch_dir: Path) -> YamlMapping:
    summary_path = batch_dir / "summary.yaml"
    if not summary_path.is_file():
        raise ValueError(f"not a planned batch run: {batch_dir} (missing summary.yaml)")
    return load_yaml_mapping(summary_path)


def task_rows(summary: YamlMapping) -> list[YamlMapping]:
    tasks = summary.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("batch summary tasks must be a list")
    rows = [item for item in tasks if isinstance(item, dict)]
    if len(rows) != len(tasks):
        raise ValueError("batch summary tasks must contain mappings")
    return rows


def task_ids(summary: YamlMapping) -> list[str]:
    ids = [str(row.get("task_id") or "") for row in task_rows(summary)]
    if any(not task_id for task_id in ids):
        raise ValueError("batch summary contains a task without task_id")
    return ids


def executor_mapping(summary: YamlMapping) -> dict[str, YamlValue]:
    executor = summary.get("executor")
    if not isinstance(executor, dict):
        executor = {}
        summary["executor"] = executor
    return executor


def batch_id(summary: YamlMapping, batch_dir: Path) -> str:
    return str(summary.get("batch_id") or batch_dir.name)


def write_summary(batch_dir: Path, summary: YamlMapping) -> None:
    atomic_write_text(batch_dir / "summary.yaml", dump_yaml(summary))


def refresh_summary_counts(summary: YamlMapping) -> None:
    rows = task_rows(summary)
    completed = 0
    needs_review = 0
    failed = 0
    cancelled = 0
    pending = 0
    reconcile_required = 0
    for row in rows:
        state = task_state(row.get("executor_state"), default="queued")
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
        executor["total_attempts"] = total_attempts(summary)
        executor["updated_at"] = now_iso()


def total_attempts(summary: YamlMapping) -> int:
    return sum(int_value(row.get("attempts"), 0) for row in task_rows(summary))


def write_task_executor_state(
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
    status = load_json_mapping(status_path)
    executor = status.get("executor")
    executor_mapping: dict[str, object] = dict(executor) if isinstance(executor, dict) else {}
    executor_mapping.update(
        {
            "state": state,
            "attempts": attempts,
            "updated_at": now_iso(),
            "retryable": retryable,
        }
    )
    set_optional_object(executor_mapping, "attempt_id", attempt_id)
    set_optional_object(executor_mapping, "receipt_path", receipt_path)
    set_optional_object(executor_mapping, "next_retry_at", next_retry_at)
    set_optional_object(executor_mapping, "adapter_status", adapter_status)
    set_optional_object(executor_mapping, "last_error", last_error)
    set_optional_object(executor_mapping, "failure_category", failure_category)
    status["executor"] = executor_mapping
    atomic_write_text(status_path, json.dumps(status, indent=2) + "\n")


def set_optional_row_value(row: YamlMapping, key: str, value: str | None) -> None:
    if value is None:
        row.pop(key, None)
    else:
        row[key] = value


def set_optional_object(mapping: dict[str, object], key: str, value: object | None) -> None:
    if value is None:
        mapping.pop(key, None)
    else:
        mapping[key] = value


def load_json_mapping(path: Path) -> dict[str, object]:
    try:
        loaded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON mapping: {path}") from exc
    if not isinstance(loaded, dict):
        raise ValueError(f"JSON root must be a mapping: {path}")
    return {str(key): value for key, value in loaded.items()}


def required_string(mapping: YamlMapping, key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing or empty field: {key}")
    return value


def optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def bool_value(value: object, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def int_value(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return default


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def future_iso(seconds: int) -> str:
    return (
        (datetime.now(UTC) + timedelta(seconds=seconds))
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def backoff_for_attempt(policy: BatchExecutionPolicy, attempt_number: int) -> int:
    index = min(max(attempt_number - 1, 0), len(policy.retry_backoff_seconds) - 1)
    return policy.retry_backoff_seconds[index]


def task_state(value: object, *, default: ExecutorTaskState) -> ExecutorTaskState:
    if isinstance(value, str) and value in EXECUTOR_TASK_STATES:
        return cast(ExecutorTaskState, value)
    return default


def batch_state(value: object, *, default: BatchExecutorState) -> BatchExecutorState:
    if isinstance(value, str) and value in EXECUTOR_BATCH_STATES:
        return cast(BatchExecutorState, value)
    return default
