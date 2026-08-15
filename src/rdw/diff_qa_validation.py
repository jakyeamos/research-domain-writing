from __future__ import annotations

from pathlib import Path

from rdw.diff_qa_support import (
    DIFF_QA_CODES,
    DIFF_QA_MODES,
    DIFF_QA_SEVERITIES,
    DIFF_QA_STATUSES,
    empty_counts,
    is_sha256,
    string,
)
from rdw.validation import ValidationResult
from rdw.yaml_io import YamlMapping, load_yaml_mapping


def validate_diff_qa_file(path: Path) -> ValidationResult:
    if not path.exists():
        return ValidationResult(errors=[f"not found: {path}"], warnings=[])
    try:
        data = load_yaml_mapping(path)
    except ValueError as exc:
        return ValidationResult(errors=[f"invalid: {exc}"], warnings=[])
    return validate_diff_qa(data)


def validate_diff_qa(data: YamlMapping) -> ValidationResult:
    """Validate the structural and outcome contract of a diff-QA report."""

    errors: list[str] = []
    warnings: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("diff_qa schema_version must be 1")
    if data.get("kind") != "diff_qa":
        errors.append("diff_qa kind must be diff_qa")
    if not string(data.get("output_id")):
        errors.append("diff_qa output_id must be a non-empty string")

    comparison = data.get("comparison")
    if not isinstance(comparison, dict):
        errors.append("diff_qa comparison must be a mapping")
    else:
        mode = string(comparison.get("mode"))
        if mode not in DIFF_QA_MODES:
            errors.append("diff_qa comparison.mode must be packet or draft")
        for side in ("baseline", "candidate"):
            value = comparison.get(side)
            if not isinstance(value, dict):
                errors.append(f"diff_qa comparison.{side} must be a mapping")
                continue
            if not is_sha256(string(value.get("sha256"))):
                errors.append(f"diff_qa comparison.{side}.sha256 must be sha256:<64 hex>")
            if not string(value.get("path")):
                errors.append(f"diff_qa comparison.{side}.path must be a non-empty string")

    summary = data.get("summary")
    if not isinstance(summary, dict):
        errors.append("diff_qa summary must be a mapping")
        return ValidationResult(errors=errors, warnings=warnings)
    status = string(summary.get("status"))
    if status not in DIFF_QA_STATUSES:
        errors.append("diff_qa summary.status must be pass, fail, or indeterminate")
    passed = summary.get("pass")
    if not isinstance(passed, bool):
        errors.append("diff_qa summary.pass must be boolean")
    elif passed != (status == "pass"):
        errors.append("diff_qa summary.pass must be derived from summary.status")
    needs_review = summary.get("needs_human_review")
    if not isinstance(needs_review, bool):
        errors.append("diff_qa summary.needs_human_review must be boolean")
    if status == "indeterminate" and (passed is True or needs_review is not True):
        errors.append("indeterminate diff_qa must fail and require human review")

    counts = summary.get("counts")
    if not isinstance(counts, dict):
        errors.append("diff_qa summary.counts must be a mapping")
    else:
        for field in empty_counts():
            value = counts.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"diff_qa summary.counts.{field} must be a non-negative integer")

    issues = data.get("issues")
    if not isinstance(issues, list):
        errors.append("diff_qa issues must be a list")
        issues = []
    blocker_count = 0
    major_count = 0
    minor_count = 0
    issue_ids: set[str] = set()
    for index, issue in enumerate(issues, start=1):
        if not isinstance(issue, dict):
            errors.append(f"diff_qa issues[{index}] must be a mapping")
            continue
        code = string(issue.get("code"))
        severity = string(issue.get("severity"))
        issue_id = string(issue.get("id"))
        if code not in DIFF_QA_CODES:
            errors.append(f"diff_qa issues[{index}] has unknown code: {code}")
        if severity not in DIFF_QA_SEVERITIES:
            errors.append(f"diff_qa issues[{index}] severity must be blocker|major|minor")
        if not issue_id:
            errors.append(f"diff_qa issues[{index}] missing id")
        elif issue_id in issue_ids:
            errors.append(f"diff_qa issues[{index}] duplicate id: {issue_id}")
        else:
            issue_ids.add(issue_id)
        if not string(issue.get("category")):
            errors.append(f"diff_qa issues[{index}] missing category")
        if not string(issue.get("subject_type")):
            errors.append(f"diff_qa issues[{index}] missing subject_type")
        if not string(issue.get("description")):
            errors.append(f"diff_qa issues[{index}] missing description")
        if severity == "blocker":
            blocker_count += 1
        elif severity == "major":
            major_count += 1
        elif severity == "minor":
            minor_count += 1
    blocker_or_major = blocker_count + major_count
    if status == "fail" and blocker_or_major == 0:
        errors.append("failed diff_qa must contain a blocker or major issue")
    if status == "pass" and blocker_or_major:
        errors.append("passing diff_qa cannot contain blocker or major issues")
    if status == "pass" and any(
        isinstance(issue, dict) and string(issue.get("code")) in {"DQA-009", "DQA-010"}
        for issue in issues
    ):
        errors.append("passing diff_qa cannot contain indeterminate diagnostics")
    expected_issue_counts = {
        "blocking_issue_count": blocker_count,
        "major_issue_count": major_count,
        "minor_issue_count": minor_count,
    }
    for field, expected in expected_issue_counts.items():
        value = summary.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"diff_qa summary.{field} must be a non-negative integer")
        elif value != expected:
            errors.append(f"diff_qa summary.{field} must equal the report issue count ({expected})")
    return ValidationResult(errors=errors, warnings=warnings)
