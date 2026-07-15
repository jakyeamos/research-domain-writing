#!/usr/bin/env python3
"""Synchronize the canonical repository content into packaged assets."""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "src" / "rdw" / "assets"


@dataclass(frozen=True)
class AssetPair:
    source: Path
    destination: Path


DIRECTORIES = ("config", "domains", "examples", "install", "knowledge", "prompts")
FILES = (
    ("CHANGELOG.md", "CHANGELOG.md"),
    ("LICENSE", "LICENSE"),
    ("README.md", "README.md"),
    ("RELEASE.md", "RELEASE.md"),
    ("SKILL.md", "SKILL.md"),
    ("docs/FUTURE-AIOS-INTEGRATION.md", "docs/FUTURE-AIOS-INTEGRATION.md"),
    ("docs/LIMITATIONS.md", "docs/LIMITATIONS.md"),
)


def asset_pairs() -> tuple[AssetPair, ...]:
    directory_pairs = tuple(
        AssetPair(ROOT / directory, PACKAGE_ROOT / directory) for directory in DIRECTORIES
    )
    file_pairs = tuple(
        AssetPair(ROOT / source, PACKAGE_ROOT / destination) for source, destination in FILES
    )
    return directory_pairs + file_pairs


def _destination(package_root: Path, pair: AssetPair) -> Path:
    return package_root / pair.destination.relative_to(PACKAGE_ROOT)


def expected_files(package_root: Path = PACKAGE_ROOT) -> set[Path]:
    expected: set[Path] = set()
    for pair in asset_pairs():
        if pair.source.is_dir():
            expected.update(
                package_root / source_path.relative_to(ROOT)
                for source_path in pair.source.rglob("*")
                if source_path.is_file()
            )
        else:
            expected.add(_destination(package_root, pair))
    return expected


def package_files(package_root: Path = PACKAGE_ROOT) -> set[Path]:
    files: set[Path] = set()
    for pair in asset_pairs():
        destination = _destination(package_root, pair)
        if destination.is_dir():
            files.update(path for path in destination.rglob("*") if path.is_file())
        elif destination.is_file():
            files.add(destination)
    return files


def drift(package_root: Path = PACKAGE_ROOT) -> list[str]:
    differences: list[str] = []
    expected = expected_files(package_root)
    actual = package_files(package_root)
    for pair in asset_pairs():
        destination_root = _destination(package_root, pair)
        if pair.source.is_dir():
            source_files = [path for path in pair.source.rglob("*") if path.is_file()]
            for source_path in source_files:
                destination = package_root / source_path.relative_to(ROOT)
                if not destination.exists():
                    differences.append(f"missing: {destination.relative_to(package_root)}")
                elif source_path.read_bytes() != destination.read_bytes():
                    differences.append(f"different: {source_path.relative_to(ROOT)}")
        elif not destination_root.exists():
            differences.append(f"missing: {destination_root.relative_to(package_root)}")
        elif pair.source.read_bytes() != destination_root.read_bytes():
            differences.append(f"different: {pair.source.relative_to(ROOT)}")
    for extra in sorted(actual - expected):
        differences.append(f"extra: {extra.relative_to(package_root)}")
    return differences


def sync() -> None:
    PACKAGE_ROOT.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{PACKAGE_ROOT.name}.sync-", dir=PACKAGE_ROOT.parent))
    previous = _temporary_sibling(f".{PACKAGE_ROOT.name}.previous-")
    try:
        shutil.copytree(PACKAGE_ROOT, stage, dirs_exist_ok=True)
        for pair in asset_pairs():
            destination = _destination(stage, pair)
            if pair.source.is_dir():
                _remove_path(destination)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(pair.source, destination)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(pair.source, destination)
        differences = drift(stage)
        if differences:
            raise ValueError("staged package assets failed verification: " + "; ".join(differences))
        os.replace(PACKAGE_ROOT, previous)
        try:
            os.replace(stage, PACKAGE_ROOT)
        except BaseException:
            if not PACKAGE_ROOT.exists():
                os.replace(previous, PACKAGE_ROOT)
            raise
        _remove_path(previous)
    finally:
        _remove_path(stage)


def _temporary_sibling(prefix: str) -> Path:
    file_descriptor, name = tempfile.mkstemp(prefix=prefix, dir=PACKAGE_ROOT.parent)
    os.close(file_descriptor)
    path = Path(name)
    path.unlink()
    return path


def _remove_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="fail when package assets drift")
    mode.add_argument("--sync", action="store_true", help="copy canonical assets into the package")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.sync:
        sync()
    differences = drift()
    if differences:
        for difference in differences:
            print(difference)
        return 1
    print("Package assets are in sync.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
