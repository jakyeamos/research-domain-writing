from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest

from rdw.batch_execution import (
    BatchExecutionPolicy,
    BatchLeaseConflictError,
    execute_batch,
    replay_batch_events,
    request_batch_cancel,
    request_batch_pause,
)
from rdw.cli import main
from rdw.execution import execute_fixture
from rdw.io import atomic_write_text
from rdw.planner import plan_batch
from rdw.yaml_io import dump_yaml, load_yaml_mapping

ROOT = Path(__file__).resolve().parents[1]


def _write_batch(tmp_path: Path, task_ids: tuple[str, ...]) -> tuple[Path, Path]:
    tasks = []
    for task_id in task_ids:
        tasks.extend(
            [
                f"  - task_id: {task_id}",
                '    request: "Two-sentence player summary for Demo Guard synthetic sample"',
                "    domain: basketball",
                "    entity_name: Demo Guard",
                "    output_type: player_summary",
                "    research_depth: light",
                "    packet_id: basketball-player-demo-guard-2026",
            ]
        )
    batch_input = tmp_path / "batch.yaml"
    batch_input.write_text(
        "\n".join(
            [
                "batch_id: batch-test-001",
                "tasks:",
                *tasks,
                "",
            ]
        ),
        encoding="utf-8",
    )
    batch_dir = tmp_path / "batch-run"
    plan_batch(batch_input, batch_dir, root=ROOT)
    fixture_map = tmp_path / "fixture-map.yaml"
    fixture_map.write_text(
        "\n".join(
            [
                "batch_id: batch-test-001",
                "fixtures:",
                *[f"  {task_id}: {task_id}.yaml" for task_id in task_ids],
                "",
            ]
        ),
        encoding="utf-8",
    )
    return batch_dir, fixture_map


def _write_fixture(tmp_path: Path, task_id: str, *, outcome: str = "succeeded") -> Path:
    fixture = tmp_path / f"{task_id}.yaml"
    if outcome == "succeeded":
        content = """fixture_version: 1
name: generic-success
outcome: succeeded
requested_stages: [research, draft, qa, final]
needs_review: false
missing_info: []
artifacts:
  research_packet: knowledge/basketball/demo-guard-2026-demo.yaml
  knowledge_packet: examples/basketball-example/knowledge-packet.md
  draft: examples/basketball-example/draft.md
  qa: examples/basketball-example/qa-output.yaml
  final: examples/basketball-example/final.md
"""
    elif outcome == "incomplete":
        content = """fixture_version: 1
name: generic-review
outcome: incomplete
requested_stages: [research, draft, qa, final]
needs_review: true
missing_info:
  - The draft needs a grounding review before final styling.
artifacts:
  research_packet: knowledge/basketball/demo-guard-2026-demo.yaml
  knowledge_packet: examples/basketball-example/knowledge-packet.md
  draft: examples/basketball-example/draft.md
  qa: examples/fixtures/basketball-vertical-slice-qa-failed-output.yaml
"""
    else:
        content = """fixture_version: 1
name: generic-retry
outcome: failed
requested_stages: [research, draft, qa, final]
needs_review: true
missing_info: []
failure:
  category: network
  code: transient_network
  message: temporary fixture network failure
  retryable: true
artifacts: {}
"""
    fixture.write_text(content, encoding="utf-8")
    return fixture


def _set_fixture_map_paths(fixture_map: Path, paths: dict[str, Path]) -> None:
    data = load_yaml_mapping(fixture_map)
    data["fixtures"] = {task_id: str(path) for task_id, path in paths.items()}
    atomic_write_text(fixture_map, dump_yaml(data))


def _zero_retry_policy(**overrides: object) -> BatchExecutionPolicy:
    values: dict[str, object] = {
        "retry_backoff_seconds": (0, 0),
        **overrides,
    }
    return BatchExecutionPolicy(**values)  # type: ignore[arg-type]


def test_serial_batch_executes_in_input_order_and_projects_success(tmp_path: Path) -> None:
    task_ids = ("task-a", "task-b")
    batch_dir, fixture_map = _write_batch(tmp_path, task_ids)
    paths = {task_id: _write_fixture(tmp_path, task_id) for task_id in task_ids}
    _set_fixture_map_paths(fixture_map, paths)

    result = execute_batch(
        batch_dir,
        fixture_map,
        root=ROOT,
        policy=_zero_retry_policy(),
    )

    assert result.state == "completed"
    assert [task.task_id for task in result.tasks] == list(task_ids)
    assert [task.state for task in result.tasks] == ["succeeded", "succeeded"]
    assert result.completed == 2
    assert result.total_attempts == 2
    assert not (batch_dir / "executor-lease.json").exists()
    projection = replay_batch_events(batch_dir)
    assert [projection.tasks[task_id].state for task_id in task_ids] == [
        "succeeded",
        "succeeded",
    ]
    assert projection.duplicate_event_ids == ()


