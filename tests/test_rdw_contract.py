from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

from rdw.cli import main
from rdw.planner import TaskRequest, infer_contract, plan_batch, plan_task
from rdw.validation import validate_batch_file, validate_packet_file
from rdw.yaml_io import YamlValue

ROOT = Path(__file__).resolve().parents[1]


def test_cli_doctor_passes(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["doctor"]) == 0
    output = capsys.readouterr().out
    assert re.search(r"rdw \d+\.\d+\.\d+", output)
    assert "OK pipeline orchestrator" in output


def test_sample_packet_validates_strict() -> None:
    result = validate_packet_file(
        ROOT / "knowledge" / "basketball" / "demo-guard-2026-demo.yaml",
        strict=True,
        root=ROOT,
    )

    assert result.ok
    assert result.errors == []


def test_validator_reports_missing_required_fields() -> None:
    packet = ROOT / "examples" / "invalid-packet.yaml"

    result = validate_packet_file(packet, root=ROOT)

    assert not result.ok
    assert f"not found: {packet}" in result.errors


def test_validator_reports_invalid_confidence_and_source_linkage(tmp_path: Path) -> None:
    packet = tmp_path / "packet.yaml"
    packet.write_text(
        "\n".join(
            [
                "id: packet",
                "domain: basketball",
                "entity_type: player",
                "entity_name: Player",
                "key_facts:",
                "  - id: fact-1",
                "    text: known fact",
                "source_notes:",
                "  - source: sample",
                "    accessed: '2026-06-26'",
                "    note: sample",
                "    fact_ids: [missing-fact]",
                "confidence_level: certain",
                "last_updated: not-a-date",
            ]
        ),
        encoding="utf-8",
    )

    result = validate_packet_file(packet, strict=True, root=ROOT)

    assert "confidence_level must be high|medium|low" in result.errors
    assert "last_updated must be an ISO date or datetime string" in result.errors
    assert "source_notes[1] references unknown fact id: missing-fact" in result.errors


def test_batch_validator_accepts_example() -> None:
    result = validate_batch_file(ROOT / "examples" / "batch-tasks.yaml", root=ROOT)

    assert result.ok


def test_batch_validator_rejects_duplicate_and_bad_depth(tmp_path: Path) -> None:
    batch = tmp_path / "batch.yaml"
    batch.write_text(
        "\n".join(
            [
                "batch_id: bad",
                "tasks:",
                "  - task_id: same",
                "    request: one",
                "    research_depth: impossible",
                "  - task_id: same",
                "    request: two",
            ]
        ),
        encoding="utf-8",
    )

    result = validate_batch_file(batch, root=ROOT)

    assert "tasks[1] invalid research_depth: impossible" in result.errors
    assert "duplicate task_id: same" in result.errors


def test_router_infers_lis_leaderboard() -> None:
    contract = infer_contract(
        TaskRequest(request="improve the copy on my LIS leaderboard"), root=ROOT
    )

    assert contract["domain"] == "basketball"
    assert contract["entity_name"] == "LIS leaderboard"
    assert contract["output_type"] == "ranking_explanation"


def test_router_infers_music_and_technical() -> None:
    music = infer_contract(TaskRequest(request="short album blurb about production"), root=ROOT)
    technical = infer_contract(
        TaskRequest(request="explain the API feature for backend engineers"), root=ROOT
    )
    idempotency = infer_contract(TaskRequest(request="explain idempotency keys"), root=ROOT)

    assert music["domain"] == "music"
    assert music["output_type"] == "album_review_blurb"
    assert technical["domain"] == "technical"
    assert technical["output_type"] == "feature_explainer"
    assert idempotency["domain"] == "technical"
    assert idempotency["entity_name"] == "Idempotency keys"
    assert idempotency["output_type"] == "feature_explainer"


