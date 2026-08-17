from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from rdw.diff_qa import validate_diff_qa
from rdw.io import append_jsonl, atomic_write_text
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
ALLOWED_TASK_TRANSITIONS: dict[str, frozenset[str]] = {
    "planned": frozenset({"research-done"}),
    "research-done": frozenset({"draft-done"}),
    "draft-done": frozenset({"qa-passed", "qa-failed"}),
    "qa-failed": frozenset({"research-done", "draft-done"}),
    "qa-passed": frozenset({"final-done"}),
    "final-done": frozenset(),
}


@dataclass(frozen=True)
class TaskStatusView:
    run_dir: Path
    task_id: str
    status: str
    created_at: str | None
    updated_at: str | None
    next_step: str | None
    reason: str | None
    executor_state: str | None
    diff_qa_status: str | None = None
    diff_qa_needs_review: bool = False
    diff_qa_codes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "run_dir": str(self.run_dir),
            "task_id": self.task_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "next_step": self.next_step,
            "reason": self.reason,
            "executor_state": self.executor_state,
            "diff_qa_status": self.diff_qa_status,
            "diff_qa_needs_review": self.diff_qa_needs_review,
            "diff_qa_codes": list(self.diff_qa_codes),
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
    cancelled: int
    tasks: list[YamlMapping]
    executor: YamlMapping | None

    def as_dict(self) -> dict[str, object]:
        return {
            "batch_dir": str(self.batch_dir),
            "batch_id": self.batch_id,
            "status": self.status,
            "task_count": self.task_count,
            "completed": self.completed,
            "needs_review": self.needs_review,
            "failed": self.failed,
            "cancelled": self.cancelled,
            "tasks": self.tasks,
            "executor": self.executor,
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
    current_status = _normalize_status(str(data.get("status") or "planned"))
    allowed = ALLOWED_TASK_TRANSITIONS.get(current_status)
    if allowed is None:
        raise ValueError(f"status file has unknown current status: {current_status}")
    if normalized not in allowed:
        allowed_text = ", ".join(sorted(allowed)) or "none"
        raise ValueError(
            f"cannot transition {current_status} -> {normalized} (allowed: {allowed_text})"
        )
    if normalized == "qa-failed" and not reason:
        raise ValueError("qa-failed requires --reason")
    diff_qa = None
    if normalized in {"qa-passed", "final-done"}:
        diff_qa = _require_passing_diff_qa(run_dir)
    else:
        diff_qa = _read_diff_qa(run_dir)
    now = _now_iso()
    task_id = str(data.get("task_id") or _task_id_from_contract(run_dir))
    history = data.get("history")
    events: list[YamlValue] = history if isinstance(history, list) else []
    events.append({"status": normalized, "at": now, "reason": reason})
    data["task_id"] = task_id
    data["status"] = normalized
    data["updated_at"] = now
    data["history"] = events
    if diff_qa is not None:
        data["diff_qa"] = diff_qa
    if reason:
        data["reason"] = reason
    elif normalized != "qa-failed":
        data.pop("reason", None)
    data["next_step"] = _next_step_for(normalized)
    atomic_write_text(status_path, json.dumps(data, indent=2) + "\n")
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
        executor_state=_executor_state(data.get("executor")),
        diff_qa_status=_diff_qa_status(data.get("diff_qa")),
        diff_qa_needs_review=_diff_qa_needs_review(data.get("diff_qa")),
        diff_qa_codes=_diff_qa_codes(data.get("diff_qa")),
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
        f"cancelled: {view.cancelled}",
        "",
        "tasks:",
    ]
    for row in view.tasks:
        task_id = str(row.get("task_id", ""))
        status = str(row.get("status", "unknown"))
        domain = str(row.get("domain", ""))
        executor_state = row.get("executor_state")
        state_suffix = f" / {executor_state}" if isinstance(executor_state, str) else ""
        lines.append(f"  - {task_id}: {status}{state_suffix} ({domain})")
    return "\n".join(lines)


