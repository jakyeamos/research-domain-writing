#!/usr/bin/env python3
"""Synchronize canonical repository content into packaged assets."""

from __future__ import annotations

import argparse
import shutil
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


def _destination(pair: AssetPair, package_root: Path) -> Path:
    return package_root / pair.destination.relative_to(PACKAGE_ROOT)


def _files(path: Path) -> set[Path]:
    if path.is_file():
        return {path}
    if not path.is_dir():
        return set()
    return {candidate for candidate in path.rglob("*") if candidate.is_file()}


def expected_files(package_root: Path = PACKAGE_ROOT) -> set[Path]:
    expected: set[Path] = set()
    for pair in asset_pairs():
        if pair.source.is_dir():
            expected.update(
                package_root / source_path.relative_to(ROOT) for source_path in _files(pair.source)
            )
        else:
            expected.add(_destination(pair, package_root))
    return expected


def package_files(package_root: Path = PACKAGE_ROOT) -> set[Path]:
    files: set[Path] = set()
    for pair in asset_pairs():
        files.update(_files(_destination(pair, package_root)))
    return files


def drift(package_root: Path = PACKAGE_ROOT) -> list[str]:
    differences: list[str] = []
    expected = expected_files(package_root)
    actual = package_files(package_root)
    for pair in asset_pairs():
        destination = _destination(pair, package_root)
        if pair.source.is_dir():
            for source_path in _files(pair.source):
                package_path = package_root / source_path.relative_to(ROOT)
                if not package_path.exists():
                    differences.append(f"missing: {package_path.relative_to(package_root)}")
                elif source_path.read_bytes() != package_path.read_bytes():
                    differences.append(f"different: {source_path.relative_to(ROOT)}")
        elif not destination.exists():
            differences.append(f"missing: {destination.relative_to(package_root)}")
        elif pair.source.read_bytes() != destination.read_bytes():
            differences.append(f"different: {pair.source.relative_to(ROOT)}")
    for extra in sorted(actual - expected):
        differences.append(f"extra: {extra.relative_to(package_root)}")
    return differences


def sync() -> None:
    for pair in asset_pairs():
        destination = _destination(pair, PACKAGE_ROOT)
        if pair.source.is_dir():
            if destination.exists():
                shutil.rmtree(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(pair.source, destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pair.source, destination)


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
