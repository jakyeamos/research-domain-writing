from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from rdw.yaml_io import YamlMapping, load_yaml_mapping


@dataclass(frozen=True)
class AdapterResult:
    adapter: str
    run_dir: Path
    status: str
    message: str
    artifact_path: Path | None = None


class TaskAdapter(ABC):
    name: str

    @abstractmethod
    def run(self, run_dir: Path, *, dry_run: bool = False) -> AdapterResult:
        """Consume a planned task run and write adapter status artifacts."""

    def _load_contract(self, run_dir: Path) -> YamlMapping:
        contract_path = run_dir / "task-contract.yaml"
        if not contract_path.exists():
            raise ValueError(f"missing task contract: {contract_path}")
        return load_yaml_mapping(contract_path)
