from __future__ import annotations

from pathlib import Path

from rdw.diff_qa_support import string, yaml_strings
from rdw.yaml_io import YamlMapping, YamlValue


def issue(
    code: str,
    severity: str,
    category: str,
    subject_type: str,
    subject_id: str | None,
    evidence: list[str],
    description: str,
    suggested_fix: str,
    *,
    baseline: YamlValue | None = None,
    candidate: YamlValue | None = None,
) -> dict[str, YamlValue]:
    return {
        "id": "pending",
        "code": code,
        "severity": severity,
        "category": category,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "baseline": baseline,
        "candidate": candidate,
        "evidence": yaml_strings(evidence),
        "description": description,
        "suggested_fix": suggested_fix,
    }


def dedupe_issues(issues: list[dict[str, YamlValue]]) -> list[dict[str, YamlValue]]:
    unique: dict[tuple[str, str, str], dict[str, YamlValue]] = {}
    for value in issues:
        key = (
            string(value.get("code")),
            string(value.get("subject_type")),
            string(value.get("subject_id")),
        )
        unique.setdefault(key, value)
    return [unique[key] for key in sorted(unique)]


def report(
    output_id: str,
    mode: str,
    *,
    baseline: YamlMapping | None,
    candidate: YamlMapping,
    issues: list[dict[str, YamlValue]],
    counts: dict[str, int],
    indeterminate: bool,
) -> YamlMapping:
    ordered_issues = dedupe_issues(issues)
    for index, value in enumerate(ordered_issues, start=1):
        value["id"] = f"dqa-{index:04d}"
    blocker_count = sum(value.get("severity") == "blocker" for value in ordered_issues)
    major_count = sum(value.get("severity") == "major" for value in ordered_issues)
    minor_count = sum(value.get("severity") == "minor" for value in ordered_issues)
    status = (
        "indeterminate" if indeterminate else ("fail" if blocker_count or major_count else "pass")
    )
    comparison: YamlMapping = {"mode": mode, "baseline": baseline, "candidate": candidate}
    summary: YamlMapping = {
        "status": status,
        "pass": status == "pass",
        "needs_human_review": status != "pass" or minor_count > 0,
        "blocking_issue_count": blocker_count,
        "major_issue_count": major_count,
        "minor_issue_count": minor_count,
        "counts": {key: value for key, value in counts.items()},
    }
    return {
        "schema_version": 1,
        "kind": "diff_qa",
        "output_id": output_id,
        "comparison": comparison,
        "summary": summary,
        "issues": [value for value in ordered_issues],
    }


def candidate_descriptor(path: Path, content_hash: str | None, mode: str) -> YamlMapping:
    return {"artifact_kind": mode, "path": path.as_posix(), "sha256": content_hash}


def baseline_descriptor(
    manifest: YamlMapping,
    path: Path,
    content_hash: str,
    mode: str,
) -> YamlMapping:
    descriptor: YamlMapping = {
        "artifact_kind": mode,
        "path": path.as_posix(),
        "sha256": content_hash,
        "baseline_id": string(manifest.get("baseline_id")),
    }
    for field in ("packet_id", "packet_revision_id"):
        value = string(manifest.get(field))
        if value:
            descriptor[field] = value
    return descriptor
