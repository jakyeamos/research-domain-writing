#!/usr/bin/env python3
"""Verify the public rdw install command for every supported consumer surface."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

TARGETS = ("claude", "cursor", "agents")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rdw", type=Path, help="rdw executable; defaults to PATH")
    return parser


def _require_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        raise AssertionError(f"missing install output: {path}")


def _require_link_or_copy(path: Path, root: Path) -> None:
    _require_path(path)
    if path.is_symlink() and path.resolve() != root.resolve():
        raise AssertionError(f"unexpected link target for {path}: {path.resolve()}")
    if not path.is_symlink() and not (path / "SKILL.md").is_file():
        raise AssertionError(f"skill surface is neither a link nor a copied skill: {path}")


def _verify_target(rdw: Path, target: str, repo_root: Path) -> None:
    with tempfile.TemporaryDirectory(prefix=f"rdw-install-{target}-") as directory:
        home = Path(directory)
        subprocess.run(
            [str(rdw), "install", "--target", target, "--home", str(home)],
            cwd=repo_root,
            check=True,
        )

        root = home / ".config" / "research-domain-writing" / "skill"
        _require_path(root / ".rdw-managed.json")
        _require_path(root / "SKILL.md")
        env_file = home / ".config" / "research-domain-writing" / "env"
        _require_path(env_file)
        if env_file.read_text(encoding="utf-8") != f"RDW_ROOT={root}\n":
            raise AssertionError(f"unexpected RDW_ROOT marker in {env_file}")

        if target == "claude":
            _require_path(home / ".claude" / "commands" / "rdw.md")
            _require_path(home / ".claude" / "commands" / "rdw-batch.md")
            _require_link_or_copy(home / ".claude" / "skills" / "research-domain-writing", root)
        elif target == "cursor":
            _require_path(home / ".cursor" / "skills" / "rdw" / "SKILL.md")
            _require_path(home / ".cursor" / "skills" / "rdw-batch" / "SKILL.md")
        else:
            _require_link_or_copy(home / ".agents" / "skills" / "research-domain-writing", root)


def main() -> int:
    args = _parser().parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    rdw = args.rdw or shutil.which("rdw")
    if rdw is None:
        raise SystemExit("rdw executable not found; run this smoke with `uv run`")
    for target in TARGETS:
        _verify_target(Path(rdw), target, repo_root)
        print(f"install smoke passed: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
