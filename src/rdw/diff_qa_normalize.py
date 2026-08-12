from __future__ import annotations

import json
from pathlib import Path

from rdw.diff_qa_reporting import issue
from rdw.diff_qa_support import (
    DIFF_QA_MODES,
    NormalizedArtifact,
    is_sha256,
    manifest_ledger_path,
    normalize_rules,
    normalized_text,
    plain,
    resolve_manifest_artifact,
    safe_relative,
    semantic_payload,
    short_hash,
    string,
    string_list,
    uncertainty,
    valid_timestamp,
    validate_rules,
    yaml_strings,
)
from rdw.validation import validate_packet
from rdw.yaml_io import YamlMapping, YamlValue, load_yaml_mapping


def validate_baseline_manifest(
    manifest: YamlMapping | None,
    manifest_path: Path,
    root: Path,
) -> dict[str, YamlValue] | None:
    if manifest is None:
        return issue(
            "DQA-001",
            "blocker",
            "baseline_invalid",
            "baseline",
            manifest_path.name,
            ["baseline manifest is missing or malformed"],
            "The approved baseline manifest cannot be read.",
            "Provide a valid diff_baseline manifest.",
        )
    required = {
        "schema_version": manifest.get("schema_version") == 1,
        "kind": manifest.get("kind") == "diff_baseline",
        "baseline_id": bool(string(manifest.get("baseline_id"))),
        "artifact_kind": string(manifest.get("artifact_kind")) in DIFF_QA_MODES,
        "artifact_path": bool(string(manifest.get("artifact_path"))),
        "content_sha256": is_sha256(string(manifest.get("content_sha256"))),
        "qa_status": manifest.get("qa_status") == "pass",
        "approved": manifest.get("approved") is True,
        "approved_by": string(manifest.get("approved_by")) == "human",
        "approved_at": valid_timestamp(string(manifest.get("approved_at"))),
    }
    missing = [field for field, valid in required.items() if not valid]
    if missing:
        return issue(
            "DQA-001",
            "blocker",
            "baseline_invalid",
            "baseline",
            string(manifest.get("baseline_id")) or manifest_path.name,
            [f"invalid baseline fields: {', '.join(missing)}"],
            "The manifest is not an explicitly approved, passing baseline.",
            "Repair the manifest or create a new approved baseline artifact.",
        )
    if resolve_manifest_artifact(root, manifest, "artifact_path") is None:
        return issue(
            "DQA-001",
            "blocker",
            "baseline_invalid",
            "baseline",
            string(manifest.get("baseline_id")),
            ["artifact_path must resolve to a file under the comparison root"],
            "The approved baseline artifact is unavailable or escapes the comparison root.",
            "Use a safe relative artifact_path and keep the approved artifact available.",
        )
    if (
        string(manifest.get("artifact_kind")) == "draft"
        and manifest_ledger_path(root, manifest) is None
    ):
        return issue(
            "DQA-001",
            "blocker",
            "baseline_invalid",
            "baseline",
            string(manifest.get("baseline_id")),
            ["draft baseline is missing claim_ledger_path"],
            "A draft baseline cannot be approved without a valid claim ledger.",
            "Add claim_ledger_path and approve the ledger-backed baseline.",
        )
    return None


