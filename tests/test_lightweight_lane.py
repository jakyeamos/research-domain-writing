from __future__ import annotations

import json
from pathlib import Path

from rdw.planner import TaskRequest, infer_contract, plan_task
from rdw.schema_export import export_schema

ROOT = Path(__file__).resolve().parents[1]


def test_light_depth_selects_run_local_research_card_lane(tmp_path: Path) -> None:
    planned = plan_task(
        TaskRequest(
            request="draft a concise outreach email to the hiring manager",
            depth="light",
            task_id="redacted-outreach",
        ),
        tmp_path / "light",
        root=ROOT,
    )

    assert planned.contract["execution_lane"] == "lightweight"
    assert planned.contract["research_needed"] is True
    assert planned.contract["local_knowledge_paths"] == []
    assert planned.contract["research_card_path"] == (
        "outputs/research/redacted-outreach-research-card.yaml"
    )
    assert planned.contract["diff_qa_mode"] == "draft"
    assert "## Lightweight Orchestrator" in planned.prompt_bundle
    assert "lightweight research card" in planned.prompt_bundle
    assert "## Pipeline Orchestrator" not in planned.prompt_bundle
    assert "human_approval_required: true" in planned.prompt_bundle
    assert "Do not send, submit, publish, upload" in planned.prompt_bundle


def test_minimal_depth_is_lightweight_without_new_research() -> None:
    contract = infer_contract(
        TaskRequest(request="short album blurb about production", depth="minimal"), root=ROOT
    )

    assert contract["execution_lane"] == "lightweight"
    assert contract["research_needed"] is False
    assert contract["local_knowledge_paths"] == []
    warnings = contract.get("warnings")
    assert isinstance(warnings, list)
    assert any("minimal depth requires an existing packet" in str(item) for item in warnings)


def test_standard_depth_keeps_full_lane_bundle(tmp_path: Path) -> None:
    planned = plan_task(
        TaskRequest(request="explain idempotency keys", depth="standard"),
        tmp_path / "full",
        root=ROOT,
    )

    assert planned.contract["execution_lane"] == "full"
    assert planned.contract["diff_qa_mode"] == "packet"
    assert planned.contract["local_knowledge_paths"]
    assert "## Pipeline Orchestrator" in planned.prompt_bundle
    assert (
        "Run research, knowledge packet, draft, QA, deterministic diff-QA, and humanizer in order."
        in (planned.prompt_bundle)
    )
    assert "## Lightweight Orchestrator" not in planned.prompt_bundle


def test_task_contract_schema_exposes_lane_and_card_path() -> None:
    schema = json.loads(export_schema("task-contract"))
    properties = schema["properties"]

    assert properties["execution_lane"]["enum"] == ["full", "lightweight"]
    assert properties["research_card_path"]["type"] == "string"
