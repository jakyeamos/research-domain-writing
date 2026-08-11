from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _sync_assets_module():
    path = ROOT / "scripts" / "sync-package-assets.py"
    spec = importlib.util.spec_from_file_location("sync_package_assets", path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_drift_reports_unmapped_package_files(tmp_path: Path) -> None:
    package_root = tmp_path / "assets"
    for source in ROOT.joinpath("src", "rdw", "assets").iterdir():
        if source.name == "__pycache__":
            continue
        destination = package_root / source.name
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
    stale = package_root / "docs" / "stale.md"
    stale.write_text("stale\n", encoding="utf-8")

    module = _sync_assets_module()

    assert "extra: docs/stale.md" in module.drift(package_root)