def test_fixture_map_policy_is_typed_and_enforces_serial_bounds(tmp_path: Path) -> None:
    batch_dir, fixture_map = _write_batch(tmp_path, ("policy-task",))
    fixture = _write_fixture(tmp_path, "policy-task")
    _set_fixture_map_paths(fixture_map, {"policy-task": fixture})
    fixture_map_data = load_yaml_mapping(fixture_map)
    fixture_map_data["execution"] = {
        "max_concurrency": 1,
        "max_attempts": 1,
        "retry_backoff_seconds": [0],
        "max_tasks": 1,
        "max_total_attempts": 1,
        "failure_policy": "continue",
    }
    atomic_write_text(fixture_map, dump_yaml(fixture_map_data))

    result = execute_batch(batch_dir, fixture_map, root=ROOT)

    assert result.state == "completed"
    summary = load_yaml_mapping(batch_dir / "summary.yaml")
    executor = summary.get("executor")
    assert isinstance(executor, dict)
    policy = executor.get("policy")
    assert isinstance(policy, dict)
    assert policy["max_concurrency"] == 1
    assert policy["max_attempts"] == 1


def test_batch_retry_is_bounded_and_preserves_failure_receipts(tmp_path: Path) -> None:
    batch_dir, fixture_map = _write_batch(tmp_path, ("retry-task",))
    fixture = _write_fixture(tmp_path, "retry-task", outcome="failed")
    _set_fixture_map_paths(fixture_map, {"retry-task": fixture})

    result = execute_batch(
        batch_dir,
        fixture_map,
        root=ROOT,
        policy=_zero_retry_policy(max_attempts=2),
    )

    assert result.state == "completed-with-failures"
    assert result.failed == 1
    assert result.tasks[0].attempts == 2
    receipts = list(
        (batch_dir / "tasks" / "retry-task" / "adapter-runs" / "fixture").glob("*/receipt.json")
    )
    assert len(receipts) == 2
    receipt_payloads = [json.loads(path.read_text(encoding="utf-8")) for path in receipts]
    assert all(payload["status"] == "failed" for payload in receipt_payloads)
    assert len({payload["idempotency_key"] for payload in receipt_payloads}) == 1
    projection = replay_batch_events(batch_dir)
    assert projection.tasks["retry-task"].attempts == 2
    assert projection.tasks["retry-task"].state == "failed"


def test_batch_review_outcome_is_partial_success(tmp_path: Path) -> None:
    task_ids = ("success-task", "review-task")
    batch_dir, fixture_map = _write_batch(tmp_path, task_ids)
    success = _write_fixture(tmp_path, "success-task")
    review = _write_fixture(tmp_path, "review-task", outcome="incomplete")
    _set_fixture_map_paths(fixture_map, {"success-task": success, "review-task": review})

    result = execute_batch(batch_dir, fixture_map, root=ROOT, policy=_zero_retry_policy())

    assert result.state == "completed-with-failures"
    assert result.completed == 1
    assert result.needs_review == 1
    assert (batch_dir / "tasks" / "success-task" / "outputs" / "final").is_dir()
    assert not (batch_dir / "tasks" / "review-task" / "outputs" / "final").exists()


def test_pause_resume_is_cooperative_and_batch_resume_remains_read_only(tmp_path: Path) -> None:
    batch_dir, fixture_map = _write_batch(tmp_path, ("pause-task",))
    fixture = _write_fixture(tmp_path, "pause-task")
    _set_fixture_map_paths(fixture_map, {"pause-task": fixture})

    paused = request_batch_pause(batch_dir)
    assert paused.state == "paused"
    blocked = execute_batch(batch_dir, fixture_map, root=ROOT, policy=_zero_retry_policy())
    assert blocked.state == "paused"
    assert not (batch_dir / "tasks" / "pause-task" / "adapter-runs").exists()

    resumed = execute_batch(
        batch_dir,
        fixture_map,
        root=ROOT,
        resume=True,
        policy=_zero_retry_policy(),
    )
    assert resumed.state == "completed"
    assert resumed.completed == 1