def test_infer_contract_includes_output_format() -> None:
    default = infer_contract(TaskRequest(request="explain idempotency keys"), root=ROOT)
    assert default["output_format"] == "markdown"

    explicit = infer_contract(
        TaskRequest(request="explain idempotency keys", output_format="json"), root=ROOT
    )
    assert explicit["output_format"] == "json"

    unknown = infer_contract(
        TaskRequest(request="explain idempotency keys", output_format="pdf"), root=ROOT
    )
    assert unknown["output_format"] == "pdf"
    warnings = cast("list[YamlValue]", unknown["warnings"])
    assert any("unknown output_format: pdf" in str(w) for w in warnings)


def test_task_plan_writes_deterministic_bundle(tmp_path: Path) -> None:
    output = tmp_path / "task"

    planned = plan_task(
        TaskRequest(request="improve the copy on my LIS leaderboard"),
        output,
        root=ROOT,
    )

    assert planned.task_id == "basketball-lis-leaderboard-ranking-explanation"
    assert (output / "task-contract.yaml").is_file()
    bundle = (output / "prompt-bundle.md").read_text(encoding="utf-8")
    assert "# RDW Agent Prompt Bundle" in bundle
    assert "LIS leaderboard" in bundle
    status = json.loads((output / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "planned"


def test_batch_plan_writes_summary_and_log(tmp_path: Path) -> None:
    output = tmp_path / "batch"

    plan_batch(ROOT / "examples" / "batch-tasks.yaml", output, root=ROOT)

    summary = (output / "summary.yaml").read_text(encoding="utf-8")
    log = (output / "batch-log.jsonl").read_text(encoding="utf-8")
    assert "task_count: 3" in summary
    assert "batch-demo-guard-summary" in log
    assert (output / "tasks" / "batch-demo-guard-summary" / "prompt-bundle.md").is_file()


def test_cli_install_templates_with_temp_home(tmp_path: Path) -> None:
    home = tmp_path / "home"

    assert (
        main(["install", "--target", "all", "--home", str(home), "--source-root", str(ROOT)]) == 0
    )

    assert (home / ".claude" / "commands" / "rdw.md").is_file()
    assert (home / ".cursor" / "skills" / "rdw" / "SKILL.md").is_file()
    assert (home / ".agents" / "skills" / "research-domain-writing").is_symlink()


def test_config_domain_and_format_accessors() -> None:
    from rdw import config

    known = config.known_domains(ROOT)
    enabled = config.enabled_domains(ROOT)
    assert {"general", "basketball", "music", "technical", "legal", "finance"} <= known
    assert "legal" in known and "legal" not in enabled
    assert "finance" in known and "finance" not in enabled
    assert "basketball" in enabled

    assert {"markdown", "json", "yaml"} <= config.output_formats(ROOT)
    assert config.default_output_format(ROOT) == "markdown"


def _disabled_domain_packet(tmp_path: Path) -> Path:
    packet = tmp_path / "legal.yaml"
    packet.write_text(
        "\n".join(
            [
                "id: legal-demo",
                "domain: legal",
                "entity_type: policy",
                "entity_name: Demo Policy",
                "key_facts:",
                "  - id: fact-1",
                "    text: a fact",
                "source_notes:",
                "  - source: Synthetic RDW demo data",
                "    accessed: '2026-06-26'",
                "    note: demo",
                "    fact_ids: [fact-1]",
                "confidence_level: low",
                "last_updated: '2026-06-26T12:00:00Z'",
            ]
        ),
        encoding="utf-8",
    )
    return packet


def test_disabled_domain_warns_then_errors(tmp_path: Path) -> None:
    packet = _disabled_domain_packet(tmp_path)

    lenient = validate_packet_file(packet, root=ROOT)
    assert lenient.ok
    assert any("registered but disabled: legal" in w for w in lenient.warnings)

    strict = validate_packet_file(packet, strict=True, root=ROOT)
    assert not strict.ok
    assert any("registered but disabled: legal" in e for e in strict.errors)

    allowed = validate_packet_file(packet, strict=True, root=ROOT, allow_disabled=True)
    assert allowed.ok


def test_compat_validate_packet_script() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate-packet.py"),
            str(ROOT / "knowledge" / "basketball" / "demo-guard-2026-demo.yaml"),
        ],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )

    assert "OK:" in result.stdout
