from __future__ import annotations

import re
from pathlib import Path
from typing import cast

from rdw.artifact_validation import validate_artifact_file, validate_artifact_request
from rdw.yaml_io import YamlMapping, load_yaml_mapping

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "acceptance" / "career" / "redacted-outreach-followup.yaml"


def _check_map(receipt: YamlMapping) -> dict[str, YamlMapping]:
    checks = receipt.get("checks")
    assert isinstance(checks, list)
    return {
        str(item["id"]): cast(YamlMapping, item)
        for item in checks
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def test_redacted_career_outreach_fixture_has_human_review_receipt() -> None:
    request = load_yaml_mapping(FIXTURE)
    receipt = validate_artifact_file(FIXTURE, root=ROOT)

    assert request["artifact_type"] == "outreach_followup_email"
    assert receipt["ok"] is True
    assert receipt["status"] == "approved_for_human_review"
    assert receipt["human_approval_required"] is True

    checks = _check_map(receipt)
    expected_passes = {
        "schema",
        "artifact_id",
        "artifact_profile",
        "channel",
        "intent",
        "content",
        "human_approval_boundary",
        "evidence_shape",
        "required_evidence",
        "claim_bindings",
        "claim_bindings_well_formed",
        "claim_bindings_in_content",
        "evidence_in_content",
        "body_words",
        "subject_words",
        "subject_characters",
        "sentences",
        "blocked_phrases",
        "clear_cta",
    }
    assert expected_passes <= set(checks)
    assert all(checks[check_id]["status"] == "pass" for check_id in expected_passes)
    assert "proof_link" not in checks


def test_redacted_career_outreach_fixture_has_no_external_or_identifying_data() -> None:
    request = load_yaml_mapping(FIXTURE)
    serialized = FIXTURE.read_text(encoding="utf-8")
    constraints = request.get("constraints")
    privacy = request.get("privacy")

    assert isinstance(constraints, dict)
    assert constraints["human_approval_required"] is True
    assert constraints["external_actions"] == []
    assert isinstance(privacy, dict)
    assert privacy["redacted"] is True
    assert privacy["source_scope"] == "private_sent_email_only"
    assert "[REDACTED]" in serialized
    assert "@" not in serialized
    assert not re.search(r"https?://", serialized, flags=re.IGNORECASE)
    assert not re.search(r"\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b", serialized)


def test_redacted_career_outreach_fixture_cannot_bypass_human_review() -> None:
    request = load_yaml_mapping(FIXTURE)
    constraints = request.get("constraints")
    assert isinstance(constraints, dict)
    constraints["human_approval_required"] = False

    receipt = validate_artifact_request(request, root=ROOT)
    checks = _check_map(receipt)

    assert receipt["ok"] is False
    assert receipt["status"] == "blocked"
    assert receipt["human_approval_required"] is True
    assert checks["human_approval_boundary"]["status"] == "fail"


def test_outreach_followup_rejects_supplied_binding_to_unknown_evidence() -> None:
    request = load_yaml_mapping(FIXTURE)
    request["claim_bindings"] = [
        {
            "claim": "An unsupported claim.",
            "evidence_ids": ["missing-evidence"],
        }
    ]

    receipt = validate_artifact_request(request, root=ROOT)
    checks = _check_map(receipt)

    assert receipt["ok"] is False
    assert receipt["status"] == "blocked"
    assert checks["claim_bindings_well_formed"]["status"] == "fail"


def test_outreach_followup_allows_no_bindings_when_profile_allows_zero() -> None:
    request = load_yaml_mapping(FIXTURE)
    request["claim_bindings"] = []

    receipt = validate_artifact_request(request, root=ROOT)
    checks = _check_map(receipt)

    assert receipt["ok"] is True
    assert checks["claim_bindings_well_formed"]["status"] == "pass"
