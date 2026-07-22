from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from rdw.batch_events import EventWriter
from rdw.batch_models import BatchLease, BatchLeaseConflictError
from rdw.batch_projection import record_batch_state, record_task_state
from rdw.batch_support import (
    int_value,
    load_json_mapping,
    load_summary,
    now_iso,
    optional_string,
    parse_iso,
    task_rows,
    task_state,
)


def mark_unknown_attempts(batch_dir: Path, batch_id: str) -> bool:
    summary = load_summary(batch_dir)
    writer = EventWriter(batch_dir, batch_id, f"reclaim-{uuid.uuid4().hex}")
    found = False
    for row in task_rows(summary):
        task_id = str(row.get("task_id") or "")
        status_details = task_executor_details(batch_dir / "tasks" / task_id)
        state_value = row.get("executor_state")
        if not isinstance(state_value, str):
            state_value = status_details.get("state")
        state = task_state(state_value, default="queued")
        attempt_id = optional_string(row.get("attempt_id")) or optional_string(
            status_details.get("attempt_id")
        )
        if state in {"leased", "running", "retry-wait"} and attempt_id:
            found = True
            record_task_state(
                batch_dir,
                summary,
                row,
                "reconcile-required",
                writer,
                attempt_id=attempt_id,
                attempt_number=int_value(
                    row.get("attempts"), int_value(status_details.get("attempts"), 0)
                ),
                receipt_path=optional_string(row.get("receipt_path"))
                or optional_string(status_details.get("receipt_path")),
                last_error="attempt outcome is unknown; inspect the immutable receipt before retrying",
                failure_category="unknown_attempt",
                retryable=False,
            )
    if found:
        record_batch_state(
            summary,
            "recovery-required",
            writer,
            reason="unknown attempt requires explicit reconciliation",
        )
    return found


def task_executor_details(task_dir: Path) -> dict[str, object]:
    status_path = task_dir / "status.json"
    if not status_path.is_file():
        return {}
    status = load_json_mapping(status_path)
    executor = status.get("executor")
    return dict(executor) if isinstance(executor, dict) else {}


def acquire_lease(
    batch_dir: Path,
    batch_id: str,
    *,
    reclaim: bool,
) -> tuple[BatchLease, bool]:
    lease_path = batch_dir / "executor-lease.json"
    unknown_attempts = False
    if lease_path.exists():
        existing = load_json_mapping(lease_path)
        expires_at = parse_iso(optional_string(existing.get("expires_at")))
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
        unknown_attempts = mark_unknown_attempts(batch_dir, batch_id)
        lease_path.unlink()

    acquired_at = now_iso()
    expires_at = (datetime.now(UTC) + timedelta(seconds=300)).replace(microsecond=0)
    lease = BatchLease(
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


def release_lease(batch_dir: Path, lease: BatchLease) -> None:
    lease_path = batch_dir / "executor-lease.json"
    if not lease_path.exists():
        return
    current = load_json_mapping(lease_path)
    if str(current.get("lease_id") or "") == lease.lease_id:
        lease_path.unlink()
