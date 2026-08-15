from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path

from rdw.cli import main
from rdw.diff_qa import run_diff_qa, validate_diff_qa, validate_diff_qa_file
from rdw.yaml_io import YamlMapping, YamlValue, dump_yaml, load_yaml_mapping

ROOT = Path(__file__).resolve().parents[1]


def _fact(
    fact_id: str,
    text: str,
    *,
    required: bool = False,
    uncertainty: str | None = None,
) -> YamlMapping:
    fact: YamlMapping = {"id": fact_id, "text": text}
    if required:
        fact["required"] = True
    if uncertainty is not None:
        fact["uncertainty"] = uncertainty
    return fact


def _packet(
    facts: list[YamlMapping],
    source_fact_ids: list[str],
    *,
    source_note: str = "Local fixture evidence boundary.",
    rules: list[YamlMapping] | None = None,
) -> YamlMapping:
    fact_values: list[YamlValue] = [fact for fact in facts]
    source_fact_values: list[YamlValue] = [fact_id for fact_id in source_fact_ids]
    source_note_mapping: YamlMapping = {
        "source_id": "source-1",
        "source": "Local synthetic fixture source",
        "accessed": "2026-08-10",
        "note": source_note,
        "fact_ids": source_fact_values,
    }
    packet: YamlMapping = {
        "id": "fixture-packet-1",
        "domain": "general",
        "entity_type": "topic",
        "entity_name": "Diff-QA fixture",
        "key_facts": fact_values,
        "source_notes": [source_note_mapping],
        "confidence_level": "high",
        "last_updated": "2026-08-10T12:00:00Z",
    }
    if rules is not None:
        packet["rules"] = [rule for rule in rules]
    return packet


def _write(path: Path, data: YamlMapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_yaml(data), encoding="utf-8")


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _write_packet_baseline(root: Path, packet: YamlMapping) -> Path:
    artifact = root / "baseline.yaml"
    _write(artifact, packet)
    manifest: YamlMapping = {
        "schema_version": 1,
        "kind": "diff_baseline",
        "baseline_id": "fixture-baseline-1",
        "artifact_kind": "packet",
        "artifact_path": "baseline.yaml",
        "content_sha256": _sha256(artifact),
        "packet_id": "fixture-packet-1",
        "qa_status": "pass",
        "approved": True,
        "approved_by": "human",
        "approved_at": "2026-08-10T13:00:00Z",
    }
    manifest_path = root / "baseline-manifest.yaml"
    _write(manifest_path, manifest)
    return manifest_path


def _write_draft_baseline(root: Path) -> Path:
    draft = root / "baseline.md"
    draft.write_text("A local fixture draft.\n", encoding="utf-8")
    claim: YamlMapping = {
        "claim_id": "claim-1",
        "text": "The fixture is supported.",
        "fact_ids": ["fact-1"],
        "source_ids": ["source-1"],
    }
    claims: list[YamlValue] = [claim]
    ledger: YamlMapping = {
        "schema_version": 1,
        "kind": "draft_claim_ledger",
        "output_id": "fixture-draft-1",
        "draft_path": "baseline.md",
        "claims": claims,
    }
    ledger_path = root / "baseline-claims.yaml"
    _write(ledger_path, ledger)
    manifest: YamlMapping = {
        "schema_version": 1,
        "kind": "diff_baseline",
        "baseline_id": "fixture-draft-baseline-1",
        "artifact_kind": "draft",
        "artifact_path": "baseline.md",
        "content_sha256": _sha256(draft),
        "claim_ledger_path": "baseline-claims.yaml",
        "qa_status": "pass",
        "approved": True,
        "approved_by": "human",
        "approved_at": "2026-08-10T13:00:00Z",
    }
    manifest_path = root / "draft-baseline-manifest.yaml"
    _write(manifest_path, manifest)
    return manifest_path


def _codes(report: YamlMapping) -> set[str]:
    issues = report.get("issues")
    if not isinstance(issues, list):
        return set()
    return {
        str(issue.get("code"))
        for issue in issues
        if isinstance(issue, dict) and isinstance(issue.get("code"), str)
    }


def _status(report: YamlMapping) -> str:
    summary = report.get("summary")
    assert isinstance(summary, dict)
    return str(summary["status"])


