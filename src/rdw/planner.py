from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from rdw.config import default_output_format, output_formats
from rdw.resources import read_asset_text
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


def plan_task(task: TaskRequest, output_dir: Path, *, root: Path | None = None) -> PlannedTask:
    contract = infer_contract(task, root=root)
    task_id = str(contract["task_id"])
    prompt_bundle = render_prompt_bundle(contract)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "task-contract.yaml").write_text(dump_yaml(contract), encoding="utf-8")
    (output_dir / "prompt-bundle.md").write_text(prompt_bundle, encoding="utf-8")
    status = {
        "task_id": task_id,
        "status": "planned",
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "next_step": "Give prompt-bundle.md to an agent and run the RDW pipeline.",
    }
    (output_dir / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return PlannedTask(task_id=task_id, contract=contract, prompt_bundle=prompt_bundle)


def plan_batch(batch_path: Path, output_dir: Path, *, root: Path | None = None) -> None:
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
                    "needs_review": True,
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
    (output_dir / "summary.yaml").write_text(dump_yaml(summary), encoding="utf-8")
    (output_dir / "batch-log.jsonl").write_text("\n".join(log_lines) + "\n", encoding="utf-8")


def infer_contract(task: TaskRequest, *, root: Path | None = None) -> YamlMapping:
    request = task.request.strip()
    lower = request.lower()
    domain = task.domain or _infer_domain(lower)
    output_type, entity_type = _infer_output(lower)
    entity_name = task.entity or _infer_entity(request, entity_type)
    depth = normalize_depth(task.depth or "") or _infer_depth(lower)
    task_id = task.task_id or _slugify(f"{domain}-{entity_name}-{output_type}")
    audience = task.audience or _infer_audience(lower)
    packet_id = task.packet_id or _default_packet_id(domain, entity_type, entity_name)
    output_format = task.output_format or default_output_format(root)
    warnings: list[YamlValue] = []
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
        "output_type": task.output_type or output_type,
        "output_format": output_format,
        "audience": audience,
        "research_needed": True,
        "research_depth": depth,
        "packet_id": packet_id,
        "inference": {
            "mode": "mixed" if _has_overrides(task) else "inferred",
            "confidence": "medium",
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


def _infer_domain(lower: str) -> str:
    if any(
        token in lower for token in ("nba", "basketball", "leaderboard", "usage", "fantasy", "lis")
    ):
        return "basketball"
    if any(token in lower for token in ("album", "artist", "song", "track", "genre", "production")):
        return "music"
    if any(
        token in lower
        for token in ("api", "feature", "architecture", "sdk", "latency", "release", "idempotency")
    ):
        return "technical"
    return "general"


def _infer_output(lower: str) -> tuple[str, str]:
    if any(token in lower for token in ("leaderboard", "ranking", "rankings", "ladder")):
        return "ranking_explanation", "ranking"
    if "stat" in lower:
        return "stat_interpretation", "player"
    if any(token in lower for token in ("album", "blurb")):
        return "album_review_blurb", "album"
    if any(token in lower for token in ("feature", "how it works", "api", "idempotency")):
        return "feature_explainer", "feature"
    return "summary", "entity"


def _infer_entity(request: str, entity_type: str) -> str:
    lower = request.lower()
    if "idempotency key" in lower:
        return "Idempotency keys"
    leaderboard = re.search(r"(?:my |the )?([A-Z][A-Za-z0-9]+) leaderboard", request)
    if leaderboard:
        return f"{leaderboard.group(1)} leaderboard"
    if entity_type == "ranking":
        return "leaderboard"
    title = request.strip().split(" for ", maxsplit=1)
    if len(title) == 2 and title[1].strip():
        return title[1].strip().strip(".")
    return "requested subject"


def _infer_depth(lower: str) -> str:
    if any(token in lower for token in ("controversial", "lawsuit", "medical", "definitive")):
        return "deep"
    if any(token in lower for token in ("short blurb", "one-liner", "quick note")):
        return "light"
    return "standard"


def _infer_audience(lower: str) -> str:
    if any(token in lower for token in ("leaderboard", "ranking", "fantasy", "analytics")):
        return "fantasy and analytics users who know basic stats"
    if any(token in lower for token in ("album", "track", "genre")):
        return "general music readers"
    if any(token in lower for token in ("api", "developer", "engineer", "architecture")):
        return "backend engineers and technical implementers"
    return "general readers with basic domain literacy"


def _default_packet_id(domain: str, entity_type: str, entity_name: str) -> str:
    return _slugify(f"{domain}-{entity_type}-{entity_name}")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "rdw-task"


def _topic(request: str, output_type: str) -> str:
    return f"{output_type}: {request[:120]}"


def _has_overrides(task: TaskRequest) -> bool:
    return any(
        [task.domain, task.entity, task.output_type, task.audience, task.depth, task.packet_id]
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