def load_batch_status_view(batch_dir: Path) -> BatchStatusView:
    batch_dir = batch_dir.resolve()
    summary_path = batch_dir / "summary.yaml"
    if not summary_path.exists():
        raise ValueError(f"not a planned batch run: {batch_dir} (missing summary.yaml)")
    summary = load_yaml_mapping(summary_path)
    tasks = summary.get("tasks")
    task_rows = [row for row in tasks if isinstance(row, dict)] if isinstance(tasks, list) else []
    _refresh_batch_counts(summary, task_rows, batch_dir, persist=False)
    executor = summary.get("executor")
    return BatchStatusView(
        batch_dir=batch_dir,
        batch_id=str(summary.get("batch_id") or batch_dir.name),
        status=str(summary.get("status") or "unknown"),
        task_count=_int_value(summary.get("task_count"), len(task_rows)),
        completed=_int_value(summary.get("completed"), 0),
        needs_review=_int_value(summary.get("needs_review"), 0),
        failed=_int_value(summary.get("failed"), 0),
        cancelled=_int_value(summary.get("cancelled"), 0),
        tasks=task_rows,
        executor=executor if isinstance(executor, dict) else None,
    )


def batch_resume(batch_dir: Path) -> list[YamlMapping]:
    view = load_batch_status_view(batch_dir)
    pending: list[YamlMapping] = []
    for row in view.tasks:
        status = str(row.get("status") or "planned")
        executor_state = str(row.get("executor_state") or "")
        if status in TERMINAL_TASK_STATUSES or executor_state in {"succeeded", "cancelled"}:
            continue
        task_id = str(row.get("task_id") or "")
        pending.append(
            {
                "task_id": task_id,
                "status": status,
                "executor_state": executor_state or None,
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
    summary: YamlMapping,
    task_rows: list[YamlMapping],
    batch_dir: Path,
    *,
    persist: bool,
) -> None:
    if isinstance(summary.get("executor"), dict):
        _refresh_executor_counts(summary, task_rows, batch_dir)
        if persist:
            atomic_write_text(batch_dir / "summary.yaml", dump_yaml(summary))
        return
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
        if needs_review_for(status) or _task_diff_needs_review(task_dir):
            needs_review += 1
    summary["completed"] = completed
    summary["needs_review"] = needs_review
    summary["failed"] = failed
    summary["task_count"] = len(task_rows)
    if completed == len(task_rows) and task_rows:
        summary["status"] = "complete"
    elif completed or failed:
        summary["status"] = "in_progress"
    if persist:
        atomic_write_text(batch_dir / "summary.yaml", dump_yaml(summary))


def _refresh_executor_counts(
    summary: YamlMapping,
    task_rows: list[YamlMapping],
    batch_dir: Path,
) -> None:
    completed = 0
    needs_review = 0
    failed = 0
    cancelled = 0
    pending = 0
    reconcile_required = 0
    for row in task_rows:
        task_id = str(row.get("task_id") or "")
        task_dir = batch_dir / "tasks" / task_id
        status = str(row.get("status") or "planned")
        if task_dir.is_dir() and (task_dir / "status.json").exists():
            status = load_task_status_view(task_dir).status
            row["status"] = status
        executor_state = row.get("executor_state")
        if not isinstance(executor_state, str):
            executor_state = "succeeded" if status == "final-done" else "queued"
            row["executor_state"] = executor_state
        if executor_state == "succeeded":
            completed += 1
            if _task_diff_needs_review(task_dir):
                needs_review += 1
        elif executor_state == "needs-review":
            needs_review += 1
        elif executor_state == "failed":
            failed += 1
        elif executor_state == "cancelled":
            cancelled += 1
        elif executor_state == "reconcile-required":
            reconcile_required += 1
        else:
            pending += 1
    summary["completed"] = completed
    summary["needs_review"] = needs_review
    summary["failed"] = failed
    summary["cancelled"] = cancelled
    summary["pending"] = pending
    summary["reconcile_required"] = reconcile_required
    summary["task_count"] = len(task_rows)


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
    _refresh_batch_counts(summary, task_rows, batch_root, persist=True)
    log_path = batch_root / "batch-log.jsonl"
    event = {
        "task_id": task_id,
        "domain": _domain_for_task(batch_root, task_id, task_rows),
        "status": status,
        "confidence_level": "unknown",
        "needs_review": needs_review_for(status),
        "missing_info": [reason] if reason else [],
    }
    diff_qa = _read_diff_qa(batch_root / "tasks" / task_id)
    if diff_qa is not None:
        event["diff_qa_status"] = _diff_qa_status(diff_qa)
        event["diff_qa_needs_review"] = _diff_qa_needs_review(diff_qa)
        event["diff_qa_codes"] = list(_diff_qa_codes(diff_qa))
        for row in task_rows:
            if str(row.get("task_id")) == task_id:
                row["diff_qa_status"] = _diff_qa_status(diff_qa)
                row["diff_qa_needs_review"] = _diff_qa_needs_review(diff_qa)
                row["diff_qa_codes"] = list(_diff_qa_codes(diff_qa))
                break
        atomic_write_text(summary_path, dump_yaml(summary))
    append_jsonl(log_path, event)


def needs_review_for(status: str) -> bool:
    return status not in {"planned", *TERMINAL_TASK_STATUSES}


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
        "planned": "Run the selected lane using prompt-bundle.md and save its evidence artifact.",
        "research-done": "Draft domain copy using the lane's evidence artifact and writing templates.",
        "draft-done": "Run lane QA and deterministic diff-QA against the approved baseline.",
        "qa-passed": "Run humanizer/blader for final copy (no new facts); preserve diff-QA status.",
        "qa-failed": "Return to research or copywriter; fix blockers before humanizer.",
        "final-done": "Task complete. Review output artifacts if flagged.",
    }
    return steps.get(status, "Continue the RDW pipeline.")


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _optional_string(value: YamlValue | None) -> str | None:
    return value if isinstance(value, str) and value else None


