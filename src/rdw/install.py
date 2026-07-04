from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from rdw.resources import copy_package_assets, read_asset_text

INSTALL_TARGETS = {"claude", "cursor", "agents", "all"}


@dataclass(frozen=True)
class InstallResult:
    root: Path
    written: list[Path]


def install(
    *,
    target: str,
    home: Path,
    project_root: Path | None = None,
    source_root: Path | None = None,
) -> InstallResult:
    if target not in INSTALL_TARGETS:
        raise ValueError(f"unknown target: {target}")
    install_root = _resolve_install_root(home, source_root)
    written: list[Path] = []
    targets = {"claude", "cursor", "agents"} if target == "all" else {target}
    if "claude" in targets:
        written.extend(_install_claude(home, install_root))
    if "cursor" in targets:
        written.extend(_install_cursor(home, install_root, project_root))
    if "agents" in targets:
        written.extend(_install_agents(home, install_root))
    env_file = home / ".config" / "research-domain-writing" / "env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text(f"RDW_ROOT={install_root}\n", encoding="utf-8")
    written.append(env_file)
    return InstallResult(root=install_root, written=written)


def _resolve_install_root(home: Path, source_root: Path | None) -> Path:
    if source_root:
        return source_root.resolve()
    destination = home / ".config" / "research-domain-writing" / "skill"
    copy_package_assets(destination)
    return destination


def _render_template(template: str, root: Path) -> str:
    return template.replace("__RDW_ROOT__", str(root))


def _install_claude(home: Path, root: Path) -> list[Path]:
    command_dir = home / ".claude" / "commands"
    skill_link = home / ".claude" / "skills" / "research-domain-writing"
    command_dir.mkdir(parents=True, exist_ok=True)
    skill_link.parent.mkdir(parents=True, exist_ok=True)
    rdw = command_dir / "rdw.md"
    batch = command_dir / "rdw-batch.md"
    rdw.write_text(
        _render_template(read_asset_text("install", "claude-commands", "rdw.md"), root),
        encoding="utf-8",
    )
    batch.write_text(
        _render_template(read_asset_text("install", "claude-commands", "rdw-batch.md"), root),
        encoding="utf-8",
    )
    _replace_symlink(skill_link, root)
    return [rdw, batch, skill_link]


def _install_cursor(home: Path, root: Path, project_root: Path | None) -> list[Path]:
    written = _write_cursor_skills(home / ".cursor" / "skills", root)
    if project_root:
        written.extend(_write_cursor_skills(project_root / ".cursor" / "skills", root))
    return written


def _write_cursor_skills(base: Path, root: Path) -> list[Path]:
    rdw_dir = base / "rdw"
    batch_dir = base / "rdw-batch"
    rdw_dir.mkdir(parents=True, exist_ok=True)
    batch_dir.mkdir(parents=True, exist_ok=True)
    rdw = rdw_dir / "SKILL.md"
    batch = batch_dir / "SKILL.md"
    rdw.write_text(
        _render_template(read_asset_text("install", "cursor-skills", "rdw", "SKILL.md"), root),
        encoding="utf-8",
    )
    batch.write_text(
        _render_template(
            read_asset_text("install", "cursor-skills", "rdw-batch", "SKILL.md"), root
        ),
        encoding="utf-8",
    )
    return [rdw, batch]


def _install_agents(home: Path, root: Path) -> list[Path]:
    link = home / ".agents" / "skills" / "research-domain-writing"
    link.parent.mkdir(parents=True, exist_ok=True)
    _replace_symlink(link, root)
    return [link]


def _replace_symlink(link: Path, target: Path) -> None:
    if link.exists() or link.is_symlink():
        if link.is_dir() and not link.is_symlink():
            shutil.rmtree(link)
        else:
            link.unlink()
    os.symlink(target, link, target_is_directory=True)
