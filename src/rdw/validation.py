from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rdw.config import enabled_domains, known_domains, output_formats
from rdw.yaml_io import YamlMapping, YamlValue, load_yaml_mapping

REQUIRED_PACKET_FIELDS = {
    "id",
    "domain",
    "entity_type",
    "entity_name",
    "key_facts",
    "source_notes",
    "confidence_level",
    "last_updated",
}
CONFIDENCE_VALUES = {"high", "medium", "low"}
DEPTH_ALIASES = {
    "1": "deep",
    "2": "standard",
    "3": "light",
    "4": "minimal",
    "deep": "deep",
    "standard": "standard",
    "light": "light",
    "minimal": "minimal",
}


@dataclass(frozen=True)
class ValidationResult:
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, object]:
        return {"ok": self.ok, "errors": self.errors, "warnings": self.warnings}


def validate_packet_file(
    path: Path, *, strict: bool = False, root: Path | None = None, allow_disabled: bool = False
) -> ValidationResult:
    if not path.exists():
        return ValidationResult(errors=[f"not found: {path}"], warnings=[])
    try:
        data = load_yaml_mapping(path)
    except ValueError as exc:
        return ValidationResult(errors=[f"invalid: {exc}"], warnings=[])
    return validate_packet(data, strict=strict, root=root, allow_disabled=allow_disabled)


