from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from rdw.yaml_io import YamlMapping, YamlValue, dump_yaml, load_yaml_mapping

TASK_STATUSES = (
    "planned",
    "research-done",
    "draft-done",
    "qa-passed",
    "qa-failed",
    "final-done",
)

TERMINAL_TASK_STATUSES = frozenset({"final-done"})


@dataclass(frozen=True)
class TaskStatusView:
    run_dir: Path
    task_id: str
    status: str
    created_at: str | None
    updated_at: str | None
    next_step: str | None
    reason: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "run_dir": str(self.run_dir),
            "task_id": self.task_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "next_step": self.next_step,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class BatchStatusView:
    batch_dir: Path
    batch_id: str
    status: str
    task_count: int
    completed: int
    needs_review: int
    failed: int
    tasks: list[YamlMapping]

    def as_dict(self) -> dict[str, object]:
        return {
            "batch_dir": str(self.batch_dir),
            "batch_id": self.batch_id,
            "status": self.status,
            "task_count": self.task_count,
            "completed": self.completed,
            "needs_review": self.needs_review,
            "failed": self.failed,
            "tasks": self.tasks,
        }


def show_task_status(run_dir: Path) -> str:
    view = load_task_status_view(run_dir)
    lines = [
        f"task_id: {view.task_id}",
        f"status: {view.status}",
        f"run_dir: {view.run_dir}",
    ]
    if view.created_at:
        lines.append(f"created_at: {view.created_at}")
    if view.updated_at:
        lines.append(f"updated_at: {view.updated_at}")
    if view.reason:
        lines.append(f"reason: {view.reason}")
    if view.next_step:
        lines.append(f"next_step: {view.next_step}")
    return "\n".join(lines)


def mark_task_status(run_dir: Path, status: str, *, reason: str | None = None) -> TaskStatusView:
    normalized = _normalize_status(status)
    if normalized not in TASK_STATUSES:
        raise ValueError(f"unknown status: {status} (expected one of {', '.join(TASK_STATUSES)})")
    run_dir = run_dir.resolve()
    status_path = _task_status_path(run_dir)
    if not status_path.exists():
        raise ValueError(f"not a planned task run: {run_dir} (missing status.json)")
    data = _load_status(status_path)
    now = _now_iso()
    task_id = str(data.get("task_id") or _task_id_from_contract(run_dir))
    history = data.get("history")
    events: list[YamlValue] = history if isinstance(history, list) else []
    events.append({"status": normalized, "at": now, "reason": reason})
    data["task_id"] = task_id
    data["status"] = normalized
    data["updated_at"] = now
    data["history"] = events
    if reason:
        data["reason"] = reason
    elif normalized != "qa-failed":
        data.pop("reason", None)
    data["next_step"] = _next_step_for(normalized)
    status_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    batch_root = _find_batch_root(run_dir)
    if batch_root is not None:
        _sync_batch_task(batch_root, task_id, normalized, reason=reason)
    return load_task_status_view(run_dir)


def load_task_status_view(run_dir: Path) -> TaskStatusView:
    run_dir = run_dir.resolve()
    status_path = _task_status_path(run_dir)
    if not status_path.exists():
        raise ValueError(f"not a planned task run: {run_dir} (missing status.json)")
    data = _load_status(status_path)
    return TaskStatusView(
        run_dir=run_dir,
        task_id=str(data.get("task_id") or _task_id_from_contract(run_dir)),
        status=str(data.get("status") or "unknown"),
        created_at=_optional_string(data.get("created_at")),
        updated_at=_optional_string(data.get("updated_at")),
        next_step=_optional_string(data.get("next_step")),
        reason=_optional_string(data.get("reason")),
    )


def show_batch_status(batch_dir: Path) -> str:
    view = load_batch_status_view(batch_dir)
    lines = [
        f"batch_id: {view.batch_id}",
        f"status: {view.status}",
        f"task_count: {view.task_count}",
        f"completed: {view.completed}",
        f"needs_review: {view.needs_review}",
        f"failed: {view.failed}",
        "",
        "tasks:",
    ]
    for row in view.tasks:
        task_id = str(row.get("task_id", ""))
        status = str(row.get("status", "unknown"))
        domain = str(row.get("domain", ""))
        lines.append(f"  - {task_id}: {status} ({domain})")
    return "\n".join(lines)


def load_batch_status_view(batch_dir: Path) -> BatchStatusView:
    batch_dir = batch_dir.resolve()
    summary_path = batch_dir / "summary.yaml"
    if not summary_path.exists():
        raise ValueError(f"not a planned batch run: {batch_dir} (missing summary.yaml)")
    summary = load_yaml_mapping(summary_path)
    tasks = summary.get("tasks")
    task_rows = [row for row in tasks if isinstance(row, dict)] if isinstance(tasks, list) else []
    _refresh_batch_counts(summary, task_rows, batch_dir)
    return BatchStatusView(
        batch_dir=batch_dir,
        batch_id=str(summary.get("batch_id") or batch_dir.name),
        status=str(summary.get("status") or "unknown"),
        task_count=_int_value(summary.get("task_count"), len(task_rows)),
        completed=_int_value(summary.get("completed"), 0),
        needs_review=_int_value(summary.get("needs_review"), 0),
        failed=_int_value(summary.get("failed"), 0),
        tasks=task_rows,
    )


