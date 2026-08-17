from __future__ import annotations

from pathlib import Path

from rdw.resources import asset_path
from rdw.yaml_io import YamlMapping, YamlValue, load_yaml, load_yaml_mapping, normalize_yaml


def config_root(root: Path | None) -> Path | None:
    if root and (root / "config" / "domains.yaml").exists():
        return root
    return None


def load_config(name: str, root: Path | None) -> YamlMapping:
    local_root = config_root(root)
    if local_root and (local_root / "config" / name).exists():
        return load_yaml_mapping(local_root / "config" / name)
    asset = asset_path("config", name)
    temp_path = Path(str(asset)) if isinstance(asset, Path) else None
    if temp_path and temp_path.exists():
        raw = load_yaml(temp_path)
    else:
        import yaml

        loaded: object = yaml.safe_load(asset.read_text(encoding="utf-8"))
        raw = normalize_yaml(loaded)
    if not isinstance(raw, dict):
        return {}
    return raw


def _domain_registry(root: Path | None) -> dict[str, YamlValue]:
    config = load_config("domains.yaml", root)
    domains = config.get("domains")
    return domains if isinstance(domains, dict) else {}


def known_domains(root: Path | None) -> set[str]:
    domains = {str(key) for key in _domain_registry(root)}
    return domains or {"general"}


def enabled_domains(root: Path | None) -> set[str]:
    enabled: set[str] = set()
    for key, meta in _domain_registry(root).items():
        if isinstance(meta, dict) and meta.get("enabled") is False:
            continue
        enabled.add(str(key))
    return enabled or {"general"}


def output_formats(root: Path | None) -> set[str]:
    config = load_config("output-formats.yaml", root)
    formats = config.get("formats")
    if not isinstance(formats, dict):
        return {"markdown"}
    return {str(key) for key in formats}


def default_output_format(root: Path | None) -> str:
    config = load_config("output-formats.yaml", root)
    value = config.get("default_format")
    return value if isinstance(value, str) and value else "markdown"