def test_cancel_preserves_completed_tasks_and_cancels_queued_tasks(tmp_path: Path) -> None:
    task_ids = ("completed-task", "queued-task")
    batch_dir, fixture_map = _write_batch(tmp_path, task_ids)
    success = _write_fixture(tmp_path, "completed-task")
    queued = _write_fixture(tmp_path, "queued-task")
    _set_fixture_map_paths(fixture_map, {"completed-task": success, "queued-task": queued})

    execute_fixture(batch_dir / "tasks" / "completed-task", success, root=ROOT)
    cancelled = request_batch_cancel(batch_dir)

    assert cancelled.state == "cancelled"
    assert cancelled.completed == 1
    assert cancelled.cancelled == 1
    assert (batch_dir / "tasks" / "completed-task" / "outputs" / "final").is_dir()
    assert not (batch_dir / "tasks" / "queued-task" / "adapter-runs").exists()


def test_duplicate_event_replay_is_idempotent(tmp_path: Path) -> None:
    batch_dir, fixture_map = _write_batch(tmp_path, ("replay-task",))
    fixture = _write_fixture(tmp_path, "replay-task")
    _set_fixture_map_paths(fixture_map, {"replay-task": fixture})
    execute_batch(batch_dir, fixture_map, root=ROOT, policy=_zero_retry_policy())

    before = replay_batch_events(batch_dir)
    lines = (batch_dir / "batch-log.jsonl").read_text(encoding="utf-8").splitlines()
    last_event = lines[-1]
    with (batch_dir / "batch-log.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(last_event + "\n")
    after = replay_batch_events(batch_dir)

    assert after.tasks == before.tasks
    assert after.batch_state == before.batch_state
    assert after.duplicate_event_ids == (json.loads(last_event)["event_id"],)


def test_live_lease_conflict_is_not_reclaimed_implicitly(tmp_path: Path) -> None:
    batch_dir, fixture_map = _write_batch(tmp_path, ("lease-task",))
    fixture = _write_fixture(tmp_path, "lease-task")
    _set_fixture_map_paths(fixture_map, {"lease-task": fixture})
    expires_at = (datetime.now(UTC) + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    (batch_dir / "executor-lease.json").write_text(
        json.dumps(
            {
                "lease_id": "other-lease",
                "batch_id": "batch-test-001",
                "acquired_at": "2026-07-15T00:00:00Z",
                "expires_at": expires_at,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(BatchLeaseConflictError, match="lease is active"):
        execute_batch(batch_dir, fixture_map, root=ROOT, policy=_zero_retry_policy())


def test_expired_lease_recovery_marks_unknown_attempt_without_retry(tmp_path: Path) -> None:
    batch_dir, fixture_map = _write_batch(tmp_path, ("unknown-task",))
    fixture = _write_fixture(tmp_path, "unknown-task")
    _set_fixture_map_paths(fixture_map, {"unknown-task": fixture})
    paused = request_batch_pause(batch_dir)
    assert paused.state == "paused"

    summary = load_yaml_mapping(batch_dir / "summary.yaml")
    tasks = summary.get("tasks")
    assert isinstance(tasks, list)
    task_row_value = tasks[0]
    assert isinstance(task_row_value, dict)
    task_row = cast(dict[str, object], task_row_value)
    task_row["executor_state"] = "running"
    task_row["attempt_id"] = "attempt-unknown"
    task_row["attempts"] = 1
    executor = summary.get("executor")
    assert isinstance(executor, dict)
    executor["state"] = "running"
    atomic_write_text(batch_dir / "summary.yaml", dump_yaml(summary))
    status_path = batch_dir / "tasks" / "unknown-task" / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["executor"] = {"state": "running", "attempt_id": "attempt-unknown", "attempts": 1}
    atomic_write_text(status_path, json.dumps(status, indent=2) + "\n")
    expired = (datetime.now(UTC) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    (batch_dir / "executor-lease.json").write_text(
        json.dumps(
            {
                "lease_id": "expired-lease",
                "batch_id": "batch-test-001",
                "acquired_at": "2026-07-15T00:00:00Z",
                "expires_at": expired,
            }
        ),
        encoding="utf-8",
    )

    result = execute_batch(
        batch_dir,
        fixture_map,
        root=ROOT,
        reclaim_lease=True,
        policy=_zero_retry_policy(),
    )

    assert result.state == "recovery-required"
    assert result.recovery_required
    assert result.tasks[0].state == "reconcile-required"
    assert not (batch_dir / "tasks" / "unknown-task" / "adapter-runs").exists()


def test_cli_batch_execute_is_additive_and_machine_readable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    batch_dir, fixture_map = _write_batch(tmp_path, ("cli-task",))
    fixture = _write_fixture(tmp_path, "cli-task")
    _set_fixture_map_paths(fixture_map, {"cli-task": fixture})

    assert (
        main(
            [
                "batch",
                "execute",
                str(batch_dir),
                "--fixture-map",
                str(fixture_map),
                "--root",
                str(ROOT),
                "--dry-run",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert payload["state"] == "idle"
    assert not (batch_dir / "executor-lease.json").exists()