def test_packet_supported_addition_passes(tmp_path: Path) -> None:
    baseline = _packet(
        [
            _fact("fact-1", "The fixture has a stable source."),
            _fact("fact-2", "The baseline is small."),
        ],
        ["fact-1", "fact-2"],
    )
    manifest = _write_packet_baseline(tmp_path, baseline)
    candidate = _packet(
        [
            _fact("fact-1", "The fixture has a stable source."),
            _fact("fact-2", "The baseline is small."),
            _fact("fact-3", "The candidate adds a supported fact."),
        ],
        ["fact-1", "fact-2", "fact-3"],
    )
    candidate_path = tmp_path / "candidate.yaml"
    _write(candidate_path, candidate)

    report = run_diff_qa(manifest, candidate_path, root=tmp_path)

    assert _status(report) == "pass"
    assert _codes(report) == set()
    summary = report["summary"]
    assert isinstance(summary, dict)
    counts = summary["counts"]
    assert isinstance(counts, dict)
    assert counts["claims_added"] == 1
    assert validate_diff_qa(report).ok


def test_packet_metric_inherits_source_link_from_fact_ids(tmp_path: Path) -> None:
    baseline = _packet([_fact("fact-1", "The baseline is supported.")], ["fact-1"])
    manifest = _write_packet_baseline(tmp_path, baseline)
    candidate = _packet([_fact("fact-1", "The baseline is supported.")], ["fact-1"])
    candidate["relevant_metrics"] = [
        {
            "name": "supported metric",
            "value": "42",
            "fact_ids": ["fact-1"],
        }
    ]
    candidate_path = tmp_path / "candidate.yaml"
    _write(candidate_path, candidate)

    report = run_diff_qa(manifest, candidate_path, root=tmp_path)

    assert _status(report) == "pass"
    summary = report["summary"]
    assert isinstance(summary, dict)
    counts = summary["counts"]
    assert isinstance(counts, dict)
    assert counts["claims_added"] == 1


def test_packet_metric_with_unknown_fact_is_unsupported(tmp_path: Path) -> None:
    baseline = _packet([_fact("fact-1", "The baseline is supported.")], ["fact-1"])
    manifest = _write_packet_baseline(tmp_path, baseline)
    candidate = _packet([_fact("fact-1", "The baseline is supported.")], ["fact-1"])
    candidate["relevant_metrics"] = [
        {
            "name": "unsupported metric",
            "value": "42",
            "fact_ids": ["missing-fact"],
        }
    ]
    candidate_path = tmp_path / "candidate.yaml"
    _write(candidate_path, candidate)

    report = run_diff_qa(manifest, candidate_path, root=tmp_path)

    assert _status(report) == "fail"
    assert "DQA-002" in _codes(report)


def test_report_validator_rejects_forged_issue_counts(tmp_path: Path) -> None:
    baseline = _packet([_fact("fact-1", "The baseline is supported.")], ["fact-1"])
    manifest = _write_packet_baseline(tmp_path, baseline)
    candidate_path = tmp_path / "candidate.yaml"
    _write(candidate_path, baseline)
    report = run_diff_qa(manifest, candidate_path, root=tmp_path)
    summary = report["summary"]
    assert isinstance(summary, dict)
    summary["minor_issue_count"] = 1

    result = validate_diff_qa(report)

    assert not result.ok
    assert any("minor_issue_count" in error for error in result.errors)


def test_baseline_requires_human_approval_marker(tmp_path: Path) -> None:
    baseline = _packet([_fact("fact-1", "The baseline is supported.")], ["fact-1"])
    manifest = _write_packet_baseline(tmp_path, baseline)
    manifest_data = load_yaml_mapping(manifest)
    manifest_data["approved_by"] = "agent"
    _write(manifest, manifest_data)
    candidate_path = tmp_path / "candidate.yaml"
    _write(candidate_path, baseline)

    report = run_diff_qa(manifest, candidate_path, root=tmp_path)

    assert _status(report) == "fail"
    assert "DQA-001" in _codes(report)


def test_packet_unsupported_addition_blocks(tmp_path: Path) -> None:
    baseline = _packet([_fact("fact-1", "The baseline is supported.")], ["fact-1"])
    manifest = _write_packet_baseline(tmp_path, baseline)
    candidate = _packet(
        [_fact("fact-1", "The baseline is supported."), _fact("fact-2", "No source is linked.")],
        ["fact-1"],
    )
    candidate_path = tmp_path / "candidate.yaml"
    _write(candidate_path, candidate)

    report = run_diff_qa(manifest, candidate_path, root=tmp_path)

    assert _status(report) == "fail"
    assert "DQA-002" in _codes(report)


