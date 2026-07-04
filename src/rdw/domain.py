from __future__ import annotations

import re
import shutil
from pathlib import Path

from rdw.resources import asset_path, copy_asset_tree


def create_domain(domain_id: str, display_name: str, *, root: Path) -> Path:
    if not re.fullmatch(r"[a-z][a-z0-9-]*", domain_id):
        raise ValueError("domain id must be kebab-case starting with a letter")
    destination = root / "domains" / domain_id
    if destination.exists():
        raise ValueError(f"exists: {destination}")
    template = root / "domains" / "_template"
    if template.exists():
        shutil.copytree(template, destination)
    else:
        copy_asset_tree(asset_path("domains", "_template"), destination)
    config_path = destination / "domain-config.yaml"
    config = config_path.read_text(encoding="utf-8")
    config = config.replace("_template", domain_id).replace("Template Domain", display_name)
    config_path.write_text(config, encoding="utf-8")
    (root / "knowledge" / domain_id).mkdir(parents=True, exist_ok=True)
    return destination
