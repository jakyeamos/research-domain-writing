from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from rdw.io import atomic_write_text
from rdw.resources import copy_package_assets, read_asset_text

INSTALL_TARGETS = {"claude", "cursor", "agents", "all"}


@dataclass(frozen=True)
class InstallResult:
    root: Path
    written: list[Path]


@dataclass(frozen=True)
class _Options:
    dry_run: bool = False
    backup: bool = False
    force: bool = False


def install(
    *,
    target: str,
    home: Path,
    project_root: Path | None = None,
    source_root: Path | None = None,
    dry_run: bool = False,
    backup: bool = False,
    force: bool = False,
) -> InstallResult:
    if target not in INSTALL_TARGETS:
        raise ValueError(f"unknown target: {target}")
    opts = _Options(dry_run=dry_run, backup=backup, force=force)
    install_root = _resolve_install_root(home, source_root, opts)
    written: list[Path] = []
    targets = {"claude", "cursor", "agents"} if target == "all" else {target}
    if "claude" in targets:
        written.extend(_install_claude(home, install_root, opts))
    if "cursor" in targets:
        written.extend(_install_cursor(home, install_root, project_root, opts))
    if "agents" in targets:
        written.extend(_install_agents(home, install_root, opts))
    env_file = home / ".config" / "research-domain-writing" / "env"
    if not opts.dry_run:
        env_file.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(env_file, f"RDW_ROOT={install_root}\n")
    written.append(env_file)
    return InstallResult(root=install_root, written=written)


def _resolve_install_root(home: Path, source_root: Path | None, opts: _Options) -> Path:
    if source_root:
        return source_root.resolve()
    destination = home / ".config" / "research-domain-writing" / "skill"
    if not opts.dry_run:
        copy_package_assets(destination, backup=opts.backup, force=opts.force)
    return destination


def _render_template(template: str, root: Path) -> str:
    return template.replace("__RDW_ROOT__", str(root))


def _install_claude(home: Path, root: Path, opts: _Options) -> list[Path]:
    command_dir = home / ".claude" / "commands"
    skill_link = home / ".claude" / "skills" / "research-domain-writing"
    rdw = command_dir / "rdw.md"
    batch = command_dir / "rdw-batch.md"
    if not opts.dry_run:
        command_dir.mkdir(parents=True, exist_ok=True)
        skill_link.parent.mkdir(parents=True, exist_ok=True)
        _write_managed_file(
            rdw,
            _render_template(read_asset_text("install", "claude-commands", "rdw.md"), root),
            opts,
        )
        _write_managed_file(
            batch,
            _render_template(read_asset_text("install", "claude-commands", "rdw-batch.md"), root),
            opts,
        )
    _replace_symlink(skill_link, root, opts)
    return [rdw, batch, skill_link]


def _install_cursor(
    home: Path, root: Path, project_root: Path | None, opts: _Options
) -> list[Path]:
    written = _write_cursor_skills(home / ".cursor" / "skills", root, opts)
    if project_root:
        written.extend(_write_cursor_skills(project_root / ".cursor" / "skills", root, opts))
    return written


def _write_cursor_skills(base: Path, root: Path, opts: _Options) -> list[Path]:
    rdw_dir = base / "rdw"
    batch_dir = base / "rdw-batch"
    rdw = rdw_dir / "SKILL.md"
    batch = batch_dir / "SKILL.md"
    if not opts.dry_run:
        rdw_dir.mkdir(parents=True, exist_ok=True)
        batch_dir.mkdir(parents=True, exist_ok=True)
        _write_managed_file(
            rdw,
            _render_template(read_asset_text("install", "cursor-skills", "rdw", "SKILL.md"), root),
            opts,
        )
        _write_managed_file(
            batch,
            _render_template(
                read_asset_text("install", "cursor-skills", "rdw-batch", "SKILL.md"), root
            ),
            opts,
        )
    return [rdw, batch]


def _install_agents(home: Path, root: Path, opts: _Options) -> list[Path]:
    link = home / ".agents" / "skills" / "research-domain-writing"
    if not opts.dry_run:
        link.parent.mkdir(parents=True, exist_ok=True)
    _replace_symlink(link, root, opts)
    return [link]


def _replace_symlink(link: Path, target: Path, opts: _Options) -> None:
    if opts.dry_run:
        return
    if link.exists() or link.is_symlink():
        if link.is_dir() and not link.is_symlink():
            if opts.backup:
                shutil.move(str(link), str(_backup_path(link)))
            elif opts.force:
                shutil.rmtree(link)
            else:
                raise ValueError(f"real directory in the way: {link} (use --force or --backup)")
        else:
            link.unlink()
    _create_link(link, target)


def _write_managed_file(path: Path, content: str, opts: _Options) -> None:
    if path.exists() or path.is_symlink():
        if path.is_dir() and not path.is_symlink():
            if opts.backup:
                shutil.move(str(path), str(_backup_path(path)))
            elif opts.force:
                shutil.rmtree(path)
            else:
                raise ValueError(f"real directory in the way: {path} (use --force or --backup)")
        elif path.is_file() and path.read_text(encoding="utf-8") == content:
            return
        elif opts.backup:
            shutil.move(str(path), str(_backup_path(path)))
        elif not opts.force:
            raise ValueError(f"managed file in the way: {path} (use --force or --backup)")
    atomic_write_text(path, content)


def _create_link(link: Path, target: Path) -> None:
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        shutil.copytree(target, link)


def _backup_path(link: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return link.with_name(f"{link.name}.bak-{stamp}")
