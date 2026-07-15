from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from rdw.config import default_output_format, output_formats
from rdw.io import atomic_write_text
from rdw.lifecycle import needs_review_for
from rdw.resources import read_asset_text
from rdw.router import route_request
from rdw.validation import normalize_depth, validate_batch_file
from rdw.yaml_io import YamlMapping, YamlValue, dump_yaml, load_yaml_mapping


@dataclass(frozen=True)
class TaskRequest:
    request: str
    domain: str | None = None
    entity: str | None = None
    output_type: str | None = None
    audience: str | None = None
    depth: str | None = None
    packet_id: str | None = None
    task_id: str | None = None
    output_format: str | None = None


@dataclass(frozen=True)
class PlannedTask:
    task_id: str
    contract: YamlMapping
    prompt_bundle: str
    output_dir: Path


def plan_task(
    task: TaskRequest,
    output_dir: Path,
    *,
    root: Path | None = None,
    no_overwrite: bool = False,
    run_id: str | None = None,
) -> PlannedTask:
    if run_id is not None:
        output_dir = output_dir / _resolve_run_id(run_id)
    contract = infer_contract(task, root=root)
    task_id = str(contract["task_id"])
    prompt_bundle = render_prompt_bundle(contract)
    contract_path = output_dir / "task-contract.yaml"
    if no_overwrite and contract_path.exists():
        raise ValueError(f"refusing to overwrite existing plan: {contract_path} (use --force)")
    output_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(contract_path, dump_yaml(contract))
    atomic_write_text(output_dir / "prompt-bundle.md", prompt_bundle)
    status = {
        "task_id": task_id,
        "status": "planned",
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "next_step": "Give prompt-bundle.md to an agent and run the RDW pipeline.",
    }
    atomic_write_text(output_dir / "status.json", json.dumps(status, indent=2) + "\n")
    return PlannedTask(
        task_id=task_id,
        contract=contract,
        prompt_bundle=prompt_bundle,
        output_dir=output_dir,
    )


def plan_batch(batch_path: Path, output_dir: Path, *, root: Path | None = None) -> YamlMapping:
    result = validate_batch_file(batch_path, root=root)
    if not result.ok:
        raise ValueError("\n".join(result.errors))
    data = load_yaml_mapping(batch_path)
    batch_id = str(data["batch_id"])
    defaults = data.get("defaults")
    default_mapping = defaults if isinstance(defaults, dict) else {}
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("tasks must be a list")
    output_dir.mkdir(parents=True, exist_ok=True)
    task_rows: list[YamlValue] = []
    log_lines: list[str] = []
    for item in tasks:
        if not isinstance(item, dict):
            continue
        task_id = str(item["task_id"])
        depth_value = item.get("research_depth", default_mapping.get("research_depth", "standard"))
        output_format = str(
            item.get("output_format", default_mapping.get("output_format", "markdown"))
        )
        planned = plan_task(
            TaskRequest(
                request=str(item["request"]),
                domain=_optional_string(item.get("domain")),
                entity=_optional_string(item.get("entity_name")),
                output_type=_optional_string(item.get("output_type")),
                audience=_optional_string(item.get("audience")),
                depth=normalize_depth(str(depth_value)) or str(depth_value),
                packet_id=_optional_string(item.get("packet_id")),
                task_id=task_id,
                output_format=output_format,
            ),
            output_dir / "tasks" / task_id,
            root=root,
        )
        task_rows.append(
            {
                "task_id": planned.task_id,
                "status": "planned",
                "domain": str(planned.contract["domain"]),
                "output_format": output_format,
                "prompt_bundle": f"tasks/{task_id}/prompt-bundle.md",
            }
        )
        log_lines.append(
            json.dumps(
                {
                    "task_id": planned.task_id,
                    "domain": planned.contract["domain"],
                    "status": "planned",
                    "confidence_level": "unknown",
                    "needs_review": needs_review_for("planned"),
                    "missing_info": [],
                },
                sort_keys=True,
            )
        )
    summary: YamlMapping = {
        "batch_id": batch_id,
        "status": "planned",
        "task_count": len(task_rows),
        "completed": 0,
        "needs_review": 0,
        "failed": 0,
        "tasks": task_rows,
    }
    atomic_write_text(output_dir / "summary.yaml", dump_yaml(summary))
    atomic_write_text(output_dir / "batch-log.jsonl", "\n".join(log_lines) + "\n")
    return summary


