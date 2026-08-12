from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rdw.yaml_io import YamlMapping, YamlValue, load_yaml_mapping

DIFF_QA_CODES = tuple(f"DQA-{index:03d}" for index in range(1, 11))
DIFF_QA_SEVERITIES = ("blocker", "major", "minor")
DIFF_QA_STATUSES = ("pass", "fail", "indeterminate")
DIFF_QA_MODES = ("packet", "draft")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class NormalizedArtifact:
    kind: str
    artifact_id: str
    revision_id: str
    claims: dict[str, YamlMapping]
    sources: dict[str, YamlMapping]
    rules: dict[str, YamlMapping]


def empty_counts() -> dict[str, int]:
    return {
        "claims_added": 0,
        "claims_removed": 0,
        "claims_changed": 0,
        "source_links_removed": 0,
        "uncertainty_removed": 0,
        "rules_regressed": 0,
    }


def yaml_strings(values: list[str]) -> list[YamlValue]:
    return [value for value in values]


def normalize_rules(value: YamlValue | None) -> dict[str, YamlMapping]:
    raw = value.get("rules") if isinstance(value, dict) else value
    if not isinstance(raw, list):
        return {}
    result: dict[str, YamlMapping] = {}
    for rule in raw:
        if not isinstance(rule, dict):
            continue
        rule_id = string(rule.get("rule_id"))
        if rule_id:
            result[rule_id] = {
                "rule_id": rule_id,
                "status": string(rule.get("status")) or "unknown",
                "evidence": normalized_text(string(rule.get("evidence"))),
            }
    return result


def validate_rules(value: YamlValue) -> list[str]:
    if not isinstance(value, list):
        return ["rules must be a list"]
    errors: list[str] = []
    seen: set[str] = set()
    for index, rule in enumerate(value, start=1):
        if not isinstance(rule, dict):
            errors.append(f"rules[{index}] must be a mapping")
            continue
        rule_id = string(rule.get("rule_id"))
        status = string(rule.get("status"))
        if not rule_id:
            errors.append(f"rules[{index}] missing rule_id")
        elif rule_id in seen:
            errors.append(f"rules duplicate rule_id: {rule_id}")
        seen.add(rule_id)
        if status not in {"pass", "fail", "unknown"}:
            errors.append(f"rules[{index}] status must be pass|fail|unknown")
    return errors


def manifest_ledger_path(root: Path, manifest: YamlMapping) -> Path | None:
    reference = string(manifest.get("claim_ledger_path"))
    if not reference:
        return None
    return safe_relative(root, reference)


def conventional_ledger_path(root: Path, draft_path: Path) -> Path:
    output_id = draft_path.stem
    return root / "outputs" / "qa" / f"{output_id}-claims.yaml"


def resolve_manifest_artifact(root: Path, manifest: YamlMapping, field: str) -> Path | None:
    return safe_relative(root, string(manifest.get(field)))


def safe_relative(root: Path, reference: str) -> Path | None:
    if not reference:
        return None
    path = Path(reference)
    if path.is_absolute() or ".." in path.parts:
        return None
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        return None
    return resolved


def try_load_mapping(path: Path) -> YamlMapping | None:
    try:
        return load_yaml_mapping(path)
    except (OSError, ValueError):
        return None


def hash_file(path: Path) -> str | None:
    try:
        return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def is_sha256(value: str) -> bool:
    return bool(_SHA256_RE.fullmatch(value))


def string(value: YamlValue | None) -> str:
    return value if isinstance(value, str) else ""


def string_list(value: YamlValue | None) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def normalized_text(value: str) -> str:
    return " ".join(value.replace("\r\n", "\n").replace("\r", "\n").split())


def uncertainty(mapping: dict[str, YamlValue]) -> str:
    value = mapping.get("uncertainty")
    if isinstance(value, str) and value:
        return value.strip().lower()
    if mapping.get("uncertainty_required") is True:
        return "required"
    return "unknown"


def semantic_payload(mapping: dict[str, YamlValue], excluded: set[str] | None = None) -> YamlValue:
    excluded = excluded or {"id", "source_ids", "uncertainty", "required"}
    return plain({key: value for key, value in mapping.items() if key not in excluded})


def source_semantic(value: YamlMapping) -> YamlValue:
    return {
        "source_normalized": value.get("source_normalized"),
        "source_type": value.get("source_type"),
        "evidence_boundary": value.get("evidence_boundary"),
    }


def plain(value: YamlValue) -> YamlValue:
    if isinstance(value, dict):
        return {key: plain(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


def short_hash(value: YamlValue) -> str:
    payload = json.dumps(plain(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def valid_timestamp(value: str) -> bool:
    if not value:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True
