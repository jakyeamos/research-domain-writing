from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import yaml

YamlScalar = str | int | float | bool | None
YamlValue = YamlScalar | list["YamlValue"] | dict[str, "YamlValue"]
YamlMapping = dict[str, YamlValue]


def load_yaml(path: Path) -> YamlValue:
    return load_yaml_text(path.read_text(encoding="utf-8"), source=str(path))


def load_yaml_text(text: str, *, source: str = "<text>") -> YamlValue:
    try:
        data: object = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML in {source}: {exc}") from exc
    return normalize_yaml(data)


def load_yaml_mapping(path: Path) -> YamlMapping:
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise ValueError("root must be a mapping")
    return data


def load_yaml_mapping_text(text: str, *, source: str = "<text>") -> YamlMapping:
    data = load_yaml_text(text, source=source)
    if not isinstance(data, dict):
        raise ValueError(f"root must be a mapping: {source}")
    return data


def dump_yaml(data: Mapping[str, YamlValue]) -> str:
    return yaml.safe_dump(dict(data), sort_keys=False, allow_unicode=False)


def normalize_yaml(value: object) -> YamlValue:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Mapping):
        normalized: YamlMapping = {}
        for key, item in value.items():
            normalized[str(key)] = normalize_yaml(item)
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [normalize_yaml(item) for item in value]
    return str(value)