def infer_contract(task: TaskRequest, *, root: Path | None = None) -> YamlMapping:
    request = task.request.strip()
    routed = route_request(request, root=root)
    domain = task.domain or routed.domain
    output_type = task.output_type or routed.output_type
    entity_type = routed.entity_type
    entity_name = task.entity or routed.entity_name
    depth = normalize_depth(task.depth or "") or routed.depth
    audience = task.audience or routed.audience
    task_id = task.task_id or _slugify(f"{domain}-{entity_name}-{output_type}")
    packet_id = task.packet_id or _default_packet_id(domain, entity_type, entity_name)
    output_format = task.output_format or default_output_format(root)
    warnings: list[YamlValue] = list(routed.warnings)
    if output_format not in output_formats(root):
        warnings.append(f"unknown output_format: {output_format}")
    return {
        "task_id": task_id,
        "task": request,
        "domain": domain,
        "pack_exists": _pack_exists(domain, root),
        "entity_type": entity_type,
        "entity_name": entity_name,
        "topic": _topic(request, output_type),
        "output_type": output_type,
        "output_format": output_format,
        "audience": audience,
        "research_needed": True,
        "research_depth": depth,
        "packet_id": packet_id,
        "inference": {
            "mode": "mixed" if _has_overrides(task) else "inferred",
            "confidence": routed.confidence,
            "fields_inferred": _fields_inferred(task),
            "fields_explicit": _fields_explicit(task),
            "rationale": "Contract generated by rdw's deterministic router; agent may refine before writing.",
        },
        "local_knowledge_paths": [f"knowledge/{domain}/{packet_id}.yaml"],
        "qa_checklist_path": f"domains/{domain}/qa-checklist.md",
        "writing_template": f"domains/{domain}/writing-templates.md",
        "style_profile_path": "config/style-profile.yaml",
        "warnings": warnings,
    }


def render_prompt_bundle(contract: YamlMapping) -> str:
    contract_yaml = dump_yaml(contract).rstrip()
    orchestrator = read_asset_text("prompts", "pipeline-orchestrator.md")
    router = read_asset_text("prompts", "domain-router.md")
    return (
        "# RDW Agent Prompt Bundle\n\n"
        "This bundle does not call an LLM by itself. Give it to an agent with repo/file/web tools.\n\n"
        "## Task Contract\n\n"
        "```yaml\n"
        f"{contract_yaml}\n"
        "```\n\n"
        "## Execution Order\n\n"
        "1. Read `SKILL.md` and the prompts listed below.\n"
        "2. Confirm or adjust the task contract if the user objects.\n"
        "3. Run research, knowledge packet, draft, QA, and humanizer in order.\n"
        "4. Save artifacts in the `output_format` from the contract above, "
        "using the output paths in `config/output-formats.yaml`.\n\n"
        "## Router Prompt\n\n"
        f"{router}\n\n"
        "## Pipeline Orchestrator\n\n"
        f"{orchestrator}\n"
    )


def _default_packet_id(domain: str, entity_type: str, entity_name: str) -> str:
    return _slugify(f"{domain}-{entity_type}-{entity_name}")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "rdw-task"


def _resolve_run_id(run_id: str) -> str:
    if run_id == "auto":
        return datetime.now(UTC).strftime("run-%Y%m%dT%H%M%SZ")
    return _slugify(run_id)


def _topic(request: str, output_type: str) -> str:
    return f"{output_type}: {request[:120]}"


def _has_overrides(task: TaskRequest) -> bool:
    return any(
        [
            task.domain,
            task.entity,
            task.output_type,
            task.audience,
            task.depth,
            task.packet_id,
            task.task_id,
            task.output_format,
        ]
    )


def _fields_explicit(task: TaskRequest) -> list[YamlValue]:
    fields: list[YamlValue] = []
    for name, value in (
        ("domain", task.domain),
        ("entity_name", task.entity),
        ("output_type", task.output_type),
        ("audience", task.audience),
        ("research_depth", task.depth),
        ("packet_id", task.packet_id),
    ):
        if value:
            fields.append(name)
    return fields


def _fields_inferred(task: TaskRequest) -> list[YamlValue]:
    all_fields = {"domain", "entity_name", "output_type", "audience", "research_depth", "packet_id"}
    inferred: list[YamlValue] = []
    for field in sorted(all_fields - set(str(field) for field in _fields_explicit(task))):
        inferred.append(field)
    return inferred


def _pack_exists(domain: str, root: Path | None) -> bool:
    if root and (root / "domains" / domain).exists():
        return True
    return domain in {"general", "basketball", "music", "technical"}


def _optional_string(value: YamlValue | None) -> str | None:
    return value if isinstance(value, str) and value else None
