from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rdw.config import load_config
from rdw.yaml_io import YamlMapping, YamlValue


@dataclass(frozen=True)
class RouteResult:
    domain: str
    output_type: str
    entity_type: str
    entity_name: str
    audience: str
    depth: str


def route_request(request: str, *, root: Path | None = None) -> RouteResult:
    config = load_config("router-inference.yaml", root)
    lower = request.strip().lower()
    defaults = _mapping(config.get("defaults"))
    domain = _match_domain(lower, config)
    output_type, entity_type = _match_output(lower, config, defaults)
    entity_name, entity_domain = _match_entity(request, config, entity_type)
    if entity_domain:
        domain = entity_domain
    audience = _match_audience(lower, config, defaults)
    depth = _match_depth(lower, config)
    return RouteResult(
        domain=domain,
        output_type=output_type,
        entity_type=entity_type,
        entity_name=entity_name,
        audience=audience,
        depth=depth,
    )


def _mapping(value: YamlValue | None) -> YamlMapping:
    return value if isinstance(value, dict) else {}


def _sequence(value: YamlValue | None) -> list[YamlValue]:
    return value if isinstance(value, list) else []


def _text(value: YamlValue | None) -> str:
    return value if isinstance(value, str) else ""


def _tokens(entry: YamlMapping) -> list[str]:
    return [str(token).lower() for token in _sequence(entry.get("match"))]


def _match_domain(lower: str, config: YamlMapping) -> str:
    for name, meta in _mapping(config.get("domain_inference")).items():
        keywords = [str(keyword).lower() for keyword in _sequence(_mapping(meta).get("keywords"))]
        if any(keyword in lower for keyword in keywords):
            return str(name)
    return "general"


def _match_output(lower: str, config: YamlMapping, defaults: YamlMapping) -> tuple[str, str]:
    for raw in _sequence(config.get("output_type_inference")):
        entry = _mapping(raw)
        if any(token in lower for token in _tokens(entry)):
            output_type = _text(entry.get("output_type"))
            if output_type:
                return output_type, _text(entry.get("entity_type")) or "entity"
    return _text(defaults.get("output_type")) or "summary", "entity"


def _match_entity(request: str, config: YamlMapping, entity_type: str) -> tuple[str, str | None]:
    for raw in _sequence(config.get("entity_inference")):
        entry = _mapping(raw)
        pattern = _text(entry.get("pattern"))
        if not pattern:
            continue
        match = re.search(pattern, request, flags=re.IGNORECASE)
        if not match:
            continue
        template = _text(entry.get("entity_name_template"))
        if template:
            entity_name = _apply_template(template, match)
        else:
            entity_name = _text(entry.get("entity_name"))
        if entity_name:
            entity_domain = _text(entry.get("domain")) or None
            return entity_name, entity_domain
    if entity_type == "ranking":
        return "leaderboard", None
    title = request.strip().split(" for ", maxsplit=1)
    if len(title) == 2 and title[1].strip():
        return title[1].strip().strip("."), None
    return "requested subject", None


def _apply_template(template: str, match: re.Match[str]) -> str:
    result = template
    for index, group in enumerate(match.groups(), start=1):
        result = result.replace("{" + str(index) + "}", group or "")
    return result


def _match_audience(lower: str, config: YamlMapping, defaults: YamlMapping) -> str:
    for raw in _sequence(config.get("audience_inference")):
        entry = _mapping(raw)
        if any(token in lower for token in _tokens(entry)):
            audience = _text(entry.get("audience"))
            if audience:
                return audience
    return _text(defaults.get("audience")) or "general readers with basic domain literacy"


def _match_depth(lower: str, config: YamlMapping) -> str:
    depth = _mapping(config.get("depth_inference"))
    for level in ("deep", "light"):
        tokens = [str(token).lower() for token in _sequence(depth.get(level))]
        if any(token in lower for token in tokens):
            return level
    return "standard"
