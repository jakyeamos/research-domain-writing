from __future__ import annotations

import json
import re
from pathlib import Path
from typing import cast

import pytest

from rdw.cli import main
from rdw.validation import (
    validate_claim_ledger,
    validate_claim_ledger_file,
    validate_packet_file,
)
from rdw.yaml_io import YamlMapping, load_yaml_mapping

ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE_ROOT = ROOT / "examples" / "acceptance" / "basketball"
MANIFEST = ACCEPTANCE_ROOT / "acceptance-manifest.yaml"


def _string(mapping: YamlMapping, key: str) -> str:
    value = mapping.get(key)
    assert isinstance(value, str), f"{key} must be a string"
    return value


def _case_list(manifest: YamlMapping, key: str) -> list[YamlMapping]:
    value = manifest.get(key)
    assert isinstance(value, list)
    return [cast(YamlMapping, item) for item in value if isinstance(item, dict)]


def _claim_fact_ids(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    fact_ids: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        linked_ids = item.get("fact_ids")
        if isinstance(linked_ids, list):
            fact_ids.update(linked_id for linked_id in linked_ids if isinstance(linked_id, str))
    return fact_ids


def _markdown_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        _, separator, body = text.partition("\n---\n")
        if separator:
            return body
    return text


def _pipeline_path(case: YamlMapping, key: str) -> Path:
    value = case.get(key)
    assert isinstance(value, str), f"positive case is missing {key}"
    return ACCEPTANCE_ROOT / value


def test_mature_acceptance_manifest_covers_the_initial_surface() -> None:
    manifest = load_yaml_mapping(MANIFEST)
    assert manifest["example_only"] is True
    positive = _case_list(manifest, "positive_cases")
    negative = _case_list(manifest, "negative_cases")

    assert {_string(case, "id") for case in positive} == {
        "leaderboard-methodology",
        "player-stat-interpretation",
        "player-comparison",
        "team-fit",
        "bounded-projection",
    }
    assert {_string(case, "id") for case in negative} == {
        "ranking-missing-context",
        "invented-tracking",
        "small-sample-high-confidence",
        "synthetic-real-player",
        "claim-ledger-unknown-fact",
        "unsupported-injury",
        "forbidden-generic-praise",
    }


def test_source_grounded_packets_and_claim_ledgers_pass() -> None:
    manifest = load_yaml_mapping(MANIFEST)
    positive = _case_list(manifest, "positive_cases")

    for case in positive:
        packet = ACCEPTANCE_ROOT / _string(case, "packet")
        packet_result = validate_packet_file(packet, root=ROOT, mature=True)
        assert packet_result.ok, f"{packet} failed mature validation: {packet_result.errors}"

        qa = case.get("qa")
        if isinstance(qa, str):
            ledger_result = validate_claim_ledger_file(
                packet,
                ACCEPTANCE_ROOT / qa,
                root=ROOT,
                mature=True,
            )
            assert ledger_result.ok, f"{packet} claim ledger failed: {ledger_result.errors}"


def test_positive_cases_have_full_pipeline_and_humanizer_lineage() -> None:
    manifest = load_yaml_mapping(MANIFEST)
    for case in _case_list(manifest, "positive_cases"):
        case_id = _string(case, "id")
        required_stages = (
            "research_missing",
            "knowledge",
            "draft",
            "qa",
            "final",
            "humanizer_handoff",
        )
        for stage in required_stages:
            stage_path = _pipeline_path(case, stage)
            assert stage_path.is_file(), f"{case_id} missing {stage}: {stage_path}"
            assert stage_path.read_text(encoding="utf-8").strip()

        missing = load_yaml_mapping(_pipeline_path(case, "research_missing"))
        assert missing["status"] == "open"
        assert isinstance(missing.get("missing_info"), list)

        qa = load_yaml_mapping(_pipeline_path(case, "qa"))
        assert qa["pass"] is True
        assert qa["issues"] == []
        assert qa["blocking_issue_count"] == 0
        assert qa["needs_human_review"] is True

        draft_body = _markdown_body(_pipeline_path(case, "draft"))
        final_body = _markdown_body(_pipeline_path(case, "final"))
        assert draft_body != final_body
        draft_numbers = set(re.findall(r"\b\d+(?:\.\d+)?(?:-\d+)?\b", draft_body))
        final_numbers = set(re.findall(r"\b\d+(?:\.\d+)?(?:-\d+)?\b", final_body))
        assert final_numbers <= draft_numbers, f"{case_id} humanizer added numeric content"

        handoff = load_yaml_mapping(_pipeline_path(case, "humanizer_handoff"))
        assert handoff["status"] == "ready_for_human_graduation_review"
        assert handoff["facts_added"] is False
        assert handoff["qualifiers_preserved"] is True
        preserved_fact_ids = handoff.get("preserved_fact_ids")
        assert isinstance(preserved_fact_ids, list)
        assert _claim_fact_ids(qa.get("claim_ledger")) <= set(
            fact_id for fact_id in preserved_fact_ids if isinstance(fact_id, str)
        )

        secondary_packet = qa.get("secondary_packet")
        secondary_claims = qa.get("secondary_claim_ledger")
        if isinstance(secondary_packet, str):
            assert isinstance(secondary_claims, list), f"{case_id} lacks secondary claim ledger"
            secondary_ledger = cast(
                YamlMapping,
                {
                    "pass": qa.get("pass"),
                    "issues": qa.get("issues"),
                    "blocking_issue_count": qa.get("blocking_issue_count"),
                    "claim_ledger": secondary_claims,
                },
            )
            secondary_result = validate_claim_ledger(
                load_yaml_mapping(ACCEPTANCE_ROOT / secondary_packet),
                secondary_ledger,
                root=ROOT,
                mature=True,
            )
            assert secondary_result.ok, (
                f"{case_id} secondary claim ledger failed: {secondary_result.errors}"
            )
            assert _claim_fact_ids(secondary_claims) <= set(
                fact_id for fact_id in preserved_fact_ids if isinstance(fact_id, str)
            )


def test_negative_packets_and_claim_ledger_are_rejected() -> None:
    manifest = load_yaml_mapping(MANIFEST)
    negative = _case_list(manifest, "negative_cases")
    expected_errors = {
        "ranking-missing-context": "extensions.ranking missing metric_definition",
        "invented-tracking": "relevant_metrics[1] references unknown fact id",
        "small-sample-high-confidence": "player samples under 15 games require confidence_level: low",
        "synthetic-real-player": "synthetic/demo provenance is not allowed",
        "unsupported-injury": "draft contains unsupported injury/availability claim",
        "forbidden-generic-praise": "draft contains forbidden generic basketball phrase",
    }

    for case in negative:
        case_id = _string(case, "id")
        packet = ACCEPTANCE_ROOT / _string(case, "packet")
        qa = case.get("qa")
        if isinstance(qa, str):
            ledger_result = validate_claim_ledger_file(
                packet,
                ACCEPTANCE_ROOT / qa,
                root=ROOT,
                mature=True,
            )
            assert not ledger_result.ok
            expected = (
                "references unknown fact id"
                if case_id == "claim-ledger-unknown-fact"
                else expected_errors[case_id]
            )
            assert any(expected in error for error in ledger_result.errors)
            continue

        result = validate_packet_file(packet, root=ROOT, mature=True)
        assert not result.ok
        assert any(expected_errors[case_id] in error for error in result.errors)


def test_mature_validation_cli_and_claim_ledger_cli(
    capsys: pytest.CaptureFixture[str],
) -> None:
    packet = ACCEPTANCE_ROOT / "packets" / "ranking-usage-ts-change.yaml"
    ledger = ACCEPTANCE_ROOT / "qa" / "ranking-usage-ts-change.yaml"

    assert main(["validate-packet", str(packet), "--mature", "--root", str(ROOT), "--json"]) == 0
    packet_payload = json.loads(capsys.readouterr().out)
    assert packet_payload["ok"] is True

    assert (
        main(
            [
                "validate-claim-ledger",
                str(packet),
                str(ledger),
                "--mature",
                "--root",
                str(ROOT),
                "--json",
            ]
        )
        == 0
    )
    ledger_payload = json.loads(capsys.readouterr().out)
    assert ledger_payload["ok"] is True