def _executor_state(value: YamlValue | None) -> str | None:
    if isinstance(value, dict):
        return _optional_string(value.get("state"))
    return None


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


def _require_passing_diff_qa(run_dir: Path) -> YamlMapping:
    contract = _task_contract(run_dir)
    if contract.get("diff_qa_required") is False:
        return {}
    report = _read_diff_qa(run_dir)
    if report is None:
        raise ValueError(
            "diff-QA report is required before qa-passed or final-done; "
            "run `rdw diff-qa` and save the report in the task's diff_qa_path"
        )
    validation = validate_diff_qa(report)
    if not validation.ok:
        raise ValueError("diff-QA report is invalid: " + "; ".join(validation.errors))
    expected_mode = contract.get("diff_qa_mode")
    comparison = report.get("comparison")
    actual_mode = comparison.get("mode") if isinstance(comparison, dict) else None
    if isinstance(expected_mode, str) and expected_mode and actual_mode != expected_mode:
        raise ValueError(
            f"diff-QA mode {actual_mode or 'unknown'} does not match task contract "
            f"({expected_mode})"
        )
    summary = report.get("summary")
    if not isinstance(summary, dict) or summary.get("status") != "pass":
        codes = ", ".join(_diff_qa_codes(report)) or "none"
        status = _diff_qa_status(report) or "unknown"
        raise ValueError(f"diff-QA status {status} blocks promotion (codes: {codes})")
    return report


def _task_contract(run_dir: Path) -> YamlMapping:
    path = run_dir / "task-contract.yaml"
    if not path.exists():
        return {}
    try:
        return load_yaml_mapping(path)
    except ValueError:
        return {}


def _read_diff_qa(run_dir: Path) -> YamlMapping | None:
    path = _diff_qa_path(run_dir)
    if path is None:
        return None
    try:
        return load_yaml_mapping(path)
    except ValueError:
        return None


def _diff_qa_path(run_dir: Path) -> Path | None:
    contract = _task_contract(run_dir)
    configured = contract.get("diff_qa_path")
    if isinstance(configured, str) and configured:
        candidate = _safe_run_path(run_dir, configured)
        if candidate is not None and candidate.is_file():
            return candidate
    qa_dir = run_dir / "outputs" / "qa"
    candidates = sorted(qa_dir.glob("*-diff.yaml")) if qa_dir.is_dir() else []
    return candidates[0] if len(candidates) == 1 else None


def _safe_run_path(run_dir: Path, value: str) -> Path | None:
    path = Path(value)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        return None
    resolved = (run_dir / path).resolve()
    if not resolved.is_relative_to(run_dir.resolve()):
        return None
    return resolved


def _diff_qa_status(value: YamlValue | None) -> str | None:
    if not isinstance(value, dict):
        return None
    summary = value.get("summary")
    if not isinstance(summary, dict):
        return None
    status = summary.get("status")
    return status if isinstance(status, str) else None


def _diff_qa_needs_review(value: YamlValue | None) -> bool:
    if not isinstance(value, dict):
        return False
    summary = value.get("summary")
    return isinstance(summary, dict) and summary.get("needs_human_review") is True


def _diff_qa_codes(value: YamlValue | None) -> tuple[str, ...]:
    if not isinstance(value, dict):
        return ()
    issues = value.get("issues")
    if not isinstance(issues, list):
        return ()
    return tuple(
        sorted(
            {
                str(issue.get("code"))
                for issue in issues
                if isinstance(issue, dict) and isinstance(issue.get("code"), str)
            }
        )
    )


def _task_diff_needs_review(run_dir: Path) -> bool:
    return _diff_qa_needs_review(_read_diff_qa(run_dir))