def test_packet_source_weakening_and_source_change_are_reported(tmp_path: Path) -> None:
    baseline = _packet(
        [_fact("fact-1", "The baseline is supported."), _fact("fact-2", "Another supported fact.")],
        ["fact-1", "fact-2"],
    )
    manifest = _write_packet_baseline(tmp_path, baseline)
    weakened = _packet(
        [_fact("fact-1", "The baseline is supported."), _fact("fact-2", "Another supported fact.")],
        ["fact-2"],
    )
    weakened_path = tmp_path / "weakened.yaml"
    _write(weakened_path, weakened)

    report = run_diff_qa(manifest, weakened_path, root=tmp_path)
    assert _status(report) == "fail"
    assert "DQA-003" in _codes(report)

    changed = _packet(
        [_fact("fact-1", "The baseline is supported.")],
        ["fact-1"],
        source_note="A changed evidence boundary.",
    )
    changed_path = tmp_path / "changed-source.yaml"
    _write(changed_path, changed)
    changed_report = run_diff_qa(manifest, changed_path, root=tmp_path)
    assert _status(changed_report) == "fail"
    assert "DQA-008" in _codes(changed_report)


def test_packet_claim_and_uncertainty_changes_block(tmp_path: Path) -> None:
    baseline = _packet(
        [
            _fact("fact-1", "The baseline is supported."),
            _fact("fact-2", "The caveat is required.", uncertainty="required"),
        ],
        ["fact-1", "fact-2"],
    )
    manifest = _write_packet_baseline(tmp_path, baseline)
    candidate = _packet(
        [
            _fact("fact-1", "The baseline changed."),
            _fact("fact-2", "The caveat is required."),
        ],
        ["fact-1", "fact-2"],
    )
    candidate_path = tmp_path / "candidate.yaml"
    _write(candidate_path, candidate)

    report = run_diff_qa(manifest, candidate_path, root=tmp_path)

    assert _status(report) == "fail"
    assert {"DQA-004", "DQA-006"}.issubset(_codes(report))


def test_packet_optional_removal_passes_with_review_but_required_removal_fails(
    tmp_path: Path,
) -> None:
    baseline = _packet(
        [_fact("fact-1", "The baseline is supported."), _fact("fact-2", "Optional context.")],
        ["fact-1", "fact-2"],
    )
    manifest = _write_packet_baseline(tmp_path, baseline)
    optional_candidate = _packet([_fact("fact-1", "The baseline is supported.")], ["fact-1"])
    optional_path = tmp_path / "optional.yaml"
    _write(optional_path, optional_candidate)
    optional_report = run_diff_qa(manifest, optional_path, root=tmp_path)

    assert _status(optional_report) == "pass"
    assert "DQA-005" in _codes(optional_report)
    optional_summary = optional_report["summary"]
    assert isinstance(optional_summary, dict)
    assert optional_summary["needs_human_review"] is True

    required_baseline = _packet(
        [
            _fact("fact-1", "The baseline is supported."),
            _fact("fact-2", "Required context.", required=True),
        ],
        ["fact-1", "fact-2"],
    )
    required_root = tmp_path / "required"
    required_manifest = _write_packet_baseline(required_root, required_baseline)
    required_path = required_root / "required-candidate.yaml"
    _write(required_path, _packet([_fact("fact-1", "The baseline is supported.")], ["fact-1"]))
    required_report = run_diff_qa(
        required_manifest,
        required_path,
        root=required_root,
    )
    assert _status(required_report) == "fail"
    assert "DQA-005" in _codes(required_report)


