from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rdw import __version__
from rdw.adapters import get_adapter, list_adapters
from rdw.batch_execution import execute_batch, request_batch_cancel, request_batch_pause
from rdw.domain import create_domain
from rdw.execution import execute_fixture
from rdw.install import INSTALL_TARGETS, install
from rdw.io import atomic_write_text
from rdw.lifecycle import (
    format_batch_resume,
    mark_task_status,
    show_batch_status,
    show_task_status,
)
from rdw.planner import TaskRequest, plan_batch, plan_task
from rdw.resources import asset_path
from rdw.schema_export import export_schema
from rdw.validation import ValidationResult, validate_batch_file, validate_packet_file


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except OSError as exc:
        if bool(getattr(args, "json_output", False)):
            _emit_json({"ok": False, "category": "environment", "error": str(exc)})
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        if bool(getattr(args, "json_output", False)):
            _emit_json({"ok": False, "category": "validation", "error": str(exc)})
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        if bool(getattr(args, "json_output", False)):
            _emit_json({"ok": False, "category": "internal", "error": str(exc)})
        else:
            print(f"ERROR: internal failure: {exc}", file=sys.stderr)
        return 3


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rdw", description="Research Domain Writing harness")
    parser.add_argument("--version", action="version", version=f"rdw {__version__}")
    subcommands = parser.add_subparsers(dest="command", required=True)

    doctor = subcommands.add_parser("doctor", help="Check RDW installation health")
    doctor.add_argument("--json", dest="json_output", action="store_true")
    doctor.set_defaults(func=_doctor)

    status = subcommands.add_parser("status", help="Show status for a planned task run")
    status.add_argument("run_dir", type=Path)
    status.add_argument("--json", dest="json_output", action="store_true")
    status.set_defaults(func=_status)

    schema = subcommands.add_parser("schema", help="Export public JSON Schemas")
    schema.add_argument("target", choices=["packet", "batch", "task-contract"])
    schema.add_argument("--format", default="jsonschema", choices=["jsonschema"])
    schema.add_argument("-o", "--output", type=Path)
    schema.set_defaults(func=_schema)

    adapter = subcommands.add_parser("adapter", help="Optional provider-neutral runtime adapters")
    adapter_subcommands = adapter.add_subparsers(dest="adapter_command", required=True)
    adapter_list = adapter_subcommands.add_parser("list", help="List available adapters")
    adapter_list.set_defaults(func=_adapter_list)
    adapter_run = adapter_subcommands.add_parser("run", help="Run an adapter against a task run")
    adapter_run.add_argument("name")
    adapter_run.add_argument("run_dir", type=Path)
    adapter_run.add_argument("--dry-run", action="store_true")
    adapter_run.set_defaults(func=_adapter_run)

    validate_packet = subcommands.add_parser("validate-packet", help="Validate a research packet")
    validate_packet.add_argument("path", type=Path)
    validate_packet.add_argument("--strict", action="store_true")
    validate_packet.add_argument("--root", type=Path, default=Path.cwd())
    validate_packet.add_argument("--allow-disabled-domain", action="store_true")
    validate_packet.add_argument("--json", dest="json_output", action="store_true")
    validate_packet.set_defaults(func=_validate_packet)

    validate_batch = subcommands.add_parser("validate-batch", help="Validate a batch task file")
    validate_batch.add_argument("path", type=Path)
    validate_batch.add_argument("--root", type=Path, default=Path.cwd())
    validate_batch.add_argument("--json", dest="json_output", action="store_true")
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
    task_plan.add_argument("--output-format")
    task_plan.add_argument("--out", type=Path, default=None)
    task_plan.add_argument("--root", type=Path, default=Path.cwd())
    task_plan.add_argument("--force", action="store_true")
    task_plan.add_argument("--no-overwrite", action="store_true")
    task_plan.add_argument("--run-id")
    task_plan.add_argument("--json", dest="json_output", action="store_true")
    task_plan.set_defaults(func=_task_plan)

    task_mark = task_subcommands.add_parser("mark", help="Update task lifecycle status")
    task_mark.add_argument("status")
    task_mark.add_argument("run_dir", type=Path)
    task_mark.add_argument("--reason")
    task_mark.add_argument("--json", dest="json_output", action="store_true")
    task_mark.set_defaults(func=_task_mark)

    task_execute = task_subcommands.add_parser(
        "execute", help="Execute a deterministic fixture through the task lifecycle"
    )
    task_execute.add_argument("run_dir", type=Path)
    task_execute.add_argument("--fixture", required=True, type=Path)
    task_execute.add_argument("--root", type=Path, default=Path.cwd())
    task_execute.add_argument("--resume", action="store_true")
    task_execute.add_argument("--dry-run", action="store_true")
    task_execute.add_argument("--json", dest="json_output", action="store_true")
    task_execute.set_defaults(func=_task_execute)

    batch = subcommands.add_parser("batch", help="Batch planning and execution commands")
    batch_subcommands = batch.add_subparsers(dest="batch_command", required=True)
    batch_plan = batch_subcommands.add_parser("plan", help="Plan a batch file")
    batch_plan.add_argument("path", type=Path)
    batch_plan.add_argument("--out", type=Path, default=None)
    batch_plan.add_argument("--root", type=Path, default=Path.cwd())
    batch_plan.add_argument("--json", dest="json_output", action="store_true")
    batch_plan.set_defaults(func=_batch_plan)

    batch_status = batch_subcommands.add_parser("status", help="Show batch run status")
    batch_status.add_argument("batch_dir", type=Path)
    batch_status.add_argument("--json", dest="json_output", action="store_true")
    batch_status.set_defaults(func=_batch_status)

    batch_resume = batch_subcommands.add_parser("resume", help="List next batch tasks to run")
    batch_resume.add_argument("batch_dir", type=Path)
    batch_resume.add_argument("--json", dest="json_output", action="store_true")
    batch_resume.set_defaults(func=_batch_resume)

    batch_execute = batch_subcommands.add_parser(
        "execute", help="Execute a serial filesystem-first fixture batch"
    )
    batch_execute.add_argument("batch_dir", type=Path)
    batch_execute.add_argument("--fixture-map", required=True, type=Path)
    batch_execute.add_argument("--root", type=Path, default=Path.cwd())
    batch_execute.add_argument("--resume", action="store_true")
    batch_execute.add_argument("--reclaim-lease", action="store_true")
    batch_execute.add_argument("--dry-run", action="store_true")
    batch_execute.add_argument("--json", dest="json_output", action="store_true")
    batch_execute.set_defaults(func=_batch_execute)

    batch_pause = batch_subcommands.add_parser("pause", help="Request cooperative batch pause")
    batch_pause.add_argument("batch_dir", type=Path)
    batch_pause.add_argument("--json", dest="json_output", action="store_true")
    batch_pause.set_defaults(func=_batch_pause)

    batch_cancel = batch_subcommands.add_parser("cancel", help="Request cooperative batch cancel")
    batch_cancel.add_argument("batch_dir", type=Path)
    batch_cancel.add_argument("--json", dest="json_output", action="store_true")
    batch_cancel.set_defaults(func=_batch_cancel)

    install_parser = subcommands.add_parser("install", help="Install slash commands and skills")
    install_parser.add_argument("--target", choices=sorted(INSTALL_TARGETS), default="all")
    install_parser.add_argument("--project-root", type=Path)
    install_parser.add_argument("--source-root", type=Path)
    install_parser.add_argument("--home", type=Path, default=Path.home())
    install_parser.add_argument("--dry-run", action="store_true")
    install_parser.add_argument("--backup", action="store_true")
    install_parser.add_argument("--force", action="store_true")
    install_parser.set_defaults(func=_install)
    return parser


