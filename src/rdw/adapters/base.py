from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rdw.yaml_io import YamlMapping, load_yaml_mapping

AdapterOutcome = Literal["succeeded", "incomplete", "rejected", "failed", "cancelled"]

ADAPTER_OUTCOMES: tuple[AdapterOutcome, ...] = (
    "succeeded",
    "incomplete",
    "rejected",
    "failed",
    "cancelled",
)


@dataclass(frozen=True)
class AdapterResult:
    adapter: str
    run_dir: Path
    status: str
    message: str
    artifact_path: Path | None = None


@dataclass(frozen=True)
class AdapterArtifact:
    kind: str
    path: str
    sha256: str
    media_type: str

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "path": self.path,
            "sha256": self.sha256,
            "media_type": self.media_type,
        }


@dataclass(frozen=True)
class AdapterFailure:
    category: str
    code: str
    message: str
    retryable: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "category": self.category,
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
        }


@dataclass(frozen=True)
class AdapterRequest:
    run_dir: Path
    adapter: str
    attempt_id: str
    idempotency_key: str
    requested_stages: tuple[str, ...]
    dry_run: bool = False
    fixture_path: Path | None = None
    source_root: Path | None = None


@dataclass(frozen=True)
class AdapterReceipt:
    schema_version: int
    adapter: str
    task_id: str
    attempt_id: str
    idempotency_key: str
    status: AdapterOutcome
    requested_stages: tuple[str, ...]
    artifacts: tuple[AdapterArtifact, ...]
    needs_review: bool
    missing_info: tuple[str, ...]
    failure: AdapterFailure | None
    external_run_id: str | None
    started_at: str
    finished_at: str
    attempt_dir: Path
    receipt_path: Path | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "adapter": self.adapter,
            "task_id": self.task_id,
            "attempt_id": self.attempt_id,
            "idempotency_key": self.idempotency_key,
            "status": self.status,
            "requested_stages": list(self.requested_stages),
            "artifacts": [artifact.as_dict() for artifact in self.artifacts],
            "needs_review": self.needs_review,
            "missing_info": list(self.missing_info),
            "failure": self.failure.as_dict() if self.failure else None,
            "external_run_id": self.external_run_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


class TaskAdapter(ABC):
    name: str

    @abstractmethod
    def run(self, run_dir: Path, *, dry_run: bool = False) -> AdapterResult:
        """Consume a planned task run and write adapter status artifacts."""

    def execute(self, request: AdapterRequest) -> AdapterReceipt:
        raise ValueError(f"adapter does not support executable requests: {request.adapter}")

    def _load_contract(self, run_dir: Path) -> YamlMapping:
        contract_path = run_dir / "task-contract.yaml"
        if not contract_path.exists():
            raise ValueError(f"missing task contract: {contract_path}")
        return load_yaml_mapping(contract_path)