def load_normalized_artifact(
    path: Path,
    *,
    mode: str,
    root: Path,
    ledger_path: Path | None,
    subject: str,
) -> tuple[NormalizedArtifact | None, list[dict[str, YamlValue]]]:
    if not path.is_file():
        return None, [
            issue(
                "DQA-010",
                "major",
                "indeterminate",
                subject,
                path.name,
                [f"{subject} artifact is missing: {path}"],
                "The required structured representation is unavailable.",
                "Provide a valid packet or draft claim ledger before diff QA.",
            )
        ]
    if mode == "packet":
        try:
            data = load_yaml_mapping(path)
        except ValueError as exc:
            return None, [
                issue(
                    "DQA-010",
                    "major",
                    "indeterminate",
                    subject,
                    path.name,
                    [f"invalid packet YAML: {exc}"],
                    "The packet cannot be normalized deterministically.",
                    "Repair the packet and rerun diff QA.",
                )
            ]
        result = validate_packet(data, strict=True, root=root)
        if not result.ok:
            code = "DQA-001" if subject == "baseline" else "DQA-010"
            category = "baseline_invalid" if subject == "baseline" else "indeterminate"
            return None, [
                issue(
                    code,
                    "major",
                    category,
                    subject,
                    string(data.get("id")) or path.name,
                    result.errors,
                    (
                        "The approved baseline packet failed strict validation required by diff QA."
                        if subject == "baseline"
                        else "The candidate packet failed strict validation required by diff QA."
                    ),
                    (
                        "Repair the baseline packet or approve a corrected baseline."
                        if subject == "baseline"
                        else "Repair the packet validation errors and rerun diff QA."
                    ),
                )
            ]
        artifact = normalize_packet(data)
        if artifact is None:
            return None, [
                issue(
                    "DQA-010",
                    "major",
                    "indeterminate",
                    subject,
                    path.name,
                    ["packet has no deterministic claim representation"],
                    "The packet cannot be compared without stable fact IDs.",
                    "Add stable key_facts IDs and source links.",
                )
            ]
        return artifact, packet_link_issues(data, artifact, subject=subject)

    if ledger_path is None or not ledger_path.is_file():
        return None, [
            issue(
                "DQA-009",
                "major",
                "ledger_missing",
                "draft",
                path.stem,
                ["draft mode requires an explicit claim ledger"],
                "Freeform Markdown is not a deterministic claim representation.",
                "Create a valid draft_claim_ledger sidecar and rerun diff QA.",
            )
        ]
    try:
        ledger = load_yaml_mapping(ledger_path)
    except ValueError as exc:
        return None, [
            issue(
                "DQA-009",
                "major",
                "ledger_missing",
                "draft",
                ledger_path.name,
                [f"invalid claim ledger YAML: {exc}"],
                "The draft claim ledger cannot be normalized.",
                "Repair the claim ledger and rerun diff QA.",
            )
        ]
    errors = validate_draft_ledger(ledger, ledger_path)
    if errors:
        return None, [
            issue(
                "DQA-009",
                "major",
                "ledger_missing",
                "draft",
                ledger_path.name,
                errors,
                "The explicit draft claim ledger is missing required evidence structure.",
                "Add stable claim IDs, evidence links, and deterministic rule results.",
            )
        ]
    declared_draft = safe_relative(root, string(ledger.get("draft_path")))
    if declared_draft != path:
        code = "DQA-001" if subject == "baseline" else "DQA-010"
        category = "baseline_invalid" if subject == "baseline" else "indeterminate"
        return None, [
            issue(
                code,
                "blocker" if subject == "baseline" else "major",
                category,
                subject,
                path.name,
                ["claim ledger draft_path does not match the draft artifact"],
                "The claim ledger is not bound to the draft being compared.",
                "Set draft_path to the exact local draft artifact and rerun diff QA.",
            )
        ]
    return normalize_draft_ledger(ledger), []


