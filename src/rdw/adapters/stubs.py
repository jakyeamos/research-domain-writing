from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from rdw.adapters.base import AdapterResult, TaskAdapter
from rdw.lifecycle import load_task_status_view


class LocalAdapter(TaskAdapter):
    name = "local"

    def run(self, run_dir: Path, *, dry_run: bool = False) -> AdapterResult:
        run_dir = run_dir.resolve()
        contract = self._load_contract(run_dir)
        task_id = str(contract.get("task_id") or run_dir.name)
        status_view = load_task_status_view(run_dir)
        message = (
            "Local adapter records the current task contract for a human or agent runtime. "
            "It does not call external model APIs."
        )
        artifact_path = run_dir / "adapter-local.json"
        payload = {
            "adapter": self.name,
            "task_id": task_id,
            "status": status_view.status,
            "contract_path": str(run_dir / "task-contract.yaml"),
            "prompt_bundle_path": str(run_dir / "prompt-bundle.md"),
            "message": message,
            "generated_at": _now_iso(),
        }
        if not dry_run:
            artifact_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return AdapterResult(
            adapter=self.name,
            run_dir=run_dir,
            status=status_view.status,
            message=message,
            artifact_path=None if dry_run else artifact_path,
        )


class OpenAIAdapter(TaskAdapter):
    name = "openai"

    def run(self, run_dir: Path, *, dry_run: bool = False) -> AdapterResult:
        return _stub_provider_adapter(self.name, run_dir, dry_run=dry_run)


class AnthropicAdapter(TaskAdapter):
    name = "anthropic"

    def run(self, run_dir: Path, *, dry_run: bool = False) -> AdapterResult:
        return _stub_provider_adapter(self.name, run_dir, dry_run=dry_run)


def _stub_provider_adapter(name: str, run_dir: Path, *, dry_run: bool) -> AdapterResult:
    run_dir = run_dir.resolve()
    contract_path = run_dir / "task-contract.yaml"
    if not contract_path.exists():
        raise ValueError(f"missing task contract: {contract_path}")
    status_view = load_task_status_view(run_dir)
    message = (
        f"{name} adapter is a provider-neutral stub in RDW v0.2. "
        "Install the optional extra and implement API calls in your runtime; "
        "RDW still does not call model APIs by default."
    )
    artifact_path = run_dir / f"adapter-{name}.json"
    payload = {
        "adapter": name,
        "task_id": status_view.task_id,
        "status": status_view.status,
        "dry_run": dry_run,
        "message": message,
        "generated_at": _now_iso(),
    }
    if not dry_run:
        artifact_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return AdapterResult(
        adapter=name,
        run_dir=run_dir,
        status=status_view.status,
        message=message,
        artifact_path=None if dry_run else artifact_path,
    )


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
