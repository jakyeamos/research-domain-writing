from __future__ import annotations

import json
from pathlib import Path

import pytest

from rdw.cli import main
from rdw.execution import execute_fixture
from rdw.lifecycle import load_task_status_view
from rdw.planner import TaskRequest, plan_task

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples" / "fixtures"
SUCCESS_FIXTURE = FIXTURES / "basketball-vertical-slice.yaml"
QA_FAILED_FIXTURE = FIXTURES / "basketball-vertical-slice-qa-failed.yaml"
REJECTED_FIXTURE = FIXTURES / "basketball-vertical-slice-rejected.yaml"
ACCEPTANCE_FIXTURE = FIXTURES / "basketball-acceptance-ranking.yaml"


def _plan_demo(run_dir: Path) -> None:
    plan_task(
        TaskRequest(
            request=(
                "Explain why true shooting on high usage is the key read on Demo Guard "
                "in the 2026 synthetic sample — and when a stat model might still be skeptical."
            ),
            domain="basketball",
            entity="Demo Guard",
            output_type="stat_interpretation",
            audience="analytics-literate fans",
            depth="standard",
            packet_id="basketball-player-demo-guard-2026",
            task_id="basketball-example-demo-guard-stat-interpretation",
        ),
        run_dir,
        root=ROOT,
    )


def _plan_acceptance_ranking(run_dir: Path) -> None:
    plan_task(
        TaskRequest(
            request=(
                "Explain how to read a supplied usage-rate and true-shooting change comparison "
                "without turning it into a complete player-value ranking."
            ),
            domain="basketball",
            entity="Usage and true-shooting change comparison",
            output_type="ranking_explanation",
            audience="analytics-literate basketball readers",
            depth="standard",
            packet_id="basketball-ranking-usage-ts-change-2025-26",
            task_id="basketball-acceptance-ranking-methodology",
        ),
        run_dir,
        root=ROOT,
    )


def test_fixture_execution_completes_vertical_slice(tmp_path: Path) -> None:
    run_dir = tmp_path / "demo-task"
    _plan_demo(run_dir)

    result = execute_fixture(run_dir, SUCCESS_FIXTURE, root=ROOT)

    assert result.adapter_status == "succeeded"
    assert result.workflow_status == "final-done"
    assert len(result.promoted_paths) == 5
    assert (run_dir / "outputs" / "research" / "basketball-player-demo-guard-2026.yaml").is_file()
    assert (
        run_dir
        / "outputs"
        / "research"
        / "basketball-example-demo-guard-stat-interpretation-knowledge.md"
    ).is_file()
    assert (
        run_dir / "outputs" / "drafts" / "basketball-example-demo-guard-stat-interpretation.md"
    ).is_file()
    assert (
        run_dir / "outputs" / "qa" / "basketball-example-demo-guard-stat-interpretation-qa.yaml"
    ).is_file()
    assert (
        run_dir / "outputs" / "final" / "basketball-example-demo-guard-stat-interpretation.md"
    ).is_file()

    assert result.receipt_path is not None
    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    assert receipt["status"] == "succeeded"
    assert receipt["idempotency_key"] == result.idempotency_key
    assert receipt["artifacts"]
    assert [
        item["status"] for item in json.loads((run_dir / "status.json").read_text())["history"]
    ] == [
        "research-done",
        "draft-done",
        "qa-passed",
        "final-done",
    ]


def test_fixture_execution_completes_source_grounded_acceptance_slice(tmp_path: Path) -> None:
    run_dir = tmp_path / "acceptance-ranking-task"
    _plan_acceptance_ranking(run_dir)

    result = execute_fixture(run_dir, ACCEPTANCE_FIXTURE, root=ROOT)

    assert result.adapter_status == "succeeded"
    assert result.workflow_status == "final-done"
    assert len(result.promoted_paths) == 5
    assert (
        run_dir / "outputs" / "final" / "basketball-acceptance-ranking-methodology.md"
    ).is_file()
    assert [
        item["status"] for item in json.loads((run_dir / "status.json").read_text())["history"]
    ] == [
        "research-done",
        "draft-done",
        "qa-passed",
        "final-done",
    ]


def test_fixture_execution_records_qa_uncertainty_and_resumes(tmp_path: Path) -> None:
    run_dir = tmp_path / "retry-task"
    _plan_demo(run_dir)

    first = execute_fixture(run_dir, QA_FAILED_FIXTURE, root=ROOT)

    assert first.adapter_status == "incomplete"
    assert first.workflow_status == "qa-failed"
    assert first.needs_review
    assert not (run_dir / "outputs" / "final").exists()
    assert (
        load_task_status_view(run_dir).reason
        == "The draft needs a grounding review before final styling."
    )

    with pytest.raises(ValueError, match="requires --resume"):
        execute_fixture(run_dir, SUCCESS_FIXTURE, root=ROOT)

    second = execute_fixture(run_dir, SUCCESS_FIXTURE, root=ROOT, resume=True)

    assert second.adapter_status == "succeeded"
    assert second.workflow_status == "final-done"
    assert first.attempt_id != second.attempt_id
    assert first.idempotency_key == second.idempotency_key
    assert len(list((run_dir / "adapter-runs" / "fixture").glob("*/receipt.json"))) == 2


def test_fixture_execution_preserves_rejected_outcome(tmp_path: Path) -> None:
    run_dir = tmp_path / "rejected-task"
    _plan_demo(run_dir)

    result = execute_fixture(run_dir, REJECTED_FIXTURE, root=ROOT)

    assert result.adapter_status == "rejected"
    assert result.workflow_status == "planned"
    assert result.promoted_paths == ()
    assert result.receipt_path is not None
    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    assert receipt["failure"]["category"] == "unsupported"
    assert json.loads((run_dir / "status.json").read_text(encoding="utf-8"))["status"] == "planned"


def test_cli_fixture_execution_emits_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run_dir = tmp_path / "cli-task"
    _plan_demo(run_dir)

    assert (
        main(
            [
                "task",
                "execute",
                str(run_dir),
                "--fixture",
                str(SUCCESS_FIXTURE),
                "--root",
                str(ROOT),
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["adapter_status"] == "succeeded"
    assert payload["workflow_status"] == "final-done"
