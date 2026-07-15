from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from rdw.adapters.base import (
    ADAPTER_OUTCOMES,
    AdapterArtifact,
    AdapterFailure,
    AdapterOutcome,
    AdapterReceipt,
    AdapterRequest,
    AdapterResult,
    TaskAdapter,
)
from rdw.io import atomic_write_text
from rdw.lifecycle import load_task_status_view
from rdw.yaml_io import YamlMapping, YamlValue, load_yaml_mapping

FIXTURE_ARTIFACT_KINDS = (
    "research_packet",
    "knowledge_packet",
    "draft",
    "qa",
    "final",
)


class FixtureAdapter(TaskAdapter):
    name = "fixture"

    def run(self, run_dir: Path, *, dry_run: bool = False) -> AdapterResult:
        run_dir = run_dir.resolve()
        contract = self._load_contract(run_dir)
        status_view = load_task_status_view(run_dir)
        message = (
            "Fixture adapter is a deterministic runtime for the RDW vertical-slice prototype. "
            "Use `rdw task execute --fixture ...` to stage artifacts and advance lifecycle state."
        )
        artifact_path = run_dir / "adapter-fixture.json"
        payload = {
            "adapter": self.name,
            "task_id": str(contract.get("task_id") or status_view.task_id),
            "status": status_view.status,
            "message": message,
            "generated_at": _now_iso(),
        }
        if not dry_run:
            atomic_write_text(artifact_path, json.dumps(payload, indent=2) + "\n")
        return AdapterResult(
            adapter=self.name,
            run_dir=run_dir,
            status=status_view.status,
            message=message,
            artifact_path=None if dry_run else artifact_path,
        )

    def execute(self, request: AdapterRequest) -> AdapterReceipt:
        fixture_path = request.fixture_path
        if fixture_path is None:
            raise ValueError("fixture adapter requires a fixture path")
        fixture_path = fixture_path.resolve()
        if not fixture_path.is_file():
            raise ValueError(f"fixture not found: {fixture_path}")

        manifest = load_yaml_mapping(fixture_path)
        if manifest.get("fixture_version") != 1:
            raise ValueError("fixture_version must be 1")
        contract = self._load_contract(request.run_dir.resolve())
        task_id = _required_string(contract, "task_id")
        _check_expected(manifest, "task_id", task_id)
        _check_expected(manifest, "packet_id", str(contract.get("packet_id") or ""))
        output_id = _optional_string(manifest.get("output_id")) or task_id
        _validate_component(output_id, "output_id")

        outcome = _outcome(manifest.get("outcome"))
        requested_stages = _requested_stages(manifest.get("requested_stages"))
        missing_info = tuple(_string_list(manifest.get("missing_info")))
        source_root = (request.source_root or fixture_path.parent).resolve()
        attempt_dir = request.run_dir.resolve() / "adapter-runs" / self.name / request.attempt_id
        started_at = _now_iso()
        artifacts: list[AdapterArtifact] = []
        if not request.dry_run:
            for kind, source_reference in _artifact_references(manifest).items():
                source_path = _resolve_source(source_root, source_reference)
                destination = _canonical_artifact_path(
                    kind,
                    task_id=task_id,
                    packet_id=str(contract.get("packet_id") or "packet"),
                    output_id=output_id,
                )
                content = source_path.read_text(encoding="utf-8")
                destination_path = attempt_dir / destination
                atomic_write_text(destination_path, content)
                artifacts.append(
                    AdapterArtifact(
                        kind=kind,
                        path=destination,
                        sha256=_sha256(content),
                        media_type=_media_type(destination_path),
                    )
                )

        failure = _failure(manifest.get("failure"))
        finished_at = _now_iso()
        receipt = AdapterReceipt(
            schema_version=1,
            adapter=self.name,
            task_id=task_id,
            attempt_id=request.attempt_id,
            idempotency_key=request.idempotency_key,
            status=outcome,
            requested_stages=requested_stages,
            artifacts=tuple(artifacts),
            needs_review=bool(manifest.get("needs_review", outcome != "succeeded")),
            missing_info=missing_info,
            failure=failure,
            external_run_id=f"fixture:{_optional_string(manifest.get('name')) or fixture_path.stem}",
            started_at=started_at,
            finished_at=finished_at,
            attempt_dir=attempt_dir,
            receipt_path=None if request.dry_run else attempt_dir / "receipt.json",
        )
        if not request.dry_run:
            atomic_write_text(
                receipt.attempt_dir / "receipt.json",
                json.dumps(receipt.as_dict(), indent=2) + "\n",
            )
        return receipt


