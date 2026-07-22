from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import UTC, datetime
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

from rdw import __version__

ASSET_PACKAGE = "rdw.assets"
MANAGED_MARKER = ".rdw-managed.json"


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


def copy_package_assets(destination: Path, *, backup: bool = False, force: bool = False) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.stage-", dir=destination.parent))
    previous: Path | None = None
    try:
        copy_asset_tree(asset_root(), stage)
        _write_manifest(stage)
        _verify_asset_tree(stage)
        if destination.exists() or destination.is_symlink():
            if not _is_managed(destination) and not backup and not force:
                raise ValueError(
                    f"unmanaged install root in the way: {destination} (use --force or --backup)"
                )
            previous = destination.with_name(
                f"{destination.name}.bak-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
            )
            os.replace(destination, previous)
        try:
            os.replace(stage, destination)
        except BaseException:
            if previous is not None and not destination.exists():
                os.replace(previous, destination)
            raise
        if previous is not None and not backup and _is_managed(previous):
            shutil.rmtree(previous)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def _write_manifest(destination: Path) -> None:
    files = sorted(
        str(path.relative_to(destination)) for path in destination.rglob("*") if path.is_file()
    )
    payload = {"format_version": 1, "rdw_version": __version__, "files": files}
    (destination / MANAGED_MARKER).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def _is_managed(path: Path) -> bool:
    marker = path / MANAGED_MARKER
    if not marker.is_file():
        return False
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get("format_version") == 1


def _verify_asset_tree(destination: Path) -> None:
    expected = _asset_bytes(asset_root())
    actual = {
        str(path.relative_to(destination)): path.read_bytes()
        for path in destination.rglob("*")
        if path.is_file() and path.name != MANAGED_MARKER
    }
    if expected != actual:
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise ValueError(
            f"staged package assets failed verification: missing={missing}, extra={extra}"
        )


def _asset_bytes(source: Traversable, prefix: str = "") -> dict[str, bytes]:
    if source.is_file():
        return {prefix: source.read_bytes()}
    result: dict[str, bytes] = {}
    for child in source.iterdir():
        child_prefix = f"{prefix}/{child.name}" if prefix else child.name
        result.update(_asset_bytes(child, child_prefix))
    return result