def _doctor(args: argparse.Namespace) -> int:
    required = [
        ("SKILL.md", asset_path("SKILL.md")),
        ("pipeline orchestrator", asset_path("prompts", "pipeline-orchestrator.md")),
        ("domain registry", asset_path("config", "domains.yaml")),
        ("install templates", asset_path("install", "claude-commands", "rdw.md")),
    ]
    failed = False
    checks: dict[str, bool] = {}
    for label, path in required:
        exists = path.is_file()
        checks[label] = exists
        failed = failed or not exists
    output_root = Path.cwd() / "outputs"
    writable = _writable(output_root)
    if args.json_output:
        _emit_json(
            {
                "ok": not failed,
                "version": __version__,
                "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "checks": checks,
                "writable_outputs": writable,
            }
        )
    else:
        print(f"rdw {__version__}")
        print(f"python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        for label, exists in checks.items():
            print(f"{'OK' if exists else 'MISSING'} {label}")
        print(f"{'OK' if writable else 'WARN'} writable outputs: {output_root}")
    return 1 if failed else 0


def _status(args: argparse.Namespace) -> int:
    if args.json_output:
        from rdw.lifecycle import load_task_status_view

        _emit_json(load_task_status_view(args.run_dir).as_dict())
    else:
        print(show_task_status(args.run_dir))
    return 0


def _schema(args: argparse.Namespace) -> int:
    payload = export_schema(args.target, format=args.format)
    if args.output:
        atomic_write_text(args.output, payload)
        print(f"Wrote {args.output}")
    else:
        print(payload, end="")
    return 0


def _adapter_list(_args: argparse.Namespace) -> int:
    for name in list_adapters():
        print(name)
    return 0


def _adapter_run(args: argparse.Namespace) -> int:
    adapter = get_adapter(args.name)
    result = adapter.run(args.run_dir, dry_run=bool(args.dry_run))
    print(result.message)
    if result.artifact_path:
        print(f"Wrote {result.artifact_path}")
    return 0


def _validate_packet(args: argparse.Namespace) -> int:
    result = validate_packet_file(
        args.path,
        strict=bool(args.strict),
        root=args.root,
        allow_disabled=bool(args.allow_disabled_domain),
    )
    return _print_validation(result, f"OK: {args.path}", json_output=bool(args.json_output))


def _validate_batch(args: argparse.Namespace) -> int:
    result = validate_batch_file(args.path, root=args.root)
    return _print_validation(result, f"OK: {args.path}", json_output=bool(args.json_output))


def _new_domain(args: argparse.Namespace) -> int:
    destination = create_domain(args.domain_id, args.display_name, root=args.root)
    print(f"Created {destination}")
    print("Next: register it in config/domains.yaml when ready to enable it.")
    return 0


def _task_plan(args: argparse.Namespace) -> int:
    if args.force and args.no_overwrite:
        raise ValueError("--force and --no-overwrite are mutually exclusive")
    task_request = TaskRequest(
        request=args.request,
        domain=args.domain,
        entity=args.entity,
        output_type=args.output_type,
        audience=args.audience,
        depth=args.depth,
        packet_id=args.packet_id,
        task_id=args.task_id,
        output_format=args.output_format,
    )
    output_dir = args.out or (Path.cwd() / "outputs" / "runs" / "task-plan")
    planned = plan_task(
        task_request,
        output_dir,
        root=args.root,
        no_overwrite=bool(args.no_overwrite),
        run_id=args.run_id,
    )
    if args.json_output:
        _emit_json(
            {
                "ok": True,
                "task_id": planned.task_id,
                "output_dir": str(planned.output_dir),
                "contract": planned.contract,
            }
        )
    else:
        print(f"Planned {planned.task_id}")
        print(f"Prompt bundle: {planned.output_dir / 'prompt-bundle.md'}")
    return 0


def _task_mark(args: argparse.Namespace) -> int:
    view = mark_task_status(args.run_dir, args.status, reason=args.reason)
    if args.json_output:
        _emit_json(view.as_dict())
    else:
        print(f"Marked {view.task_id} -> {view.status}")
        if view.reason:
            print(f"reason: {view.reason}")
    return 0


def _task_execute(args: argparse.Namespace) -> int:
    result = execute_fixture(
        args.run_dir,
        args.fixture,
        root=args.root,
        resume=bool(args.resume),
        dry_run=bool(args.dry_run),
    )
    if args.json_output:
        _emit_json(result.as_dict())
    else:
        print(f"Executed {result.task_id}: {result.adapter_status} -> {result.workflow_status}")
        if result.receipt_path:
            print(f"Receipt: {result.receipt_path}")
        for path in result.promoted_paths:
            print(f"Promoted: {path}")
    return 0


def _batch_plan(args: argparse.Namespace) -> int:
    output_dir = args.out or (Path.cwd() / "outputs" / "batches" / args.path.stem)
    summary = plan_batch(args.path, output_dir, root=args.root)
    if args.json_output:
        _emit_json({"ok": True, "batch_dir": str(output_dir), "summary": summary})
    else:
        print(f"Planned batch: {output_dir}")
        print(f"Summary: {output_dir / 'summary.yaml'}")
    return 0


def _batch_status(args: argparse.Namespace) -> int:
    if args.json_output:
        from rdw.lifecycle import load_batch_status_view

        _emit_json(load_batch_status_view(args.batch_dir).as_dict())
    else:
        print(show_batch_status(args.batch_dir))
    return 0


def _batch_resume(args: argparse.Namespace) -> int:
    if args.json_output:
        from rdw.lifecycle import batch_resume

        _emit_json({"tasks": batch_resume(args.batch_dir)})
    else:
        print(format_batch_resume(args.batch_dir))
    return 0


def _batch_execute(args: argparse.Namespace) -> int:
    result = execute_batch(
        args.batch_dir,
        args.fixture_map,
        root=args.root,
        resume=bool(args.resume),
        reclaim_lease=bool(args.reclaim_lease),
        dry_run=bool(args.dry_run),
    )
    if args.json_output:
        _emit_json({"ok": True, **result.as_dict()})
    else:
        print(f"Batch {result.batch_id}: {result.state}")
        print(
            f"completed={result.completed} needs_review={result.needs_review} "
            f"failed={result.failed} cancelled={result.cancelled} "
            f"attempts={result.total_attempts}"
        )
    return 0


def _batch_pause(args: argparse.Namespace) -> int:
    result = request_batch_pause(args.batch_dir)
    if args.json_output:
        _emit_json({"ok": True, **result.as_dict()})
    else:
        print(f"Batch {result.batch_id}: {result.state}")
    return 0


def _batch_cancel(args: argparse.Namespace) -> int:
    result = request_batch_cancel(args.batch_dir)
    if args.json_output:
        _emit_json({"ok": True, **result.as_dict()})
    else:
        print(f"Batch {result.batch_id}: {result.state}")
    return 0


def _install(args: argparse.Namespace) -> int:
    result = install(
        target=args.target,
        home=args.home,
        project_root=args.project_root,
        source_root=args.source_root,
        dry_run=bool(args.dry_run),
        backup=bool(args.backup),
        force=bool(args.force),
    )
    prefix = "[dry-run] would write" if args.dry_run else "Wrote"
    print(f"RDW_ROOT={result.root}")
    for path in result.written:
        print(f"{prefix} {path}")
    return 0


def _print_validation(result: ValidationResult, success: str, *, json_output: bool) -> int:
    if json_output:
        _emit_json(result.as_dict())
        return 0 if result.ok else 1
    errors = result.errors
    warnings = result.warnings
    for warning in warnings:
        print(f"WARN: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(success)
    return 0


def _emit_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


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