def _artifact_references(manifest: YamlMapping) -> dict[str, str]:
    raw = manifest.get("artifacts")
    if not isinstance(raw, dict):
        raise ValueError("fixture artifacts must be a mapping")
    references: dict[str, str] = {}
    for kind, source in raw.items():
        if kind not in FIXTURE_ARTIFACT_KINDS:
            raise ValueError(f"fixture has unknown artifact kind: {kind}")
        if not isinstance(source, str) or not source.strip():
            raise ValueError(f"fixture artifact path must be a non-empty string: {kind}")
        references[kind] = source
    return references


def _canonical_artifact_path(kind: str, *, task_id: str, packet_id: str, output_id: str) -> str:
    _validate_component(task_id, "task_id")
    _validate_component(packet_id, "packet_id")
    _validate_component(output_id, "output_id")
    paths = {
        "research_packet": f"outputs/research/{packet_id}.yaml",
        "knowledge_packet": f"outputs/research/{task_id}-knowledge.md",
        "draft": f"outputs/drafts/{output_id}.md",
        "qa": f"outputs/qa/{output_id}-qa.yaml",
        "final": f"outputs/final/{output_id}.md",
    }
    try:
        return paths[kind]
    except KeyError as exc:
        raise ValueError(f"fixture has unknown artifact kind: {kind}") from exc


def _resolve_source(root: Path, reference: str) -> Path:
    relative = Path(reference)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"fixture source path must stay under source root: {reference}")
    source = (root / relative).resolve()
    if not source.is_relative_to(root):
        raise ValueError(f"fixture source path escapes source root: {reference}")
    if not source.is_file():
        raise ValueError(f"fixture artifact source not found: {source}")
    return source


def _outcome(value: YamlValue | None) -> AdapterOutcome:
    outcome = value if isinstance(value, str) and value else "succeeded"
    if outcome not in ADAPTER_OUTCOMES:
        expected = ", ".join(ADAPTER_OUTCOMES)
        raise ValueError(f"fixture outcome must be one of: {expected}")
    return cast(AdapterOutcome, outcome)


def _requested_stages(value: YamlValue | None) -> tuple[str, ...]:
    if value is None:
        return ("research", "draft", "qa", "final")
    stages = _string_list(value)
    if not stages:
        raise ValueError("fixture requested_stages must be a non-empty list")
    return tuple(stages)


def _failure(value: YamlValue | None) -> AdapterFailure | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("fixture failure must be a mapping")
    category = _required_string(value, "category")
    code = _required_string(value, "code")
    message = _required_string(value, "message")
    retryable = value.get("retryable")
    if not isinstance(retryable, bool):
        raise ValueError("fixture failure retryable must be boolean")
    return AdapterFailure(category=category, code=code, message=message, retryable=retryable)


def _check_expected(manifest: YamlMapping, field: str, actual: str) -> None:
    expected = _optional_string(manifest.get(field))
    if expected and expected != actual:
        raise ValueError(f"fixture {field} does not match task contract: {expected} != {actual}")


def _required_string(mapping: dict[str, YamlValue], field: str) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing or empty fixture field: {field}")
    return value


def _string_list(value: YamlValue | None) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return []
    return [str(item) for item in value]


def _optional_string(value: YamlValue | None) -> str | None:
    return value if isinstance(value, str) and value else None


def _validate_component(value: str, field: str) -> None:
    if not value or value in {".", ".."} or "/" in value or "\\" in value:
        raise ValueError(f"fixture {field} must be a safe path component")


def _sha256(content: str) -> str:
    return f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"


def _media_type(path: Path) -> str:
    return {
        ".md": "text/markdown",
        ".yaml": "application/yaml",
        ".yml": "application/yaml",
        ".json": "application/json",
    }.get(path.suffix.lower(), "text/plain")


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