def batch_resume(batch_dir: Path) -> list[YamlMapping]:
    view = load_batch_status_view(batch_dir)
    pending: list[YamlMapping] = []
    for row in view.tasks:
        status = str(row.get("status") or "planned")
        if status in TERMINAL_TASK_STATUSES:
            continue
        task_id = str(row.get("task_id") or "")
        pending.append(
            {
                "task_id": task_id,
                "status": status,
                "domain": row.get("domain"),
                "prompt_bundle": row.get("prompt_bundle"),
                "run_dir": str(batch_dir / "tasks" / task_id),
            }
        )
    return pending


def format_batch_resume(batch_dir: Path) -> str:
    pending = batch_resume(batch_dir)
    if not pending:
        return "All batch tasks are complete."
    lines = ["Next tasks:"]
    for index, row in enumerate(pending, start=1):
        lines.append(
            f"{index}. {row['task_id']} [{row['status']}] -> {row['run_dir']}/prompt-bundle.md"
        )
    return "\n".join(lines)


def _refresh_batch_counts(
    summary: YamlMapping, task_rows: list[YamlMapping], batch_dir: Path
) -> None:
    completed = 0
    needs_review = 0
    failed = 0
    for row in task_rows:
        task_id = str(row.get("task_id") or "")
        task_dir = batch_dir / "tasks" / task_id
        if task_dir.is_dir() and (task_dir / "status.json").exists():
            status = load_task_status_view(task_dir).status
            row["status"] = status
        status = str(row.get("status") or "planned")
        if status == "final-done":
            completed += 1
        if status == "qa-failed":
            failed += 1
            needs_review += 1
        elif status not in TERMINAL_TASK_STATUSES and status != "planned":
            needs_review += 1
    summary["completed"] = completed
    summary["needs_review"] = needs_review
    summary["failed"] = failed
    summary["task_count"] = len(task_rows)
    if completed == len(task_rows) and task_rows:
        summary["status"] = "complete"
    elif completed or failed:
        summary["status"] = "in_progress"
    (batch_dir / "summary.yaml").write_text(dump_yaml(summary), encoding="utf-8")


def _sync_batch_task(batch_root: Path, task_id: str, status: str, *, reason: str | None) -> None:
    summary_path = batch_root / "summary.yaml"
    summary = load_yaml_mapping(summary_path)
    tasks = summary.get("tasks")
    if not isinstance(tasks, list):
        return
    for row in tasks:
        if isinstance(row, dict) and str(row.get("task_id")) == task_id:
            row["status"] = status
            break
    task_rows = [row for row in tasks if isinstance(row, dict)]
    _refresh_batch_counts(summary, task_rows, batch_root)
    log_path = batch_root / "batch-log.jsonl"
    event = {
        "task_id": task_id,
        "domain": _domain_for_task(batch_root, task_id, task_rows),
        "status": status,
        "confidence_level": "unknown",
        "needs_review": status in {"qa-failed", "planned"} or status not in TERMINAL_TASK_STATUSES,
        "missing_info": [reason] if reason else [],
    }
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    line = json.dumps(event, sort_keys=True)
    log_path.write_text(f"{existing}{line}\n" if existing else f"{line}\n", encoding="utf-8")


def _domain_for_task(batch_root: Path, task_id: str, task_rows: list[YamlMapping]) -> str:
    for row in task_rows:
        if str(row.get("task_id")) == task_id:
            return str(row.get("domain") or "unknown")
    contract_path = batch_root / "tasks" / task_id / "task-contract.yaml"
    if contract_path.exists():
        contract = load_yaml_mapping(contract_path)
        return str(contract.get("domain") or "unknown")
    return "unknown"


def _task_status_path(run_dir: Path) -> Path:
    return run_dir / "status.json"


def _load_status(path: Path) -> YamlMapping:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"invalid status file: {path}")
    return loaded


def _task_id_from_contract(run_dir: Path) -> str:
    contract_path = run_dir / "task-contract.yaml"
    if contract_path.exists():
        contract = load_yaml_mapping(contract_path)
        return str(contract.get("task_id") or run_dir.name)
    return run_dir.name


def _find_batch_root(task_dir: Path) -> Path | None:
    parent = task_dir.parent
    if parent.name == "tasks" and (parent.parent / "summary.yaml").exists():
        return parent.parent
    return None


def _normalize_status(status: str) -> str:
    return status.strip().lower().replace("_", "-")


def _next_step_for(status: str) -> str:
    steps = {
        "planned": "Run research using prompt-bundle.md and save a knowledge packet.",
        "research-done": "Draft domain copy using the knowledge packet and writing templates.",
        "draft-done": "Run domain QA against the draft and packet.",
        "qa-passed": "Run humanizer/blader for final copy (no new facts).",
        "qa-failed": "Return to research or copywriter; fix blockers before humanizer.",
        "final-done": "Task complete. Review output artifacts if flagged.",
    }
    return steps.get(status, "Continue the RDW pipeline.")


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _optional_string(value: YamlValue | None) -> str | None:
    return value if isinstance(value, str) and value else None


def _int_value(value: YamlValue | None, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return default
