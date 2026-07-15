from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from rdw.adapters import get_adapter
from rdw.adapters.base import AdapterArtifact, AdapterOutcome, AdapterReceipt, AdapterRequest
from rdw.io import atomic_write_text
from rdw.lifecycle import load_task_status_view, mark_task_status
from rdw.validation import validate_packet_file
from rdw.yaml_io import YamlMapping, load_yaml_mapping

FIXTURE_STAGES = ("research", "draft", "qa", "final")
REQUIRED_SUCCESS_ARTIFACTS = frozenset(
    {"research_packet", "knowledge_packet", "draft", "qa", "final"}
)
REQUIRED_INCOMPLETE_ARTIFACTS = frozenset({"research_packet", "knowledge_packet", "draft", "qa"})
ALLOWED_ARTIFACT_KINDS = REQUIRED_SUCCESS_ARTIFACTS


@dataclass(frozen=True)
class ExecutionResult:
    task_id: str
    adapter_status: AdapterOutcome
    workflow_status: str
    attempt_id: str
    idempotency_key: str
    receipt_path: Path | None
    promoted_paths: tuple[Path, ...]
    needs_review: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "adapter_status": self.adapter_status,
            "workflow_status": self.workflow_status,
            "attempt_id": self.attempt_id,
            "idempotency_key": self.idempotency_key,
            "receipt_path": str(self.receipt_path) if self.receipt_path else None,
            "promoted_paths": [str(path) for path in self.promoted_paths],
            "needs_review": self.needs_review,
        }


def execute_fixture(
    run_dir: Path,
    fixture_path: Path,
    *,
    root: Path | None = None,
    resume: bool = False,
    dry_run: bool = False,
) -> ExecutionResult:
    run_dir = run_dir.resolve()
    fixture_path = fixture_path.resolve()
    source_root = (root or fixture_path.parent).resolve()
    contract = _load_task_contract(run_dir)
    current_status = load_task_status_view(run_dir).status
    _check_execution_status(current_status, resume=resume)

    attempt_id = _new_attempt_id()
    idempotency_key = _idempotency_key(contract)
    request = AdapterRequest(
        run_dir=run_dir,
        adapter="fixture",
        attempt_id=attempt_id,
        idempotency_key=idempotency_key,
        requested_stages=FIXTURE_STAGES,
        dry_run=dry_run,
        fixture_path=fixture_path,
        source_root=source_root,
    )
    receipt = get_adapter("fixture").execute(request)
    if dry_run:
        return ExecutionResult(
            task_id=str(contract["task_id"]),
            adapter_status=receipt.status,
            workflow_status=current_status,
            attempt_id=attempt_id,
            idempotency_key=idempotency_key,
            receipt_path=None,
            promoted_paths=(),
            needs_review=receipt.needs_review,
        )

    artifacts = _validate_receipt(receipt, contract, request=request, root=source_root)
    if receipt.status in {"rejected", "failed", "cancelled"}:
        return ExecutionResult(
            task_id=str(contract["task_id"]),
            adapter_status=receipt.status,
            workflow_status=current_status,
            attempt_id=attempt_id,
            idempotency_key=idempotency_key,
            receipt_path=receipt.receipt_path,
            promoted_paths=(),
            needs_review=receipt.needs_review,
        )

    promoted_paths = tuple(_promote_artifacts(run_dir, receipt, artifacts))
    if receipt.status == "succeeded":
        _advance_success(run_dir)
    else:
        _advance_incomplete(run_dir, artifacts, receipt.missing_info)
    workflow_status = load_task_status_view(run_dir).status
    return ExecutionResult(
        task_id=str(contract["task_id"]),
        adapter_status=receipt.status,
        workflow_status=workflow_status,
        attempt_id=attempt_id,
        idempotency_key=idempotency_key,
        receipt_path=receipt.receipt_path,
        promoted_paths=promoted_paths,
        needs_review=receipt.needs_review,
    )


def _load_task_contract(run_dir: Path) -> YamlMapping:
    contract_path = run_dir / "task-contract.yaml"
    if not contract_path.exists():
        raise ValueError(f"not a planned task run: {run_dir} (missing task-contract.yaml)")
    return load_yaml_mapping(contract_path)


def _check_execution_status(status: str, *, resume: bool) -> None:
    if status == "final-done":
        raise ValueError("task is already final-done; create a new planned run")
    if status == "qa-failed" and not resume:
        raise ValueError("qa-failed task requires --resume for fixture execution")
    if status not in {"planned", "qa-failed"}:
        raise ValueError(
            "fixture execution requires planned or qa-failed status "
            f"(found: {status}; use the lifecycle commands for other states)"
        )


