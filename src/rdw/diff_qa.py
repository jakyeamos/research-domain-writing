from __future__ import annotations

from pathlib import Path

from rdw.diff_qa_compare import compare_artifacts
from rdw.diff_qa_normalize import load_normalized_artifact, validate_baseline_manifest
from rdw.diff_qa_reporting import baseline_descriptor, candidate_descriptor, report
from rdw.diff_qa_support import (
    DIFF_QA_MODES,
    empty_counts,
    hash_file,
    string,
    try_load_mapping,
)
from rdw.diff_qa_validation import validate_diff_qa, validate_diff_qa_file
from rdw.yaml_io import YamlMapping, YamlValue, dump_yaml

__all__ = ["run_diff_qa", "validate_diff_qa", "validate_diff_qa_file", "write_diff_qa_report"]


def run_diff_qa(
    baseline_manifest_path: Path,
    candidate_path: Path,
    *,
    root: Path | None = None,
    candidate_ledger_path: Path | None = None,
    output_id: str | None = None,
) -> YamlMapping:
    """Compare a candidate with an explicitly approved local baseline.

    Only structured packet or draft-ledger representations are accepted. The
    comparison never extracts claims from Markdown or calls a provider.
    """

    baseline_manifest_path = baseline_manifest_path.resolve()
    candidate_path = candidate_path.resolve()
    comparison_root = (root or baseline_manifest_path.parent).resolve()
    candidate_hash = hash_file(candidate_path)
    manifest = try_load_mapping(baseline_manifest_path)
    mode = string(manifest.get("artifact_kind")) if manifest is not None else "packet"
    mode = mode if mode in DIFF_QA_MODES else "packet"
    manifest_output_id = string(manifest.get("output_id")) if manifest is not None else ""
    resolved_output_id = output_id or manifest_output_id or candidate_path.stem or "diff-qa"
    candidate_info = candidate_descriptor(candidate_path, candidate_hash, mode)

    if not candidate_path.is_relative_to(comparison_root):
        issue = _issue(
            "DQA-010",
            "major",
            "indeterminate",
            "candidate",
            candidate_path.name,
            ["candidate path escapes the comparison root"],
            "Diff QA will not compare a candidate outside the declared local root.",
            "Place the candidate under the comparison root and rerun diff QA.",
        )
        return report(
            resolved_output_id,
            mode,
            baseline=None,
            candidate=candidate_info,
            issues=[issue],
            counts=empty_counts(),
            indeterminate=True,
        )

    baseline_error = validate_baseline_manifest(
        manifest,
        baseline_manifest_path,
        comparison_root,
    )
    if baseline_error is not None:
        return report(
            resolved_output_id,
            mode,
            baseline=None,
            candidate=candidate_info,
            issues=[baseline_error],
            counts=empty_counts(),
            indeterminate=False,
        )

    assert manifest is not None
    from rdw.diff_qa_support import resolve_manifest_artifact

    baseline_path = resolve_manifest_artifact(comparison_root, manifest, "artifact_path")
    if baseline_path is None:
        issue = _issue(
            "DQA-001",
            "blocker",
            "baseline_invalid",
            "baseline",
            string(manifest.get("baseline_id")) or None,
            ["baseline artifact path is missing or unsafe"],
            "The approved baseline cannot be resolved.",
            "Repair the baseline manifest or create a new explicitly approved baseline.",
        )
        return report(
            resolved_output_id,
            mode,
            baseline=None,
            candidate=candidate_info,
            issues=[issue],
            counts=empty_counts(),
            indeterminate=False,
        )

    baseline_hash = hash_file(baseline_path)
    if baseline_hash is None:
        issue = _issue(
            "DQA-001",
            "blocker",
            "baseline_invalid",
            "baseline",
            string(manifest.get("baseline_id")) or None,
            ["approved baseline bytes could not be read"],
            "The approved baseline cannot be hashed for comparison.",
            "Restore the approved artifact and rerun diff QA.",
        )
        return report(
            resolved_output_id,
            mode,
            baseline=None,
            candidate=candidate_info,
            issues=[issue],
            counts=empty_counts(),
            indeterminate=False,
        )
    baseline_info = baseline_descriptor(manifest, baseline_path, baseline_hash, mode)
    if not _hash_matches(manifest, baseline_hash):
        issue = _issue(
            "DQA-001",
            "blocker",
            "baseline_invalid",
            "baseline",
            string(manifest.get("baseline_id")) or None,
            ["approved baseline content_sha256 does not match the current baseline bytes"],
            "The approved baseline changed after approval.",
            "Restore the approved bytes or create a new baseline manifest.",
            baseline={
                "expected_sha256": manifest.get("content_sha256"),
                "actual_sha256": baseline_hash,
            },
        )
        return report(
            resolved_output_id,
            mode,
            baseline=baseline_info,
            candidate=candidate_info,
            issues=[issue],
            counts=empty_counts(),
            indeterminate=False,
        )

    baseline_artifact, baseline_issues = load_normalized_artifact(
        baseline_path,
        mode=mode,
        root=comparison_root,
        ledger_path=_manifest_ledger_path(comparison_root, manifest),
        subject="baseline",
    )
    if baseline_issues:
        return report(
            resolved_output_id,
            mode,
            baseline=baseline_info,
            candidate=candidate_info,
            issues=baseline_issues,
            counts=empty_counts(),
            indeterminate=False,
        )

    candidate_artifact, candidate_issues = load_normalized_artifact(
        candidate_path,
        mode=mode,
        root=comparison_root,
        ledger_path=candidate_ledger_path
        or _conventional_ledger_path(comparison_root, candidate_path),
        subject="candidate",
    )
    if candidate_artifact is None or candidate_issues:
        candidate_indeterminate = any(
            string(value.get("code")) in {"DQA-009", "DQA-010"} for value in candidate_issues
        )
        return report(
            resolved_output_id,
            mode,
            baseline=baseline_info,
            candidate=candidate_info,
            issues=candidate_issues,
            counts=empty_counts(),
            indeterminate=candidate_indeterminate,
        )

    assert baseline_artifact is not None
    manifest_packet_id = string(manifest.get("packet_id"))
    if (
        mode == "packet"
        and manifest_packet_id
        and manifest_packet_id != baseline_artifact.artifact_id
    ):
        issue = _issue(
            "DQA-001",
            "blocker",
            "baseline_invalid",
            "baseline",
            manifest_packet_id,
            [
                f"manifest packet_id {manifest_packet_id} does not match "
                f"baseline packet id {baseline_artifact.artifact_id}"
            ],
            "The approved baseline identity does not match its artifact.",
            "Repair the manifest identity or approve the intended artifact.",
            baseline={"artifact_id": baseline_artifact.artifact_id},
        )
        return report(
            resolved_output_id,
            mode,
            baseline=baseline_info,
            candidate=candidate_info,
            issues=[issue],
            counts=empty_counts(),
            indeterminate=False,
        )
    manifest_revision_id = string(manifest.get("packet_revision_id"))
    if (
        mode == "packet"
        and manifest_revision_id
        and manifest_revision_id != baseline_artifact.revision_id
    ):
        issue = _issue(
            "DQA-001",
            "blocker",
            "baseline_invalid",
            "baseline",
            manifest_packet_id or baseline_artifact.artifact_id,
            [
                f"manifest packet_revision_id {manifest_revision_id} does not match "
                f"baseline revision {baseline_artifact.revision_id}"
            ],
            "The approved baseline revision does not match its artifact.",
            "Repair the manifest revision or approve the intended artifact.",
            baseline={"revision_id": baseline_artifact.revision_id},
        )
        return report(
            resolved_output_id,
            mode,
            baseline=baseline_info,
            candidate=candidate_info,
            issues=[issue],
            counts=empty_counts(),
            indeterminate=False,
        )

    issues, counts = compare_artifacts(baseline_artifact, candidate_artifact)
    if baseline_artifact.artifact_id != candidate_artifact.artifact_id:
        issues.append(
            _issue(
                "DQA-010",
                "major",
                "indeterminate",
                "artifact",
                candidate_artifact.artifact_id,
                [
                    f"candidate identity {candidate_artifact.artifact_id} does not match "
                    f"baseline identity {baseline_artifact.artifact_id}"
                ],
                "Diff QA will not compare unrelated packet or draft identities.",
                "Use the matching baseline or create an explicitly approved baseline for this identity.",
                baseline={"artifact_id": baseline_artifact.artifact_id},
                candidate={"artifact_id": candidate_artifact.artifact_id},
            )
        )
    return report(
        resolved_output_id,
        mode,
        baseline=baseline_info,
        candidate={
            **candidate_info,
            "packet_id": candidate_artifact.artifact_id,
            "packet_revision_id": candidate_artifact.revision_id if mode == "packet" else None,
        },
        issues=issues,
        counts=counts,
        indeterminate=any(string(value.get("code")) in {"DQA-009", "DQA-010"} for value in issues),
    )


def write_diff_qa_report(report_value: YamlMapping, path: Path) -> None:
    """Write a deterministic YAML report for a diff-QA comparison."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_yaml(report_value), encoding="utf-8")


def _hash_matches(manifest: YamlMapping, baseline_hash: str) -> bool:
    declared = string(manifest.get("content_sha256"))
    return declared == baseline_hash


def _manifest_ledger_path(root: Path, manifest: YamlMapping) -> Path | None:
    from rdw.diff_qa_support import manifest_ledger_path

    return manifest_ledger_path(root, manifest)


def _conventional_ledger_path(root: Path, draft_path: Path) -> Path:
    from rdw.diff_qa_support import conventional_ledger_path

    return conventional_ledger_path(root, draft_path)


def _issue(
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
    from rdw.diff_qa_reporting import issue

    return issue(
        code,
        severity,
        category,
        subject_type,
        subject_id,
        evidence,
        description,
        suggested_fix,
        baseline=baseline,
        candidate=candidate,
    )