def validate_packet(
    data: YamlMapping,
    *,
    strict: bool = False,
    root: Path | None = None,
    allow_disabled: bool = False,
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    for field in sorted(REQUIRED_PACKET_FIELDS):
        if _is_missing(data.get(field)):
            errors.append(f"missing or empty required field: {field}")

    domain = _string_value(data.get("domain"))
    if domain:
        if domain not in known_domains(root):
            errors.append(f"domain is not registered: {domain}")
        elif domain not in enabled_domains(root):
            message = f"domain is registered but disabled: {domain}"
            if not strict:
                warnings.append(message)
            elif not allow_disabled:
                errors.append(message)

    confidence = _string_value(data.get("confidence_level"))
    if confidence not in CONFIDENCE_VALUES:
        errors.append("confidence_level must be high|medium|low")

    key_facts = _list_value(data.get("key_facts"))
    if not key_facts:
        errors.append("key_facts must be a non-empty list")
    elif strict:
        for index, fact in enumerate(key_facts, start=1):
            if not isinstance(fact, dict) or not _string_value(fact.get("id")):
                errors.append(f"key_facts[{index}] must be a mapping with an id in strict mode")

    fact_ids = _fact_ids(key_facts)
    source_notes = _list_value(data.get("source_notes"))
    if not source_notes:
        errors.append("source_notes must be a non-empty list")
    else:
        errors.extend(_validate_source_notes(source_notes, fact_ids, strict=strict))

    last_updated = _string_value(data.get("last_updated"))
    if last_updated and not _is_datetime_like(last_updated):
        errors.append("last_updated must be an ISO date or datetime string")
    if (
        strict
        and last_updated
        and _is_datetime_like(last_updated)
        and not _is_tz_aware(last_updated)
    ):
        errors.append("last_updated must be timezone-aware in strict mode")

    entity_type = _string_value(data.get("entity_type"))
    extensions = data.get("extensions")
    if (
        strict
        and entity_type
        and _domain_requires_extension(domain, entity_type, root)
        and (not isinstance(extensions, dict) or entity_type not in extensions)
    ):
        errors.append(f"extensions must include domain-specific block: {entity_type}")

    if not strict and not fact_ids:
        warnings.append("key_facts do not expose fact ids; strict source linkage is limited")

    return ValidationResult(errors=errors, warnings=warnings)


def validate_batch_file(path: Path, *, root: Path | None = None) -> ValidationResult:
    if not path.exists():
        return ValidationResult(errors=[f"not found: {path}"], warnings=[])
    try:
        data = load_yaml_mapping(path)
    except ValueError as exc:
        return ValidationResult(errors=[f"invalid: {exc}"], warnings=[])
    return validate_batch(data, root=root)


def validate_batch(data: YamlMapping, *, root: Path | None = None) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    batch_id = _string_value(data.get("batch_id"))
    if not batch_id:
        errors.append("missing or empty required field: batch_id")
    tasks = _list_value(data.get("tasks"))
    if not tasks:
        errors.append("tasks must be a non-empty list")
        return ValidationResult(errors=errors, warnings=warnings)

    seen_ids: set[str] = set()
    known_formats = output_formats(root)
    for index, task in enumerate(tasks, start=1):
        if not isinstance(task, dict):
            errors.append(f"tasks[{index}] must be a mapping")
            continue
        task_id = _string_value(task.get("task_id"))
        if not task_id:
            errors.append(f"tasks[{index}] missing task_id")
        elif task_id in seen_ids:
            errors.append(f"duplicate task_id: {task_id}")
        else:
            seen_ids.add(task_id)
        if not _string_value(task.get("request")):
            errors.append(f"tasks[{index}] missing request")
        depth = task.get("research_depth")
        if depth is not None and normalize_depth(str(depth)) is None:
            errors.append(f"tasks[{index}] invalid research_depth: {depth}")
        packet_id = _string_value(task.get("packet_id"))
        domain = _string_value(task.get("domain"))
        if packet_id and not _packet_exists(packet_id, domain, root):
            errors.append(f"tasks[{index}] packet_id not found: {packet_id}")
        output_format = _string_value(task.get("output_format"))
        if output_format and output_format not in known_formats:
            errors.append(f"tasks[{index}] unsupported output_format: {output_format}")
    defaults = data.get("defaults")
    if isinstance(defaults, dict):
        default_format = _string_value(defaults.get("output_format"))
        if default_format and default_format not in known_formats:
            errors.append(f"defaults unsupported output_format: {default_format}")
        default_depth = defaults.get("research_depth")
        if default_depth is not None and normalize_depth(str(default_depth)) is None:
            errors.append(f"defaults invalid research_depth: {default_depth}")
    elif defaults is not None:
        warnings.append("defaults should be a mapping")
    return ValidationResult(errors=errors, warnings=warnings)


def normalize_depth(value: str) -> str | None:
    return DEPTH_ALIASES.get(value.strip().lower())


def _is_missing(value: YamlValue | None) -> bool:
    return value is None or value == "" or value == []


def _string_value(value: YamlValue | None) -> str:
    return value if isinstance(value, str) else ""


def _list_value(value: YamlValue | None) -> list[YamlValue]:
    return value if isinstance(value, list) else []


def _fact_ids(key_facts: list[YamlValue]) -> set[str]:
    ids: set[str] = set()
    for fact in key_facts:
        if isinstance(fact, dict):
            fact_id = _string_value(fact.get("id"))
            if fact_id:
                ids.add(fact_id)
    return ids


def _validate_source_notes(
    source_notes: list[YamlValue], fact_ids: set[str], *, strict: bool
) -> list[str]:
    errors: list[str] = []
    for index, note in enumerate(source_notes, start=1):
        if not isinstance(note, dict):
            errors.append(f"source_notes[{index}] must be a mapping")
            continue
        for field in ("source", "accessed", "note"):
            if _is_missing(note.get(field)):
                errors.append(f"source_notes[{index}] missing {field}")
        accessed = note.get("accessed")
        if isinstance(accessed, str) and accessed and not _is_datetime_like(accessed):
            errors.append(f"source_notes[{index}] accessed must be an ISO date")
        if strict:
            source_error = _source_format_error(
                _string_value(note.get("source")), _string_value(note.get("source_type"))
            )
            if source_error:
                errors.append(f"source_notes[{index}] {source_error}")
        linked_ids = _list_value(note.get("fact_ids"))
        if strict and fact_ids and not linked_ids:
            errors.append(f"source_notes[{index}] must link fact_ids in strict mode")
        for linked_id in linked_ids:
            if isinstance(linked_id, str) and fact_ids and linked_id not in fact_ids:
                errors.append(f"source_notes[{index}] references unknown fact id: {linked_id}")
    return errors


def _is_datetime_like(value: str) -> bool:
    candidates = [value, value.replace("Z", "+00:00")]
    for candidate in candidates:
        try:
            datetime.fromisoformat(candidate)
            return True
        except ValueError:
            continue
    return False


def _is_tz_aware(value: str) -> bool:
    for candidate in (value, value.replace("Z", "+00:00")):
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            continue
        return parsed.tzinfo is not None
    return False


_DOI_RE = re.compile(r"^(doi:)?10\.\d{4,9}/\S+$", re.IGNORECASE)
_URL_RE = re.compile(r"^https?://[^\s]+\.[^\s]+", re.IGNORECASE)


def _source_format_error(source: str, source_type: str) -> str | None:
    value = source.strip()
    lower = value.lower()
    if source_type == "url":
        return None if _URL_RE.match(value) else "source must be a URL for source_type: url"
    if source_type == "doi":
        return None if _DOI_RE.match(value) else "source must be a DOI for source_type: doi"
    if lower.startswith(("http://", "https://")) and not _URL_RE.match(value):
        return f"malformed URL source: {source}"
    if lower.startswith(("doi:", "10.")) and not _DOI_RE.match(value):
        return f"malformed DOI source: {source}"
    return None


def _domain_requires_extension(domain: str, entity_type: str, root: Path | None) -> bool:
    if not domain or not entity_type:
        return False
    config_path = _domain_config_path(domain, root)
    if config_path is None:
        return False
    try:
        config = load_yaml_mapping(config_path)
    except ValueError:
        return False
    schema = config.get("extensions_schema")
    return isinstance(schema, dict) and entity_type in schema


def _domain_config_path(domain: str, root: Path | None) -> Path | None:
    if root:
        candidate = root / "domains" / domain / "domain-config.yaml"
        if candidate.exists():
            return candidate
    return None


def _packet_exists(packet_id: str, domain: str, root: Path | None) -> bool:
    if not root:
        root = Path.cwd()
    search_domains = [domain] if domain else ["basketball", "music", "technical", "general"]
    for search_domain in search_domains:
        candidate = root / "knowledge" / search_domain / f"{packet_id}.yaml"
        if candidate.exists():
            return True
        knowledge_dir = root / "knowledge" / search_domain
        if not knowledge_dir.exists():
            continue
        for packet_path in knowledge_dir.glob("*.yaml"):
            try:
                packet = load_yaml_mapping(packet_path)
            except ValueError:
                continue
            if packet.get("id") == packet_id:
                return True
    return False