def _validate_receipt(
    receipt: AdapterReceipt,
    contract: YamlMapping,
    *,
    request: AdapterRequest,
    root: Path,
) -> tuple[AdapterArtifact, ...]:
    receipt_path = receipt.receipt_path
    if receipt_path is None or not receipt_path.is_file():
        raise ValueError("adapter did not produce a durable receipt")
    try:
        persisted = json.loads(receipt_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid adapter receipt JSON: {receipt_path}") from exc
    if persisted != receipt.as_dict():
        raise ValueError(f"adapter receipt changed before core validation: {receipt_path}")
    if receipt.schema_version != 1:
        raise ValueError(f"unsupported adapter receipt schema: {receipt.schema_version}")
    if receipt.adapter != "fixture":
        raise ValueError(f"unexpected adapter receipt: {receipt.adapter}")
    expected_attempt_dir = (
        request.run_dir / "adapter-runs" / request.adapter / request.attempt_id
    ).resolve()
    if receipt.attempt_id != request.attempt_id:
        raise ValueError("adapter receipt attempt_id does not match request")
    if receipt.attempt_dir.resolve() != expected_attempt_dir:
        raise ValueError("adapter receipt attempt directory violates the run boundary")
    if receipt.idempotency_key != request.idempotency_key:
        raise ValueError("adapter receipt idempotency_key does not match request")
    if receipt.requested_stages != request.requested_stages:
        raise ValueError("adapter receipt requested_stages do not match request")
    if receipt.task_id != str(contract.get("task_id") or ""):
        raise ValueError("adapter receipt task_id does not match task contract")
    artifacts_by_kind: dict[str, AdapterArtifact] = {}
    for artifact in receipt.artifacts:
        if artifact.kind not in ALLOWED_ARTIFACT_KINDS:
            raise ValueError(f"unknown adapter artifact kind: {artifact.kind}")
        if artifact.kind in artifacts_by_kind:
            raise ValueError(f"duplicate adapter artifact kind: {artifact.kind}")
        source_path = _safe_attempt_path(receipt.attempt_dir, artifact.path)
        content = source_path.read_bytes()
        expected_hash = f"sha256:{hashlib.sha256(content).hexdigest()}"
        if artifact.sha256 != expected_hash:
            raise ValueError(f"adapter artifact hash mismatch: {artifact.path}")
        artifacts_by_kind[artifact.kind] = artifact

    if receipt.status == "succeeded":
        missing = REQUIRED_SUCCESS_ARTIFACTS - artifacts_by_kind.keys()
        if missing:
            raise ValueError(
                f"successful fixture is missing artifacts: {', '.join(sorted(missing))}"
            )
        if receipt.needs_review:
            raise ValueError("successful fixture cannot require review")
        if receipt.failure is not None:
            raise ValueError("successful fixture cannot declare a failure")
    elif receipt.status == "incomplete":
        missing = REQUIRED_INCOMPLETE_ARTIFACTS - artifacts_by_kind.keys()
        if missing:
            raise ValueError(
                f"incomplete fixture is missing artifacts: {', '.join(sorted(missing))}"
            )
        if "final" in artifacts_by_kind:
            raise ValueError("incomplete fixture cannot promote a final artifact")
        if not receipt.needs_review:
            raise ValueError("incomplete fixture must require review")
        if receipt.failure is not None:
            raise ValueError("incomplete fixture cannot declare a failure")
    else:
        if artifacts_by_kind:
            raise ValueError(f"{receipt.status} fixture cannot declare promotable artifacts")
        if receipt.failure is None:
            raise ValueError(f"{receipt.status} fixture must declare a failure")

    artifacts = tuple(artifacts_by_kind.values())
    _validate_text_artifacts(receipt, artifacts)
    if receipt.status in {"succeeded", "incomplete"}:
        _validate_packet(receipt, artifacts_by_kind["research_packet"], root=root)
        qa_pass = _validate_qa(receipt, artifacts_by_kind["qa"])
        if receipt.status == "succeeded" and not qa_pass:
            raise ValueError("successful fixture QA artifact does not pass")
        if receipt.status == "incomplete" and qa_pass:
            raise ValueError("incomplete fixture QA artifact must fail or remain uncertain")
    return artifacts


def _validate_text_artifacts(
    receipt: AdapterReceipt, artifacts: tuple[AdapterArtifact, ...]
) -> None:
    for artifact in artifacts:
        content = _safe_attempt_path(receipt.attempt_dir, artifact.path).read_text(encoding="utf-8")
        if not content.strip():
            raise ValueError(f"adapter artifact is empty: {artifact.path}")


def _validate_packet(receipt: AdapterReceipt, artifact: AdapterArtifact, *, root: Path) -> None:
    packet_path = _safe_attempt_path(receipt.attempt_dir, artifact.path)
    result = validate_packet_file(packet_path, strict=True, root=root)
    if not result.ok:
        raise ValueError("fixture research packet failed validation: " + "; ".join(result.errors))


def _validate_qa(receipt: AdapterReceipt, artifact: AdapterArtifact) -> bool:
    qa_path = _safe_attempt_path(receipt.attempt_dir, artifact.path)
    qa = load_yaml_mapping(qa_path)
    value = qa.get("pass")
    if not isinstance(value, bool):
        raise ValueError("fixture QA artifact must expose boolean pass")
    return value


def _promote_artifacts(
    run_dir: Path,
    receipt: AdapterReceipt,
    artifacts: tuple[AdapterArtifact, ...],
) -> list[Path]:
    promoted: list[Path] = []
    for artifact in artifacts:
        source_path = _safe_attempt_path(receipt.attempt_dir, artifact.path)
        relative_destination = _safe_run_path(artifact.path)
        destination = run_dir / relative_destination
        atomic_write_text(destination, source_path.read_text(encoding="utf-8"))
        promoted.append(destination)
    return promoted


def _advance_success(run_dir: Path) -> None:
    for status in ("research-done", "draft-done", "qa-passed", "final-done"):
        _mark_if_needed(run_dir, status)


def _advance_incomplete(
    run_dir: Path,
    artifacts: tuple[AdapterArtifact, ...],
    missing_info: tuple[str, ...],
) -> None:
    _mark_if_needed(run_dir, "research-done")
    _mark_if_needed(run_dir, "draft-done")
    reason = _qa_failure_reason(run_dir, artifacts, missing_info)
    _mark_if_needed(run_dir, "qa-failed", reason=reason)


def _mark_if_needed(run_dir: Path, status: str, *, reason: str | None = None) -> None:
    current = load_task_status_view(run_dir).status
    if current != status:
        mark_task_status(run_dir, status, reason=reason)


def _qa_failure_reason(
    run_dir: Path,
    artifacts: tuple[AdapterArtifact, ...],
    missing_info: tuple[str, ...],
) -> str:
    qa_artifact = next((artifact for artifact in artifacts if artifact.kind == "qa"), None)
    if qa_artifact is not None:
        qa = load_yaml_mapping(_safe_run_path_for_read(run_dir, qa_artifact.path))
        issues = qa.get("issues")
        if isinstance(issues, list):
            for issue in issues:
                if isinstance(issue, dict):
                    description = issue.get("description")
                    if isinstance(description, str) and description:
                        return description
    return missing_info[0] if missing_info else "fixture QA requires review"


def _safe_attempt_path(attempt_dir: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError(f"unsafe adapter artifact path: {relative}")
    resolved_attempt = attempt_dir.resolve()
    resolved = (resolved_attempt / path).resolve()
    if not resolved.is_relative_to(resolved_attempt):
        raise ValueError(f"adapter artifact escapes attempt directory: {relative}")
    if not resolved.is_file():
        raise ValueError(f"adapter artifact not found: {relative}")
    return resolved


def _safe_run_path(relative: str) -> Path:
    path = Path(relative)
    if (
        path.is_absolute()
        or not path.parts
        or ".." in path.parts
        or path.parts[0] == "adapter-runs"
    ):
        raise ValueError(f"unsafe promoted artifact path: {relative}")
    return path


def _safe_run_path_for_read(run_dir: Path, relative: str) -> Path:
    path = run_dir / _safe_run_path(relative)
    if not path.is_file():
        raise ValueError(f"promoted artifact not found: {path}")
    return path


def _idempotency_key(contract: YamlMapping) -> str:
    encoded = json.dumps(
        {
            "adapter": "fixture",
            "requested_stages": FIXTURE_STAGES,
            "task_contract": contract,
        },
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _new_attempt_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"attempt-{timestamp}-{uuid.uuid4().hex[:8]}"
