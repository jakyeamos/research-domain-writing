from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from rdw.cli import main
from rdw.validation import validate_claim_ledger_file, validate_packet_file
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


def test_negative_packets_and_claim_ledger_are_rejected() -> None:
    manifest = load_yaml_mapping(MANIFEST)
    negative = _case_list(manifest, "negative_cases")
    expected_errors = {
        "ranking-missing-context": "extensions.ranking missing metric_definition",
        "invented-tracking": "relevant_metrics[1] references unknown fact id",
        "small-sample-high-confidence": "player samples under 15 games require confidence_level: low",
        "synthetic-real-player": "synthetic/demo provenance is not allowed",
    }

    for case in negative:
        case_id = _string(case, "id")
        packet = ACCEPTANCE_ROOT / _string(case, "packet")
        if case_id == "claim-ledger-unknown-fact":
            ledger_result = validate_claim_ledger_file(
                packet,
                ACCEPTANCE_ROOT / _string(case, "qa"),
                root=ROOT,
                mature=True,
            )
            assert not ledger_result.ok
            assert any("references unknown fact id" in error for error in ledger_result.errors)
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
