from __future__ import annotations

from datetime import datetime

from rdw.yaml_io import YamlMapping, YamlValue


def validate_mature_basketball_packet(data: YamlMapping) -> list[str]:
    errors: list[str] = []
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
        _validate_metric(metric, index, fact_ids, errors)

    entity_type = _string_value(data.get("entity_type"))
    extensions = data.get("extensions")
    if not isinstance(extensions, dict):
        errors.append("mature basketball packet requires extensions")
        return errors
    extension = extensions.get(entity_type)
    if not isinstance(extension, dict):
        errors.append(f"mature basketball packet requires extensions.{entity_type}")
        return errors
    if entity_type == "player":
        _validate_player_extension(extension, data, errors)
    elif entity_type == "ranking":
        _validate_ranking_extension(extension, fact_ids, errors)
    elif entity_type == "team":
        _validate_team_extension(extension, errors)
    else:
        errors.append(
            "mature basketball validation supports only player, ranking, and team packets"
        )
    return errors


def validate_mature_draft_terms(
    draft: str, packet: YamlMapping, claims: list[YamlValue]
) -> list[str]:
    errors: list[str] = []
    lowered = draft.casefold()
    for phrase in ("high basketball iq", "generational", "can do it all", "blank canvas"):
        if phrase in lowered:
            errors.append(f"draft contains forbidden generic basketball phrase: {phrase}")

    injury_terms = ("injury", "injured", "injuries", "availability", "missed time")
    if not any(term in lowered for term in injury_terms):
        return errors
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
    return errors


def _validate_metric(metric: YamlValue, index: int, fact_ids: set[str], errors: list[str]) -> None:
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


def _validate_player_extension(
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


def _validate_ranking_extension(
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
        for linked_id in _list_value(entity.get("fact_ids")):
            if not isinstance(linked_id, str) or linked_id not in fact_ids:
                errors.append(f"{prefix} references unknown fact id: {linked_id}")


def _validate_team_extension(extension: dict[str, YamlValue], errors: list[str]) -> None:
    _require_mapping_fields(
        extension,
        ("conference", "roster_construction", "pace_environment", "defensive_scheme"),
        "extensions.team",
        errors,
    )


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


def _fact_ids(key_facts: list[YamlValue]) -> set[str]:
    ids: set[str] = set()
    for fact in key_facts:
        if isinstance(fact, dict):
            fact_id = _string_value(fact.get("id"))
            if fact_id:
                ids.add(fact_id)
    return ids


def _list_value(value: YamlValue | None) -> list[YamlValue]:
    return value if isinstance(value, list) else []


def _string_value(value: YamlValue | None) -> str:
    return value if isinstance(value, str) else ""


def _is_missing(value: YamlValue | None) -> bool:
    return value is None or value == "" or value == []


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
