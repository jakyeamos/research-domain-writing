from __future__ import annotations

import shutil
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

ASSET_PACKAGE = "rdw.assets"


def asset_root() -> Traversable:
    return files(ASSET_PACKAGE)


def asset_path(*parts: str) -> Traversable:
    path = asset_root()
    for part in parts:
        path = path.joinpath(part)
    return path


def read_asset_text(*parts: str) -> str:
    return asset_path(*parts).read_text(encoding="utf-8")


def copy_asset_tree(source: Traversable, destination: Path) -> None:
    if source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        return
    destination.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        copy_asset_tree(child, destination / child.name)


def copy_package_assets(destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    copy_asset_tree(asset_root(), destination)
