from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rdw import __version__
from rdw.domain import create_domain
from rdw.install import INSTALL_TARGETS, install
from rdw.planner import TaskRequest, plan_batch, plan_task
from rdw.resources import asset_path
from rdw.validation import validate_batch_file, validate_packet_file


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rdw", description="Research Domain Writing harness")
    parser.add_argument("--version", action="version", version=f"rdw {__version__}")
    subcommands = parser.add_subparsers(dest="command", required=True)

    doctor = subcommands.add_parser("doctor", help="Check RDW installation health")
    doctor.set_defaults(func=_doctor)

    validate_packet = subcommands.add_parser("validate-packet", help="Validate a research packet")
    validate_packet.add_argument("path", type=Path)
    validate_packet.add_argument("--strict", action="store_true")
    validate_packet.add_argument("--root", type=Path, default=Path.cwd())
    validate_packet.add_argument("--allow-disabled-domain", action="store_true")
    validate_packet.set_defaults(func=_validate_packet)

    validate_batch = subcommands.add_parser("validate-batch", help="Validate a batch task file")
    validate_batch.add_argument("path", type=Path)
    validate_batch.add_argument("--root", type=Path, default=Path.cwd())
    validate_batch.set_defaults(func=_validate_batch)

    new_domain = subcommands.add_parser("new-domain", help="Scaffold a new domain pack")
    new_domain.add_argument("domain_id")
    new_domain.add_argument("display_name")
    new_domain.add_argument("--root", type=Path, default=Path.cwd())
    new_domain.set_defaults(func=_new_domain)

    task = subcommands.add_parser("task", help="Single-task planning commands")
    task_subcommands = task.add_subparsers(dest="task_command", required=True)
    task_plan = task_subcommands.add_parser("plan", help="Plan one RDW task")
    task_plan.add_argument("--request", required=True)
    task_plan.add_argument("--domain")
    task_plan.add_argument("--entity")
    task_plan.add_argument("--output-type")
    task_plan.add_argument("--audience")
    task_plan.add_argument("--depth")
    task_plan.add_argument("--packet-id")
    task_plan.add_argument("--task-id")
    task_plan.add_argument("--out", type=Path, default=None)
    task_plan.add_argument("--root", type=Path, default=Path.cwd())
    task_plan.set_defaults(func=_task_plan)

    batch = subcommands.add_parser("batch", help="Batch planning commands")
    batch_subcommands = batch.add_subparsers(dest="batch_command", required=True)
    batch_plan = batch_subcommands.add_parser("plan", help="Plan a batch file")
    batch_plan.add_argument("path", type=Path)
    batch_plan.add_argument("--out", type=Path, default=None)
    batch_plan.add_argument("--root", type=Path, default=Path.cwd())
    batch_plan.set_defaults(func=_batch_plan)

    install_parser = subcommands.add_parser("install", help="Install slash commands and skills")
    install_parser.add_argument("--target", choices=sorted(INSTALL_TARGETS), default="all")
    install_parser.add_argument("--project-root", type=Path)
    install_parser.add_argument("--source-root", type=Path)
    install_parser.add_argument("--home", type=Path, default=Path.home())
    install_parser.set_defaults(func=_install)
    return parser


def _doctor(_args: argparse.Namespace) -> int:
    required = [
        ("SKILL.md", asset_path("SKILL.md")),
        ("pipeline orchestrator", asset_path("prompts", "pipeline-orchestrator.md")),
        ("domain registry", asset_path("config", "domains.yaml")),
        ("install templates", asset_path("install", "claude-commands", "rdw.md")),
    ]
    failed = False
    print(f"rdw {__version__}")
    print(f"python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    for label, path in required:
        exists = path.is_file()
        print(f"{'OK' if exists else 'MISSING'} {label}")
        failed = failed or not exists
    output_root = Path.cwd() / "outputs"
    writable = _writable(output_root)
    print(f"{'OK' if writable else 'WARN'} writable outputs: {output_root}")
    return 1 if failed else 0


def _validate_packet(args: argparse.Namespace) -> int:
    result = validate_packet_file(
        args.path,
        strict=bool(args.strict),
        root=args.root,
        allow_disabled=bool(args.allow_disabled_domain),
    )
    return _print_validation(result.errors, result.warnings, f"OK: {args.path}")


def _validate_batch(args: argparse.Namespace) -> int:
    result = validate_batch_file(args.path, root=args.root)
    return _print_validation(result.errors, result.warnings, f"OK: {args.path}")


def _new_domain(args: argparse.Namespace) -> int:
    destination = create_domain(args.domain_id, args.display_name, root=args.root)
    print(f"Created {destination}")
    print("Next: register it in config/domains.yaml when ready to enable it.")
    return 0


def _task_plan(args: argparse.Namespace) -> int:
    task_request = TaskRequest(
        request=args.request,
        domain=args.domain,
        entity=args.entity,
        output_type=args.output_type,
        audience=args.audience,
        depth=args.depth,
        packet_id=args.packet_id,
        task_id=args.task_id,
    )
    output_dir = args.out or (Path.cwd() / "outputs" / "runs" / "task-plan")
    planned = plan_task(task_request, output_dir, root=args.root)
    print(f"Planned {planned.task_id}")
    print(f"Prompt bundle: {output_dir / 'prompt-bundle.md'}")
    return 0


def _batch_plan(args: argparse.Namespace) -> int:
    output_dir = args.out or (Path.cwd() / "outputs" / "batches" / args.path.stem)
    plan_batch(args.path, output_dir, root=args.root)
    print(f"Planned batch: {output_dir}")
    print(f"Summary: {output_dir / 'summary.yaml'}")
    return 0


def _install(args: argparse.Namespace) -> int:
    result = install(
        target=args.target,
        home=args.home,
        project_root=args.project_root,
        source_root=args.source_root,
    )
    print(f"RDW_ROOT={result.root}")
    for path in result.written:
        print(f"Wrote {path}")
    return 0


def _print_validation(errors: list[str], warnings: list[str], success: str) -> int:
    for warning in warnings:
        print(f"WARN: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(success)
    return 0


def _writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".rdw-write-test"
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