def test_packet_rule_regression_and_unknown_are_not_passes(tmp_path: Path) -> None:
    baseline = _packet(
        [_fact("fact-1", "The baseline is supported.")],
        ["fact-1"],
        rules=[{"rule_id": "rule-1", "status": "pass"}],
    )
    manifest = _write_packet_baseline(tmp_path, baseline)
    failed = _packet(
        [_fact("fact-1", "The baseline is supported.")],
        ["fact-1"],
        rules=[{"rule_id": "rule-1", "status": "fail"}],
    )
    failed_path = tmp_path / "rule-failed.yaml"
    _write(failed_path, failed)
    failed_report = run_diff_qa(manifest, failed_path, root=tmp_path)
    assert _status(failed_report) == "fail"
    assert "DQA-007" in _codes(failed_report)

    unknown = _packet(
        [_fact("fact-1", "The baseline is supported.")],
        ["fact-1"],
        rules=[{"rule_id": "rule-1", "status": "unknown"}],
    )
    unknown_path = tmp_path / "rule-unknown.yaml"
    _write(unknown_path, unknown)
    unknown_report = run_diff_qa(manifest, unknown_path, root=tmp_path)
    assert _status(unknown_report) == "indeterminate"
    assert "DQA-010" in _codes(unknown_report)


def test_baseline_hash_mismatch_blocks(tmp_path: Path) -> None:
    baseline = _packet([_fact("fact-1", "The baseline is supported.")], ["fact-1"])
    manifest = _write_packet_baseline(tmp_path, baseline)
    baseline_path = tmp_path / "baseline.yaml"
    baseline_path.write_text(
        dump_yaml(_packet([_fact("fact-1", "The baseline was tampered.")], ["fact-1"])),
        encoding="utf-8",
    )
    candidate_path = tmp_path / "candidate.yaml"
    _write(candidate_path, baseline)

    report = run_diff_qa(manifest, candidate_path, root=tmp_path)

    assert _status(report) == "fail"
    assert "DQA-001" in _codes(report)


def test_draft_mode_requires_ledger_and_accepts_supported_addition(tmp_path: Path) -> None:
    manifest = _write_draft_baseline(tmp_path)
    candidate_path = tmp_path / "candidate.md"
    candidate_path.write_text("A candidate fixture draft.\n", encoding="utf-8")

    missing = run_diff_qa(manifest, candidate_path, root=tmp_path)

    assert _status(missing) == "indeterminate"
    assert "DQA-009" in _codes(missing)
    assert validate_diff_qa(missing).ok

    claim: YamlMapping = {
        "claim_id": "claim-2",
        "text": "The candidate adds a supported claim.",
        "fact_ids": ["fact-2"],
        "source_ids": ["source-1"],
    }
    ledger: YamlMapping = {
        "schema_version": 1,
        "kind": "draft_claim_ledger",
        "output_id": "fixture-draft-1",
        "draft_path": "candidate.md",
        "claims": [
            {
                "claim_id": "claim-1",
                "text": "The fixture is supported.",
                "fact_ids": ["fact-1"],
                "source_ids": ["source-1"],
            },
            claim,
        ],
    }
    ledger_path = tmp_path / "candidate-claims.yaml"
    _write(ledger_path, ledger)
    supported = run_diff_qa(
        manifest,
        candidate_path,
        root=tmp_path,
        candidate_ledger_path=ledger_path,
    )

    assert _status(supported) == "pass"
    assert _codes(supported) == set()