def normalize_packet(data: YamlMapping) -> NormalizedArtifact | None:
    facts = data.get("key_facts")
    source_notes = data.get("source_notes")
    if not isinstance(facts, list) or not isinstance(source_notes, list):
        return None
    sources: dict[str, YamlMapping] = {}
    source_ids_by_fact: dict[str, set[str]] = {}
    for note in source_notes:
        if not isinstance(note, dict):
            continue
        source = string(note.get("source"))
        source_type = string(note.get("source_type")) or "other"
        explicit_id = string(note.get("source_id"))
        source_id = explicit_id or "source-" + short_hash(
            {"source": normalized_text(source), "source_type": source_type}
        )
        fact_ids = string_list(note.get("fact_ids"))
        sources[source_id] = {
            "source_id": source_id,
            "source_normalized": normalized_text(source),
            "source_type": source_type,
            "evidence_boundary": normalized_text(
                string(note.get("evidence_boundary")) or string(note.get("note"))
            ),
            "fact_ids": yaml_strings(sorted(item for item in fact_ids if item)),
        }
        for fact_id in fact_ids:
            source_ids_by_fact.setdefault(fact_id, set()).add(source_id)

    claims: dict[str, YamlMapping] = {}
    for fact in facts:
        if not isinstance(fact, dict):
            continue
        fact_id = string(fact.get("id"))
        text = string(fact.get("text"))
        if not fact_id or not text:
            continue
        claims[fact_id] = {
            "claim_id": fact_id,
            "kind": "fact",
            "text_normalized": normalized_text(text),
            "fact_ids": [fact_id],
            "source_ids": yaml_strings(sorted(source_ids_by_fact.get(fact_id, set()))),
            "uncertainty": uncertainty(fact),
            "required": fact.get("required") is True,
            "semantic": semantic_payload(fact),
        }

    metrics = data.get("relevant_metrics")
    if isinstance(metrics, list):
        for metric in metrics:
            if not isinstance(metric, dict):
                continue
            fact_ids = string_list(metric.get("fact_ids"))
            source_ids = set(string_list(metric.get("source_ids")))
            for fact_id in fact_ids:
                source_ids.update(source_ids_by_fact.get(fact_id, set()))
            if not fact_ids and not source_ids:
                continue
            name = string(metric.get("name")) or "metric"
            claim_id = "metric:" + name
            claims[claim_id] = {
                "claim_id": claim_id,
                "kind": "metric",
                "text_normalized": normalized_text(json.dumps(plain(metric), sort_keys=True)),
                "fact_ids": yaml_strings(sorted(fact_ids)),
                "source_ids": yaml_strings(sorted(source_ids)),
                "uncertainty": "unknown",
                "required": metric.get("required") is True,
                "semantic": semantic_payload(metric, excluded={"fact_ids", "source_ids"}),
            }

    artifact_id = string(data.get("id"))
    if not artifact_id:
        return None
    return NormalizedArtifact(
        kind="packet",
        artifact_id=artifact_id,
        revision_id=string(data.get("revision_id")) or "rev-" + short_hash(plain(data)),
        claims=claims,
        sources=sources,
        rules=normalize_rules(data.get("rules") or data.get("rule_snapshot")),
    )


def packet_link_issues(
    data: YamlMapping,
    artifact: NormalizedArtifact,
    *,
    subject: str,
) -> list[dict[str, YamlValue]]:
    """Reject packet claims whose structured evidence links are not valid."""

    fact_values = data.get("key_facts")
    fact_ids = (
        {
            string(fact.get("id"))
            for fact in fact_values
            if isinstance(fact, dict) and string(fact.get("id"))
        }
        if isinstance(fact_values, list)
        else set()
    )
    source_ids = set(artifact.sources)
    issues: list[dict[str, YamlValue]] = []
    baseline = subject == "baseline"
    code = "DQA-001" if baseline else "DQA-002"
    category = "baseline_invalid" if baseline else "unsupported_claim"
    description = (
        "The approved baseline contains a claim without valid deterministic evidence links."
        if baseline
        else "The candidate contains a claim without valid deterministic evidence links."
    )
    suggested_fix = (
        "Repair the baseline packet links or approve a corrected baseline."
        if baseline
        else "Add valid fact/source links or remove the unsupported claim."
    )
    for claim_id in sorted(artifact.claims):
        claim = artifact.claims[claim_id]
        claim_fact_ids = set(string_list(claim.get("fact_ids")))
        claim_source_ids = set(string_list(claim.get("source_ids")))
        invalid_facts = sorted(claim_fact_ids - fact_ids)
        invalid_sources = sorted(claim_source_ids - source_ids)
        if not invalid_facts and not invalid_sources and (claim_source_ids or not baseline):
            continue
        evidence: list[str] = []
        if invalid_facts:
            evidence.append(f"unknown fact_ids: {', '.join(invalid_facts)}")
        if invalid_sources:
            evidence.append(f"unknown source_ids: {', '.join(invalid_sources)}")
        if not claim_source_ids and baseline:
            evidence.append("claim has no linked source_ids")
        issues.append(
            issue(
                code,
                "blocker",
                category,
                "metric" if claim.get("kind") == "metric" else "fact",
                claim_id,
                evidence,
                description,
                suggested_fix,
                baseline={"claim_id": claim_id} if baseline else None,
                candidate={"claim_id": claim_id} if not baseline else None,
            )
        )
    return issues


