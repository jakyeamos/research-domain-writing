#!/usr/bin/env python3
"""Synchronize the canonical repository content into packaged assets."""

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


def expected_files() -> set[Path]:
    expected: set[Path] = set()
    for pair in asset_pairs():
        if pair.source.is_dir():
            expected.update(
                PACKAGE_ROOT / source_path.relative_to(ROOT)
                for source_path in pair.source.rglob("*")
                if source_path.is_file()
            )
        else:
            expected.add(pair.destination)
    return expected


def package_files() -> set[Path]:
    files: set[Path] = set()
    for pair in asset_pairs():
        if pair.destination.is_dir():
            files.update(path for path in pair.destination.rglob("*") if path.is_file())
        elif pair.destination.is_file():
            files.add(pair.destination)
    return files


def drift() -> list[str]:
    differences: list[str] = []
    expected = expected_files()
    actual = package_files()
    for pair in asset_pairs():
        if pair.source.is_dir():
            source_files = [path for path in pair.source.rglob("*") if path.is_file()]
            for source_path in source_files:
                destination = PACKAGE_ROOT / source_path.relative_to(ROOT)
                if not destination.exists():
                    differences.append(f"missing: {destination.relative_to(ROOT)}")
                elif source_path.read_bytes() != destination.read_bytes():
                    differences.append(f"different: {source_path.relative_to(ROOT)}")
        elif not pair.destination.exists():
            differences.append(f"missing: {pair.destination.relative_to(ROOT)}")
        elif pair.source.read_bytes() != pair.destination.read_bytes():
            differences.append(f"different: {pair.source.relative_to(ROOT)}")
    for extra in sorted(actual - expected):
        differences.append(f"extra: {extra.relative_to(ROOT)}")
    return differences


def sync() -> None:
    for pair in asset_pairs():
        if pair.source.is_dir():
            if pair.destination.exists():
                shutil.rmtree(pair.destination)
            pair.destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(pair.source, pair.destination)
        else:
            pair.destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pair.source, pair.destination)


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
