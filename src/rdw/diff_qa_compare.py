from __future__ import annotations

from rdw.diff_qa_reporting import dedupe_issues, issue
from rdw.diff_qa_support import (
    NormalizedArtifact,
    empty_counts,
    source_semantic,
    string,
    string_list,
    yaml_strings,
)
from rdw.yaml_io import YamlValue


def compare_artifacts(
    baseline: NormalizedArtifact,
    candidate: NormalizedArtifact,
) -> tuple[list[dict[str, YamlValue]], dict[str, int]]:
    issues: list[dict[str, YamlValue]] = []
    counts = empty_counts()
    baseline_claims = baseline.claims
    candidate_claims = candidate.claims
    for claim_id in sorted(candidate_claims.keys() - baseline_claims.keys()):
        counts["claims_added"] += 1
        claim = candidate_claims[claim_id]
        if not string_list(claim.get("source_ids")):
            issues.append(
                issue(
                    "DQA-002",
                    "blocker",
                    "unsupported_claim",
                    "claim",
                    claim_id,
                    ["candidate claim has no linked source_ids"],
                    "The candidate adds a claim without deterministic evidence support.",
                    "Add a valid evidence link or remove the claim.",
                    candidate={"claim_id": claim_id, "source_ids": claim.get("source_ids", [])},
                )
            )

    for claim_id in sorted(baseline_claims.keys() - candidate_claims.keys()):
        counts["claims_removed"] += 1
        claim = baseline_claims[claim_id]
        severity = "minor" if claim.get("required") is not True else "major"
        issues.append(
            issue(
                "DQA-005",
                severity,
                "claim_removed",
                "claim",
                claim_id,
                ["baseline claim is absent from candidate"],
                "The candidate removed a baseline claim.",
                "Restore the claim or record an explicit human decision for its removal.",
                baseline={"claim_id": claim_id, "required": claim.get("required") is True},
            )
        )

    for claim_id in sorted(baseline_claims.keys() & candidate_claims.keys()):
        old = baseline_claims[claim_id]
        new = candidate_claims[claim_id]
        if old.get("semantic") != new.get("semantic"):
            counts["claims_changed"] += 1
            issues.append(
                issue(
                    "DQA-004",
                    "major",
                    "claim_changed",
                    "claim",
                    claim_id,
                    ["stable claim ID has a changed semantic representation"],
                    "The candidate changes a claim without deterministic equivalence.",
                    "Restore the baseline claim or send the change through human review.",
                    baseline={"claim_id": claim_id, "semantic": old.get("semantic")},
                    candidate={"claim_id": claim_id, "semantic": new.get("semantic")},
                )
            )

        old_sources = set(string_list(old.get("source_ids")))
        new_sources = set(string_list(new.get("source_ids")))
        removed_sources = old_sources - new_sources
        if removed_sources:
            counts["source_links_removed"] += len(removed_sources)
            code = "DQA-003" if not new_sources else "DQA-008"
            category = "evidence_removed" if code == "DQA-003" else "source_changed"
            issues.append(
                issue(
                    code,
                    "major",
                    category,
                    "claim",
                    claim_id,
                    [f"removed source links: {', '.join(sorted(removed_sources))}"],
                    "The candidate weakens or changes the evidence boundary for a retained claim.",
                    "Restore the source linkage or obtain an explicit human review decision.",
                    baseline={"source_ids": yaml_strings(sorted(old_sources))},
                    candidate={"source_ids": yaml_strings(sorted(new_sources))},
                )
            )

        old_uncertainty = string(old.get("uncertainty"))
        new_uncertainty = string(new.get("uncertainty"))
        if old_uncertainty == "required" and new_uncertainty != "required":
            counts["uncertainty_removed"] += 1
            issues.append(
                issue(
                    "DQA-006",
                    "major",
                    "uncertainty_removed",
                    "claim",
                    claim_id,
                    [
                        f"required uncertainty changed from required to {new_uncertainty or 'missing'}"
                    ],
                    "The candidate removes a required uncertainty or caveat.",
                    "Restore the uncertainty language or obtain explicit human review.",
                    baseline={"uncertainty": old_uncertainty},
                    candidate={"uncertainty": new_uncertainty},
                )
            )

    for source_id in sorted(set(baseline.sources) & set(candidate.sources)):
        if source_semantic(baseline.sources[source_id]) != source_semantic(
            candidate.sources[source_id]
        ):
            issues.append(
                issue(
                    "DQA-008",
                    "major",
                    "source_changed",
                    "source",
                    source_id,
                    ["source identity or evidence boundary changed"],
                    "The candidate changes source metadata used by the claim graph.",
                    "Restore the source boundary or obtain human review.",
                    baseline=baseline.sources[source_id],
                    candidate=candidate.sources[source_id],
                )
            )

    for rule_id in sorted(set(baseline.rules) | set(candidate.rules)):
        old = baseline.rules.get(rule_id)
        new = candidate.rules.get(rule_id)
        old_status = string(old.get("status")) if old else "unknown"
        new_status = string(new.get("status")) if new else "unknown"
        if old_status == "pass" and new_status == "fail":
            counts["rules_regressed"] += 1
            issues.append(
                issue(
                    "DQA-007",
                    "major",
                    "rule_regression",
                    "rule",
                    rule_id,
                    ["baseline rule passed and candidate rule failed"],
                    "A machine-readable domain rule regressed.",
                    "Repair the rule result before promotion.",
                    baseline=old,
                    candidate=new,
                )
            )
        elif old_status == "pass" and new_status == "unknown":
            issues.append(
                issue(
                    "DQA-010",
                    "major",
                    "indeterminate",
                    "rule",
                    rule_id,
                    ["candidate rule result is missing or unknown"],
                    "Diff QA cannot safely compare the required rule result.",
                    "Provide a deterministic pass or fail rule result.",
                    baseline=old,
                    candidate=new,
                )
            )
        elif old_status == "unknown" or new_status == "unknown":
            issues.append(
                issue(
                    "DQA-010",
                    "major",
                    "indeterminate",
                    "rule",
                    rule_id,
                    ["rule result is unknown on one side of the comparison"],
                    "Unknown rule results cannot be treated as a pass.",
                    "Provide stable rule IDs and deterministic results on both sides.",
                    baseline=old,
                    candidate=new,
                )
            )
    return dedupe_issues(issues), counts
