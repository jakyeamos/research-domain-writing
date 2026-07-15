from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from rdw.batch_models import BatchEventProjection, BatchExecutorState, BatchTaskProjection
from rdw.batch_support import (
    batch_state,
    bool_value,
    int_value,
    now_iso,
    optional_string,
    task_state,
)
from rdw.io import append_jsonl


@dataclass
class EventWriter:
    batch_dir: Path
    batch_id: str
    operation_id: str
    sequence: int = 0

    def append(self, event_type: str, **fields: object) -> dict[str, object]:
        self.sequence += 1
        payload: dict[str, object] = {
            "at": now_iso(),
            "batch_id": self.batch_id,
            "event_type": event_type,
            "operation_id": self.operation_id,
            "sequence": self.sequence,
            **fields,
        }
        payload["event_id"] = event_id(payload)
        append_jsonl(self.batch_dir / "batch-log.jsonl", payload)
        return payload


def replay_batch_events(batch_dir: Path) -> BatchEventProjection:
    records = read_event_records(batch_dir)
    batch_executor_state: BatchExecutorState = "idle"
    tasks: dict[str, BatchTaskProjection] = {}
    applied: list[str] = []
    duplicates: list[str] = []
    seen: set[str] = set()
    for record in records:
        current_event_id = str(record["event_id"])
        if current_event_id in seen:
            duplicates.append(current_event_id)
            continue
        seen.add(current_event_id)
        applied.append(current_event_id)
        event_type = str(record.get("event_type") or "")
        if event_type == "batch-state":
            batch_executor_state = batch_state(record.get("state"), default=batch_executor_state)
        elif event_type == "task-state":
            task_id = str(record.get("task_id") or "")
            if not task_id:
                continue
            previous = tasks.get(task_id)
            state = task_state(record.get("state"), default="queued")
            attempts = max(
                previous.attempts if previous else 0,
                int_value(record.get("attempt_number"), 0),
            )
            tasks[task_id] = BatchTaskProjection(
                task_id=task_id,
                state=state,
                attempts=attempts,
                attempt_id=event_optional(
                    record, "attempt_id", previous.attempt_id if previous else None
                ),
                last_error=event_optional(
                    record, "last_error", previous.last_error if previous else None
                ),
                receipt_path=event_optional(
                    record, "receipt_path", previous.receipt_path if previous else None
                ),
                next_retry_at=event_optional(
                    record, "next_retry_at", previous.next_retry_at if previous else None
                ),
                retryable=bool_value(
                    record.get("retryable"), previous.retryable if previous else False
                ),
                failure_category=event_optional(
                    record, "failure_category", previous.failure_category if previous else None
                ),
                adapter_status=event_optional(
                    record, "adapter_status", previous.adapter_status if previous else None
                ),
            )
    return BatchEventProjection(
        batch_state=batch_executor_state,
        tasks=tasks,
        applied_event_ids=tuple(applied),
        duplicate_event_ids=tuple(duplicates),
    )


def read_event_records(batch_dir: Path) -> list[dict[str, object]]:
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
        current_event_id = record.get("event_id")
        if not isinstance(current_event_id, str) or not current_event_id:
            current_event_id = f"legacy-{hashlib.sha256(line.strip().encode('utf-8')).hexdigest()}"
            record["event_id"] = current_event_id
        records.append(record)
    return records


def event_id(payload: dict[str, object]) -> str:
    identity = {key: value for key, value in payload.items() if key != "at"}
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return f"evt-{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def event_optional(record: dict[str, object], key: str, previous: str | None) -> str | None:
    if key in record:
        return optional_string(record.get(key))
    return previous