def normalize_draft_ledger(ledger: YamlMapping) -> NormalizedArtifact:
    claims: dict[str, YamlMapping] = {}
    raw_claims = ledger.get("claims")
    if isinstance(raw_claims, list):
        for claim in raw_claims:
            if not isinstance(claim, dict):
                continue
            claim_id = string(claim.get("claim_id"))
            if not claim_id:
                continue
            claims[claim_id] = {
                "claim_id": claim_id,
                "kind": "claim",
                "text_normalized": normalized_text(string(claim.get("text"))),
                "fact_ids": yaml_strings(sorted(string_list(claim.get("fact_ids")))),
                "source_ids": yaml_strings(sorted(string_list(claim.get("source_ids")))),
                "uncertainty": uncertainty(claim),
                "required": claim.get("required") is True,
                "semantic": semantic_payload(
                    claim,
                    excluded={"claim_id", "fact_ids", "source_ids", "uncertainty", "required"},
                ),
            }
    return NormalizedArtifact(
        kind="draft",
        artifact_id=string(ledger.get("output_id")) or string(ledger.get("draft_path")),
        revision_id="rev-" + short_hash(plain(ledger)),
        claims=claims,
        sources={},
        rules=normalize_rules(ledger.get("rules")),
    )


def validate_draft_ledger(ledger: YamlMapping, ledger_path: Path) -> list[str]:
    errors: list[str] = []
    if ledger.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if ledger.get("kind") != "draft_claim_ledger":
        errors.append("kind must be draft_claim_ledger")
    if not string(ledger.get("output_id")):
        errors.append("output_id must be a non-empty string")
    if not string(ledger.get("draft_path")):
        errors.append("draft_path must be a non-empty string")
    claims = ledger.get("claims")
    if not isinstance(claims, list):
        errors.append("claims must be a list")
    else:
        seen: set[str] = set()
        for index, claim in enumerate(claims, start=1):
            if not isinstance(claim, dict):
                errors.append(f"claims[{index}] must be a mapping")
                continue
            claim_id = string(claim.get("claim_id"))
            if not claim_id:
                errors.append(f"claims[{index}] missing claim_id")
            elif claim_id in seen:
                errors.append(f"claims duplicate claim_id: {claim_id}")
            seen.add(claim_id)
            if not string(claim.get("text")):
                errors.append(f"claims[{index}] missing text")
            if not string_list(claim.get("fact_ids")):
                errors.append(f"claims[{index}] must include fact_ids")
            if not string_list(claim.get("source_ids")):
                errors.append(f"claims[{index}] must include source_ids")
            uncertainty_value = claim.get("uncertainty")
            if uncertainty_value is not None and not isinstance(uncertainty_value, str):
                errors.append(f"claims[{index}] uncertainty must be a string")
    rules = ledger.get("rules")
    if rules is not None:
        errors.extend(validate_rules(rules))
    if not ledger_path.name:
        errors.append("claim ledger path must name a file")
    return errors