def test_diff_qa_cli_writes_report_and_returns_status(tmp_path: Path, capsys) -> None:
    baseline = _packet([_fact("fact-1", "The baseline is supported.")], ["fact-1"])
    manifest = _write_packet_baseline(tmp_path, baseline)
    candidate_path = tmp_path / "candidate.yaml"
    _write(candidate_path, baseline)
    output = tmp_path / "outputs" / "qa" / "fixture-diff.yaml"

    assert (
        main(
            [
                "diff-qa",
                str(manifest),
                str(candidate_path),
                "--root",
                str(tmp_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert "diff_qa: pass" in capsys.readouterr().out
    report = load_yaml_mapping(output)
    assert _status(report) == "pass"
    assert validate_diff_qa_file(output).ok


def test_diff_qa_handles_missing_unsafe_and_malformed_artifacts(tmp_path: Path) -> None:
    baseline = _packet([_fact("fact-1", "The baseline is supported.")], ["fact-1"])
    manifest = _write_packet_baseline(tmp_path, baseline)
    candidate_path = tmp_path / "candidate.yaml"
    _write(candidate_path, baseline)

    outside_root = tmp_path / "comparison-root"
    outside_root.mkdir()
    outside_path = tmp_path / "outside.yaml"
    _write(outside_path, baseline)
    outside = run_diff_qa(manifest, outside_path, root=outside_root)
    assert _status(outside) == "indeterminate"
    assert "DQA-010" in _codes(outside)

    missing_manifest = run_diff_qa(
        tmp_path / "missing-manifest.yaml",
        candidate_path,
        root=tmp_path,
    )
    assert _status(missing_manifest) == "fail"
    assert "DQA-001" in _codes(missing_manifest)

    malformed_manifest = tmp_path / "malformed-manifest.yaml"
    malformed_manifest.write_text("kind: [broken\n", encoding="utf-8")
    malformed = run_diff_qa(malformed_manifest, candidate_path, root=tmp_path)
    assert _status(malformed) == "fail"
    assert "DQA-001" in _codes(malformed)

    missing_candidate = run_diff_qa(
        manifest,
        tmp_path / "missing-candidate.yaml",
        root=tmp_path,
    )
    assert _status(missing_candidate) == "indeterminate"
    assert "DQA-010" in _codes(missing_candidate)

    malformed_candidate = tmp_path / "malformed-candidate.yaml"
    malformed_candidate.write_text("domain: [broken\n", encoding="utf-8")
    malformed_candidate_report = run_diff_qa(manifest, malformed_candidate, root=tmp_path)
    assert _status(malformed_candidate_report) == "indeterminate"
    assert "DQA-010" in _codes(malformed_candidate_report)

    invalid_timestamp = load_yaml_mapping(manifest)
    invalid_timestamp["approved_at"] = "not-a-timestamp"
    _write(manifest, invalid_timestamp)
    invalid_timestamp_report = run_diff_qa(manifest, candidate_path, root=tmp_path)
    assert _status(invalid_timestamp_report) == "fail"
    assert "DQA-001" in _codes(invalid_timestamp_report)

    unsafe_path = load_yaml_mapping(manifest)
    unsafe_path["approved_at"] = "2026-08-10T13:00:00Z"
    unsafe_path["artifact_path"] = "../baseline.yaml"
    _write(manifest, unsafe_path)
    unsafe_report = run_diff_qa(manifest, candidate_path, root=tmp_path)
    assert _status(unsafe_report) == "fail"
    assert "DQA-001" in _codes(unsafe_report)


def test_diff_qa_rejects_invalid_baseline_metadata_and_identity(tmp_path: Path) -> None:
    baseline = _packet([_fact("fact-1", "The baseline is supported.")], ["fact-1"])
    manifest = _write_packet_baseline(tmp_path, baseline)
    candidate_path = tmp_path / "candidate.yaml"
    _write(candidate_path, baseline)

    manifest_data = load_yaml_mapping(manifest)
    manifest_data["packet_id"] = "wrong-packet"
    _write(manifest, manifest_data)
    packet_id_report = run_diff_qa(manifest, candidate_path, root=tmp_path)
    assert _status(packet_id_report) == "fail"
    assert "DQA-001" in _codes(packet_id_report)

    manifest_data["packet_id"] = "fixture-packet-1"
    manifest_data["packet_revision_id"] = "wrong-revision"
    _write(manifest, manifest_data)
    revision_report = run_diff_qa(manifest, candidate_path, root=tmp_path)
    assert _status(revision_report) == "fail"
    assert "DQA-001" in _codes(revision_report)

    manifest_data.pop("packet_revision_id", None)
    _write(manifest, manifest_data)
    candidate = deepcopy(baseline)
    candidate["id"] = "unrelated-packet"
    unrelated_path = tmp_path / "unrelated.yaml"
    _write(unrelated_path, candidate)
    unrelated_report = run_diff_qa(manifest, unrelated_path, root=tmp_path)
    assert _status(unrelated_report) == "indeterminate"
    assert "DQA-010" in _codes(unrelated_report)

    invalid_baseline_root = tmp_path / "invalid-baseline"
    invalid_baseline = _packet([_fact("fact-1", "The baseline is supported.")], ["fact-1"])
    invalid_manifest = _write_packet_baseline(invalid_baseline_root, invalid_baseline)
    invalid_artifact = invalid_baseline_root / "baseline.yaml"
    invalid_artifact.write_text("id: incomplete\n", encoding="utf-8")
    invalid_manifest_data = load_yaml_mapping(invalid_manifest)
    invalid_manifest_data["content_sha256"] = _sha256(invalid_artifact)
    _write(invalid_manifest, invalid_manifest_data)
    invalid_baseline_report = run_diff_qa(
        invalid_manifest,
        invalid_baseline_root / "candidate.yaml",
        root=invalid_baseline_root,
    )
    assert _status(invalid_baseline_report) == "fail"
    assert "DQA-001" in _codes(invalid_baseline_report)


def test_diff_qa_covers_packet_evidence_normalization_edges(tmp_path: Path) -> None:
    baseline = _packet([_fact("fact-1", "The baseline is supported.")], ["fact-1"])
    manifest = _write_packet_baseline(tmp_path, baseline)
    candidate = _packet([_fact("fact-1", "The baseline is supported.")], ["fact-1"])
    source_notes = candidate["source_notes"]
    assert isinstance(source_notes, list)
    assert isinstance(source_notes[0], dict)
    source_notes[0].pop("source_id", None)
    facts = candidate["key_facts"]
    assert isinstance(facts, list)
    assert isinstance(facts[0], dict)
    facts[0]["uncertainty_required"] = True
    candidate["relevant_metrics"] = [
        {"name": "orphan metric", "value": "42"},
        {"name": "unlinked metric", "value": "43", "source_ids": ["missing-source"]},
    ]
    candidate_path = tmp_path / "candidate-edges.yaml"
    _write(candidate_path, candidate)

    report = run_diff_qa(manifest, candidate_path, root=tmp_path)

    assert _status(report) == "fail"
    assert "DQA-002" in _codes(report)

    baseline_without_source_root = tmp_path / "baseline-without-source"
    baseline_without_source = _packet([_fact("fact-1", "No source link.")], [])
    baseline_without_source_manifest = _write_packet_baseline(
        baseline_without_source_root,
        baseline_without_source,
    )
    baseline_without_source_candidate = baseline_without_source_root / "candidate.yaml"
    _write(baseline_without_source_candidate, baseline_without_source)
    baseline_without_source_report = run_diff_qa(
        baseline_without_source_manifest,
        baseline_without_source_candidate,
        root=baseline_without_source_root,
    )
    assert _status(baseline_without_source_report) == "fail"
    assert "DQA-001" in _codes(baseline_without_source_report)


def test_diff_qa_covers_draft_ledger_failures(tmp_path: Path) -> None:
    manifest = _write_draft_baseline(tmp_path)
    candidate_path = tmp_path / "candidate.md"
    candidate_path.write_text("A candidate fixture draft.\n", encoding="utf-8")

    malformed_ledger = tmp_path / "malformed-claims.yaml"
    malformed_ledger.write_text("claims: [broken\n", encoding="utf-8")
    malformed_report = run_diff_qa(
        manifest,
        candidate_path,
        root=tmp_path,
        candidate_ledger_path=malformed_ledger,
    )
    assert _status(malformed_report) == "indeterminate"
    assert "DQA-009" in _codes(malformed_report)

    invalid_ledger = tmp_path / "invalid-claims.yaml"
    _write(
        invalid_ledger,
        {
            "schema_version": 1,
            "kind": "draft_claim_ledger",
            "output_id": "fixture-draft-1",
            "draft_path": "candidate.md",
            "claims": [
                None,
                {"claim_id": "duplicate", "text": "", "fact_ids": [], "source_ids": []},
                {
                    "claim_id": "duplicate",
                    "text": "A claim.",
                    "fact_ids": ["fact-1"],
                    "source_ids": ["source-1"],
                    "uncertainty": 42,
                },
            ],
            "rules": [
                None,
                {"rule_id": "rule-1", "status": "not-a-status"},
                {"rule_id": "rule-1", "status": "pass"},
            ],
        },
    )
    invalid_report = run_diff_qa(
        manifest,
        candidate_path,
        root=tmp_path,
        candidate_ledger_path=invalid_ledger,
    )
    assert _status(invalid_report) == "indeterminate"
    assert "DQA-009" in _codes(invalid_report)

    mismatched_ledger = tmp_path / "mismatched-claims.yaml"
    _write(
        mismatched_ledger,
        {
            "schema_version": 1,
            "kind": "draft_claim_ledger",
            "output_id": "fixture-draft-1",
            "draft_path": "other.md",
            "claims": [
                {
                    "claim_id": "claim-1",
                    "text": "The fixture is supported.",
                    "fact_ids": ["fact-1"],
                    "source_ids": ["source-1"],
                }
            ],
        },
    )
    mismatched_report = run_diff_qa(
        manifest,
        candidate_path,
        root=tmp_path,
        candidate_ledger_path=mismatched_ledger,
    )
    assert _status(mismatched_report) == "indeterminate"
    assert "DQA-010" in _codes(mismatched_report)

    missing_ledger_manifest = load_yaml_mapping(manifest)
    missing_ledger_manifest.pop("claim_ledger_path", None)
    _write(manifest, missing_ledger_manifest)
    missing_ledger_baseline = run_diff_qa(manifest, candidate_path, root=tmp_path)
    assert _status(missing_ledger_baseline) == "fail"
    assert "DQA-001" in _codes(missing_ledger_baseline)


def test_diff_qa_validator_rejects_malformed_reports(tmp_path: Path) -> None:
    baseline = _packet([_fact("fact-1", "The baseline is supported.")], ["fact-1"])
    manifest = _write_packet_baseline(tmp_path, baseline)
    candidate_path = tmp_path / "candidate.yaml"
    _write(candidate_path, baseline)
    valid_report = run_diff_qa(manifest, candidate_path, root=tmp_path)

    missing_comparison = deepcopy(valid_report)
    missing_comparison.pop("comparison", None)
    assert not validate_diff_qa(missing_comparison).ok

    missing_summary = deepcopy(valid_report)
    missing_summary.pop("summary", None)
    assert not validate_diff_qa(missing_summary).ok

    malformed = deepcopy(valid_report)
    malformed["comparison"] = {
        "mode": "unknown",
        "baseline": {"sha256": "bad", "path": ""},
        "candidate": "not-a-mapping",
    }
    malformed["summary"] = {
        "status": "fail",
        "pass": True,
        "needs_human_review": "yes",
        "counts": {
            "claims_added": True,
            "claims_removed": -1,
            "claims_changed": "bad",
            "source_links_removed": 0,
            "uncertainty_removed": 0,
            "rules_regressed": 0,
        },
        "blocking_issue_count": "bad",
        "major_issue_count": -1,
        "minor_issue_count": 0,
    }
    malformed["issues"] = [
        None,
        {
            "code": "DQA-999",
            "severity": "not-a-severity",
            "id": "duplicate",
            "category": "",
            "subject_type": "",
            "description": "",
        },
        {
            "code": "DQA-001",
            "severity": "blocker",
            "id": "duplicate",
            "category": "baseline_invalid",
            "subject_type": "baseline",
            "description": "A blocker.",
        },
        {
            "code": "DQA-002",
            "severity": "major",
            "id": "major",
            "category": "unsupported_claim",
            "subject_type": "fact",
            "description": "A major issue.",
        },
        {"code": "DQA-003", "severity": "minor", "id": ""},
    ]
    malformed_result = validate_diff_qa(malformed)
    assert not malformed_result.ok
    assert any("unknown code" in error for error in malformed_result.errors)

    no_blockers = deepcopy(valid_report)
    no_blockers["summary"] = {
        "status": "fail",
        "pass": False,
        "needs_human_review": True,
        "blocking_issue_count": 0,
        "major_issue_count": 0,
        "minor_issue_count": 0,
        "counts": {
            key: 0
            for key in (
                "claims_added",
                "claims_removed",
                "claims_changed",
                "source_links_removed",
                "uncertainty_removed",
                "rules_regressed",
            )
        },
    }
    no_blockers["issues"] = []
    assert not validate_diff_qa(no_blockers).ok

    indeterminate = deepcopy(valid_report)
    indeterminate["summary"] = {
        "status": "indeterminate",
        "pass": True,
        "needs_human_review": False,
        "blocking_issue_count": 0,
        "major_issue_count": 0,
        "minor_issue_count": 0,
        "counts": {
            key: 0
            for key in (
                "claims_added",
                "claims_removed",
                "claims_changed",
                "source_links_removed",
                "uncertainty_removed",
                "rules_regressed",
            )
        },
    }
    indeterminate["issues"] = []
    assert not validate_diff_qa(indeterminate).ok

    invalid_file = tmp_path / "invalid-report.yaml"
    invalid_file.write_text("summary: [broken\n", encoding="utf-8")
    assert not validate_diff_qa_file(invalid_file).ok
    assert not validate_diff_qa_file(tmp_path / "missing-report.yaml").ok
