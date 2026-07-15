from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from importlib.resources.abc import Traversable
from pathlib import Path

from rdw.config import enabled_domains, known_domains, output_formats
from rdw.contracts import PACKET_REQUIRED_FIELDS
from rdw.resources import asset_path
from rdw.yaml_io import YamlMapping, YamlValue, load_yaml_mapping, load_yaml_mapping_text

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
    path: Path,
    *,
    strict: bool = False,
    root: Path | None = None,
    allow_disabled: bool = False,
    mature: bool = False,
) -> ValidationResult:
    if not path.exists():
        return ValidationResult(errors=[f"not found: {path}"], warnings=[])
    try:
        data = load_yaml_mapping(path)
    except ValueError as exc:
        return ValidationResult(errors=[f"invalid: {exc}"], warnings=[])
    return validate_packet(
        data,
        strict=strict,
        root=root,
        allow_disabled=allow_disabled,
        mature=mature,
    )


def validate_packet(
    data: YamlMapping,
    *,
    strict: bool = False,
    root: Path | None = None,
    allow_disabled: bool = False,
    mature: bool = False,
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    validation_strict = strict or mature
    for field in PACKET_REQUIRED_FIELDS:
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
    elif validation_strict:
        for index, fact in enumerate(key_facts, start=1):
            if not isinstance(fact, dict) or not _string_value(fact.get("id")):
                errors.append(f"key_facts[{index}] must be a mapping with an id in strict mode")

    fact_ids = _fact_ids(key_facts)
    source_notes = _list_value(data.get("source_notes"))
    if not source_notes:
        errors.append("source_notes must be a non-empty list")
    else:
        errors.extend(_validate_source_notes(source_notes, fact_ids, strict=validation_strict))

    last_updated = _string_value(data.get("last_updated"))
    if last_updated and not _is_datetime_like(last_updated):
        errors.append("last_updated must be an ISO date or datetime string")
    if (
        validation_strict
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

    if not validation_strict and not fact_ids:
        warnings.append("key_facts do not expose fact ids; strict source linkage is limited")

    if mature:
        if domain != "basketball":
            errors.append("mature validation is currently implemented only for basketball")
        else:
            _validate_mature_basketball_packet(data, errors)

    return ValidationResult(errors=errors, warnings=warnings)


def validate_claim_ledger_file(
    packet_path: Path,
    ledger_path: Path,
    *,
    root: Path | None = None,
    mature: bool = False,
) -> ValidationResult:
    for path in (packet_path, ledger_path):
        if not path.exists():
            return ValidationResult(errors=[f"not found: {path}"], warnings=[])
    try:
        packet = load_yaml_mapping(packet_path)
        ledger = load_yaml_mapping(ledger_path)
    except ValueError as exc:
        return ValidationResult(errors=[f"invalid: {exc}"], warnings=[])
    return validate_claim_ledger(packet, ledger, root=root, mature=mature)


def validate_claim_ledger(
    packet: YamlMapping,
    ledger: YamlMapping,
    *,
    root: Path | None = None,
    mature: bool = False,
) -> ValidationResult:
    packet_result = validate_packet(packet, strict=True, root=root, mature=mature)
    if not packet_result.ok:
        return packet_result

    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(ledger.get("pass"), bool):
        errors.append("claim ledger pass must be true or false")
    issues = ledger.get("issues")
    if not isinstance(issues, list):
        errors.append("claim ledger issues must be a list")
    blocking_count = ledger.get("blocking_issue_count")
    if (
        not isinstance(blocking_count, int)
        or isinstance(blocking_count, bool)
        or blocking_count < 0
    ):
        errors.append("claim ledger blocking_issue_count must be a non-negative integer")
    else:
        for index, issue in enumerate(_list_value(issues), start=1):
            if not isinstance(issue, dict):
                errors.append(f"claim ledger issues[{index}] must be a mapping")
                continue
            severity = _string_value(issue.get("severity"))
            if severity not in {"blocker", "major", "minor"}:
                errors.append(f"claim ledger issues[{index}] severity must be blocker|major|minor")
        severe_count = sum(
            1
            for issue in _list_value(issues)
            if isinstance(issue, dict)
            and _string_value(issue.get("severity")) in {"blocker", "major"}
        )
        if blocking_count != severe_count:
            errors.append(
                "claim ledger blocking_issue_count must equal the number of blocker and major issues"
            )
        if ledger.get("pass") is True and severe_count:
            errors.append("claim ledger cannot pass with blocker or major issues")

    claims = _list_value(ledger.get("claim_ledger"))
    if not claims:
        errors.append("claim_ledger must be a non-empty list")
    fact_ids = _fact_ids(_list_value(packet.get("key_facts")))
    source_fact_ids = _source_fact_ids(_list_value(packet.get("source_notes")))
    seen_claim_ids: set[str] = set()
    for index, claim in enumerate(claims, start=1):
        if not isinstance(claim, dict):
            errors.append(f"claim_ledger[{index}] must be a mapping")
            continue
        claim_id = _string_value(claim.get("claim_id"))
        if not claim_id:
            errors.append(f"claim_ledger[{index}] missing claim_id")
        elif claim_id in seen_claim_ids:
            errors.append(f"claim_ledger duplicate claim_id: {claim_id}")
        else:
            seen_claim_ids.add(claim_id)
        if not _string_value(claim.get("text")):
            errors.append(f"claim_ledger[{index}] missing text")
        linked_ids = _list_value(claim.get("fact_ids"))
        if not linked_ids:
            errors.append(f"claim_ledger[{index}] must link fact_ids")
        for linked_id in linked_ids:
            if not isinstance(linked_id, str) or not linked_id:
                errors.append(f"claim_ledger[{index}] fact_ids must contain strings")
            elif linked_id not in fact_ids:
                errors.append(f"claim_ledger[{index}] references unknown fact id: {linked_id}")
            elif linked_id not in source_fact_ids:
                errors.append(f"claim_ledger[{index}] fact id lacks source mapping: {linked_id}")
    draft = ledger.get("draft")
    if draft is not None and not isinstance(draft, str):
        errors.append("claim ledger draft must be a string when supplied")
    elif isinstance(draft, str) and draft:
        _validate_mature_draft_terms(draft, packet, claims, errors)
    return ValidationResult(errors=errors, warnings=warnings)


def _validate_mature_basketball_packet(data: YamlMapping, errors: list[str]) -> None:
    for field in ("time_period", "context", "role_or_usage_context"):
        if _is_missing(data.get(field)):
            errors.append(f"mature basketball packet missing {field}")
    for field in ("open_questions", "uncertainties", "domain_terms", "concepts_that_apply"):
        value = data.get(field)
        if not isinstance(value, list) or not value:
            errors.append(f"mature basketball packet requires a non-empty {field} list")

    key_facts = _list_value(data.get("key_facts"))
    fact_ids = _fact_ids(key_facts)
    for index, fact in enumerate(key_facts, start=1):
        if not isinstance(fact, dict):
            errors.append(f"key_facts[{index}] must be a mapping in mature mode")
            continue
        if not _string_value(fact.get("id")):
            errors.append(f"key_facts[{index}] missing id in mature mode")
        if not _string_value(fact.get("text")):
            errors.append(f"key_facts[{index}] missing text in mature mode")

    source_notes = _list_value(data.get("source_notes"))
    linked_source_fact_ids = _source_fact_ids(source_notes)
    for index, note in enumerate(source_notes, start=1):
        if not isinstance(note, dict):
            continue
        source_text = (
            f"{_string_value(note.get('source'))} {_string_value(note.get('note'))}".lower()
        )
        if "synthetic" in source_text or "demo" in source_text:
            errors.append(f"source_notes[{index}] synthetic/demo provenance is not allowed")
    for fact_id in sorted(fact_ids - linked_source_fact_ids):
        errors.append(f"mature packet fact lacks source mapping: {fact_id}")

    metrics = _list_value(data.get("relevant_metrics"))
    if not metrics:
        errors.append("mature basketball packet requires a non-empty relevant_metrics list")
    for index, metric in enumerate(metrics, start=1):
        _validate_mature_metric(metric, index, fact_ids, errors)

    entity_type = _string_value(data.get("entity_type"))
    extensions = data.get("extensions")
    if not isinstance(extensions, dict):
        errors.append("mature basketball packet requires extensions")
        return
    extension = extensions.get(entity_type)
    if not isinstance(extension, dict):
        errors.append(f"mature basketball packet requires extensions.{entity_type}")
        return
    if entity_type == "player":
        _validate_mature_player_extension(extension, data, errors)
    elif entity_type == "ranking":
        _validate_mature_ranking_extension(extension, fact_ids, errors)
    elif entity_type == "team":
        _validate_mature_team_extension(extension, errors)
    else:
        errors.append(
            "mature basketball validation supports only player, ranking, and team packets"
        )


def _validate_mature_metric(
    metric: YamlValue, index: int, fact_ids: set[str], errors: list[str]
) -> None:
    if not isinstance(metric, dict):
        errors.append(f"relevant_metrics[{index}] must be a mapping in mature mode")
        return
    prefix = f"relevant_metrics[{index}]"
    for field in (
        "name",
        "value",
        "unit",
        "denominator",
        "sample",
        "what_it_captures",
        "what_it_misses",
    ):
        if _is_missing(metric.get(field)):
            errors.append(f"{prefix} missing {field}")
    if all(_is_missing(metric.get(field)) for field in ("season", "period", "time_period")):
        errors.append(f"{prefix} missing season or period")
    linked_ids = _list_value(metric.get("fact_ids"))
    if not linked_ids:
        errors.append(f"{prefix} must link fact_ids")
    for linked_id in linked_ids:
        if not isinstance(linked_id, str) or not linked_id:
            errors.append(f"{prefix} fact_ids must contain strings")
        elif linked_id not in fact_ids:
            errors.append(f"{prefix} references unknown fact id: {linked_id}")


def _validate_mature_player_extension(
    extension: dict[str, YamlValue], data: YamlMapping, errors: list[str]
) -> None:
    required_fields = (
        "team",
        "season",
        "role",
        "archetype",
        "usage",
        "age",
        "physical_profile",
        "minutes_stability",
    )
    _require_mapping_fields(extension, required_fields, "extensions.player", errors)
    for field in ("team", "season", "role"):
        if _is_missing(extension.get(field)):
            errors.append(f"extensions.player missing {field} value")
    minutes_stability = _string_value(extension.get("minutes_stability"))
    if minutes_stability not in {"stable", "volatile", "unknown"}:
        errors.append("extensions.player.minutes_stability must be stable|volatile|unknown")
    usage = extension.get("usage")
    if not isinstance(usage, dict):
        errors.append("extensions.player.usage must be a mapping")
    else:
        _require_mapping_fields(
            usage, ("usg_pct", "on_ball_pct"), "extensions.player.usage", errors
        )
    sample_games = extension.get("sample_games")
    if isinstance(sample_games, int) and not isinstance(sample_games, bool) and sample_games < 15:
        confidence = _string_value(data.get("confidence_level"))
        if confidence != "low":
            errors.append("player samples under 15 games require confidence_level: low")


def _validate_mature_ranking_extension(
    extension: dict[str, YamlValue], fact_ids: set[str], errors: list[str]
) -> None:
    required_fields = (
        "ranking_name",
        "metric_definition",
        "population",
        "filters",
        "rank_value",
        "tie_behavior",
        "missing_value_behavior",
        "methodology_notes",
        "known_limitations",
        "updated_at",
        "freshness_window_days",
    )
    _require_mapping_fields(extension, required_fields, "extensions.ranking", errors)
    if _is_missing(extension.get("season")) and _is_missing(extension.get("update_window")):
        errors.append("extensions.ranking requires season or update_window")
    updated_at = _string_value(extension.get("updated_at"))
    if not updated_at or not _is_datetime_like(updated_at):
        errors.append("extensions.ranking.updated_at must be an ISO date or datetime string")
    elif not _is_tz_aware(updated_at):
        errors.append("extensions.ranking.updated_at must be timezone-aware")
    freshness_window_days = extension.get("freshness_window_days")
    if (
        not isinstance(freshness_window_days, int)
        or isinstance(freshness_window_days, bool)
        or freshness_window_days <= 0
    ):
        errors.append("extensions.ranking.freshness_window_days must be a positive integer")

    ranked_entities = extension.get("ranked_entities")
    source_reference = extension.get("source_reference")
    if not isinstance(ranked_entities, list) or not ranked_entities:
        if _is_missing(source_reference):
            errors.append("extensions.ranking requires ranked_entities or source_reference")
        return
    for index, entity in enumerate(ranked_entities, start=1):
        if not isinstance(entity, dict):
            errors.append(f"extensions.ranking.ranked_entities[{index}] must be a mapping")
            continue
        prefix = f"extensions.ranking.ranked_entities[{index}]"
        for field in ("entity_name", "rank", "value", "fact_ids"):
            if _is_missing(entity.get(field)):
                errors.append(f"{prefix} missing {field}")
        rank = entity.get("rank")
        if not isinstance(rank, int) or isinstance(rank, bool) or rank <= 0:
            errors.append(f"{prefix}.rank must be a positive integer")
        linked_ids = _list_value(entity.get("fact_ids"))
        for linked_id in linked_ids:
            if not isinstance(linked_id, str) or linked_id not in fact_ids:
                errors.append(f"{prefix} references unknown fact id: {linked_id}")


def _validate_mature_team_extension(extension: dict[str, YamlValue], errors: list[str]) -> None:
    _require_mapping_fields(
        extension,
        ("conference", "roster_construction", "pace_environment", "defensive_scheme"),
        "extensions.team",
        errors,
    )


def _validate_mature_draft_terms(
    draft: str, packet: YamlMapping, claims: list[YamlValue], errors: list[str]
) -> None:
    lowered = draft.casefold()
    for phrase in ("high basketball iq", "generational", "can do it all", "blank canvas"):
        if phrase in lowered:
            errors.append(f"draft contains forbidden generic basketball phrase: {phrase}")

    injury_terms = ("injury", "injured", "injuries", "availability", "missed time")
    if not any(term in lowered for term in injury_terms):
        return
    factual_injury_ids: set[str] = set()
    for fact in _list_value(packet.get("key_facts")):
        if not isinstance(fact, dict):
            continue
        fact_text = _string_value(fact.get("text")).casefold()
        if any(term in fact_text for term in injury_terms):
            fact_id = _string_value(fact.get("id"))
            if fact_id:
                factual_injury_ids.add(fact_id)
    claimed_injury_ids: set[str] = set()
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        claim_text = _string_value(claim.get("text")).casefold()
        if any(term in claim_text for term in injury_terms):
            claimed_injury_ids.update(
                fact_id
                for fact_id in _list_value(claim.get("fact_ids"))
                if isinstance(fact_id, str)
            )
    if not factual_injury_ids or not factual_injury_ids.intersection(claimed_injury_ids):
        errors.append("draft contains unsupported injury/availability claim")


def _require_mapping_fields(
    mapping: dict[str, YamlValue], fields: tuple[str, ...], prefix: str, errors: list[str]
) -> None:
    for field in fields:
        if field not in mapping:
            errors.append(f"{prefix} missing {field}")


def _source_fact_ids(source_notes: list[YamlValue]) -> set[str]:
    ids: set[str] = set()
    for note in source_notes:
        if not isinstance(note, dict):
            continue
        for fact_id in _list_value(note.get("fact_ids")):
            if isinstance(fact_id, str) and fact_id:
                ids.add(fact_id)
    return ids


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
    try:
        if isinstance(config_path, Path):
            config = load_yaml_mapping(config_path)
        elif config_path is not None:
            config = load_yaml_mapping_text(
                config_path.read_text(encoding="utf-8"), source=str(config_path)
            )
        else:
            return False
    except (OSError, ValueError):
        return False
    schema = config.get("extensions_schema")
    return isinstance(schema, dict) and entity_type in schema


def _domain_config_path(domain: str, root: Path | None) -> Path | Traversable | None:
    if root:
        candidate = root / "domains" / domain / "domain-config.yaml"
        if candidate.exists():
            return candidate
    candidate = asset_path("domains", domain, "domain-config.yaml")
    return candidate if candidate.is_file() else None


def _packet_exists(packet_id: str, domain: str, root: Path | None) -> bool:
    if not root:
        root = Path.cwd()
    search_domains = [domain] if domain else ["basketball", "music", "technical", "general"]
    for search_domain in search_domains:
        candidate = root / "knowledge" / search_domain / f"{packet_id}.yaml"
        if candidate.exists():
            return True
        knowledge_dir = root / "knowledge" / search_domain
        if knowledge_dir.exists():
            for packet_path in knowledge_dir.glob("*.yaml"):
                try:
                    packet = load_yaml_mapping(packet_path)
                except ValueError:
                    continue
                if packet.get("id") == packet_id:
                    return True
        packaged_dir = asset_path("knowledge", search_domain)
        if not packaged_dir.is_dir():
            continue
        for packet_path in packaged_dir.iterdir():
            if not packet_path.name.endswith(".yaml"):
                continue
            try:
                packet = load_yaml_mapping_text(
                    packet_path.read_text(encoding="utf-8"), source=str(packet_path)
                )
            except (OSError, ValueError):
                continue
            if packet.get("id") == packet_id:
                return True
    return False
