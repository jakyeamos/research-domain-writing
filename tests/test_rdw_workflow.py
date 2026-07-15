from __future__ import annotations

import json
from pathlib import Path

import pytest

from rdw.adapters import get_adapter, list_adapters
from rdw.cli import main
from rdw.lifecycle import (
    batch_resume,
    load_batch_status_view,
    load_task_status_view,
    mark_task_status,
)
from rdw.planner import TaskRequest, plan_batch, plan_task
from rdw.schema_export import export_schema

ROOT = Path(__file__).resolve().parents[1]


def test_task_status_and_mark(tmp_path: Path) -> None:
    run_dir = tmp_path / "lis-leaderboard"
    plan_task(TaskRequest(request="improve the copy on my LIS leaderboard"), run_dir, root=ROOT)

    view = load_task_status_view(run_dir)
    assert view.status == "planned"

    marked = mark_task_status(run_dir, "research-done")
    assert marked.status == "research-done"
    assert (run_dir / "status.json").is_file()
    history = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))["history"]
    assert history[-1]["status"] == "research-done"


def test_task_mark_qa_failed_with_reason(tmp_path: Path) -> None:
    run_dir = tmp_path / "task"
    plan_task(TaskRequest(request="explain idempotency keys"), run_dir, root=ROOT)

    mark_task_status(run_dir, "research-done")
    mark_task_status(run_dir, "draft-done")
    marked = mark_task_status(run_dir, "qa-failed", reason="unsupported claim")
    assert marked.status == "qa-failed"
    assert marked.reason == "unsupported claim"


def test_task_mark_rejects_illegal_transition(tmp_path: Path) -> None:
    run_dir = tmp_path / "task"
    plan_task(TaskRequest(request="explain idempotency keys"), run_dir, root=ROOT)

    with pytest.raises(ValueError, match="cannot transition planned -> final-done"):
        mark_task_status(run_dir, "final-done")


def test_batch_status_and_resume(tmp_path: Path) -> None:
    batch_dir = tmp_path / "demo-batch"
    plan_batch(ROOT / "examples" / "batch-tasks.yaml", batch_dir, root=ROOT)

    view = load_batch_status_view(batch_dir)
    assert view.task_count == 3
    assert view.completed == 0

    first_task = batch_dir / "tasks" / "batch-demo-guard-summary"
    mark_task_status(first_task, "research-done")
    mark_task_status(first_task, "draft-done")
    mark_task_status(first_task, "qa-passed")
    mark_task_status(first_task, "final-done")

    refreshed = load_batch_status_view(batch_dir)
    assert refreshed.completed == 1

    pending = batch_resume(batch_dir)
    assert len(pending) == 2
    assert pending[0]["task_id"] == "batch-album-blurb"


def test_batch_status_read_does_not_rewrite_summary(tmp_path: Path) -> None:
    batch_dir = tmp_path / "demo-batch"
    plan_batch(ROOT / "examples" / "batch-tasks.yaml", batch_dir, root=ROOT)
    summary_path = batch_dir / "summary.yaml"
    before = summary_path.read_text(encoding="utf-8")
    before_mtime = summary_path.stat().st_mtime_ns

    load_batch_status_view(batch_dir)

    assert summary_path.read_text(encoding="utf-8") == before
    assert summary_path.stat().st_mtime_ns == before_mtime


def test_cli_status_and_mark(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run_dir = tmp_path / "task"
    plan_task(TaskRequest(request="explain idempotency keys"), run_dir, root=ROOT)

    assert main(["status", str(run_dir)]) == 0
    assert "status: planned" in capsys.readouterr().out

    assert main(["task", "mark", "research-done", str(run_dir)]) == 0
    assert "research-done" in capsys.readouterr().out


def test_cli_batch_status_and_resume(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    batch_dir = tmp_path / "demo-batch"
    plan_batch(ROOT / "examples" / "batch-tasks.yaml", batch_dir, root=ROOT)

    assert main(["batch", "status", str(batch_dir)]) == 0
    assert "batch_id: demo-batch-001" in capsys.readouterr().out

    assert main(["batch", "resume", str(batch_dir)]) == 0
    assert "Next tasks:" in capsys.readouterr().out


def test_schema_export_packet_batch_and_contract() -> None:
    packet_schema = json.loads(export_schema("packet"))
    batch_schema = json.loads(export_schema("batch"))
    contract_schema = json.loads(export_schema("task-contract"))

    assert packet_schema["required"] == [
        "id",
        "domain",
        "entity_type",
        "entity_name",
        "key_facts",
        "source_notes",
        "confidence_level",
        "last_updated",
    ]
    assert batch_schema["required"] == ["batch_id", "tasks"]
    assert "task_id" in contract_schema["required"]


def test_cli_schema_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_path = tmp_path / "packet.schema.json"
    assert main(["schema", "packet", "--format", "jsonschema", "-o", str(out_path)]) == 0
    assert out_path.is_file()
    assert "Wrote" in capsys.readouterr().out


def test_adapters_list_and_local_run(tmp_path: Path) -> None:
    assert {"local", "openai", "anthropic"} <= set(list_adapters())

    run_dir = tmp_path / "task"
    plan_task(TaskRequest(request="explain idempotency keys"), run_dir, root=ROOT)

    result = get_adapter("local").run(run_dir)
    assert result.adapter == "local"
    assert (run_dir / "adapter-local.json").is_file()


def test_adapter_run_dry_run_writes_nothing(tmp_path: Path) -> None:
    run_dir = tmp_path / "task"
    plan_task(TaskRequest(request="explain idempotency keys"), run_dir, root=ROOT)

    result = get_adapter("openai").run(run_dir, dry_run=True)
    assert result.artifact_path is None
    assert not (run_dir / "adapter-openai.json").exists()
