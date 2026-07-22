---
name: research-domain-writing
description: Use for research-grounded writing workflows with the research-domain-writing Python package: install or diagnose `rdw`, validate packets/batches, plan single or batch runs, manage lifecycle artifacts, export schemas, or integrate the public helpers. Stay within the shipped deterministic CLI and provider-neutral boundaries; do not assume model APIs or autonomous research.
---

# Research Domain Writing

## Package metadata

- Package: `research-domain-writing` (`rdw`)
- Current source version: `0.2.0`; this skill applies to the `0.2.x` behavior documented here.
- Ecosystem: Python CLI/library; Python `>=3.12` (classified/tested for 3.12 and 3.13).
- Package manager: `uv` for this repository; PyPI installs may use `pip`.
- Runtime dependency: `pyyaml>=6.0.2`; dev tools are Ruff, basedpyright, and pytest.
- Source of truth consulted: `pyproject.toml`, `uv.lock`, `README.md`, `CHANGELOG.md`, `RELEASE.md`, `docs/LIMITATIONS.md`, `src/rdw/`, `src/rdw/assets/prompts/`, `config/`, `domains/`, `examples/`, and `tests/`.

## When to use this skill

Use it when an agent must operate or extend RDW, especially to:

- create or validate research packets and batch YAML;
- turn a writing request into a deterministic task or batch run;
- execute the agent-side research → knowledge → draft → QA → humanizer workflow;
- inspect or update run status, export JSON Schema, install skill/command templates, or use an adapter handoff.

RDW is primarily a deterministic research-grounded writing harness. The CLI plans, validates, records, and emits prompts; the agent performs research, drafting, QA, and final writing.

## Mental model and boundaries

1. Route/infer a task contract from the request, with explicit CLI/task fields taking precedence.
2. Research into a reusable YAML packet with source notes and confidence.
3. Build knowledge, write a domain draft, run domain QA, then humanize style.
4. Treat knowledge stages as fact-producing; the humanizer must not add facts.

The shipped CLI does not browse, call model APIs, run autonomous research, or write final copy. `openai` and `anthropic` adapters are provider-neutral stubs, not integrations. `config/research-sources.yaml` guides an agent; it is not a fetch configuration.

## Installation, setup, and imports

From PyPI:

```bash
python -m pip install research-domain-writing
rdw doctor
```

From this checkout, prefer the locked environment:

```bash
uv sync
uv run rdw doctor
```

Install integrations only when needed: `rdw install --target all` (targets: `claude`, `cursor`, `agents`, `all`). Use `--dry-run` first when touching a real home directory. The installer may create symlinks or copy trees; `--backup` preserves an existing real directory, while `--force` can remove it.

The CLI is the preferred public interface. For Python integration, use only source-backed public helpers such as:

```python
from pathlib import Path
from rdw.planner import TaskRequest, plan_task
from rdw.validation import validate_packet_file

request = TaskRequest(request="explain idempotency keys", domain="technical")
planned = plan_task(request, Path(".rdw-runs/idempotency"), root=Path.cwd())
result = validate_packet_file(Path("knowledge/technical/example.yaml"), strict=True, root=Path.cwd())
```

Use `rdw.__version__` for the installed version. Do not import underscored functions or rely on module internals merely because they are importable.

## Common workflows

Single task planning:

```bash
uv run rdw task plan --request "explain idempotency keys" --domain technical --out .rdw-runs/idempotency
```

It writes `task-contract.yaml`, `prompt-bundle.md`, and `status.json`. Give the prompt bundle to an agent, confirm inferred fields, then follow its ordered prompts and save artifacts according to `config/output-formats.yaml`.

Batch planning and execution:

```bash
uv run rdw validate-batch examples/batch-tasks.yaml
uv run rdw batch plan examples/batch-tasks.yaml --out .rdw-runs/demo-batch
uv run rdw batch status .rdw-runs/demo-batch
uv run rdw batch resume .rdw-runs/demo-batch
```

`batch plan` only expands deterministic per-task bundles and starts tasks at `planned`; it does not execute the writing pipeline. Do not parallelize agents that update the same packet ID without merge discipline.

Packet validation and schemas:

```bash
uv run rdw validate-packet knowledge/basketball/demo-guard-2026-demo.yaml --strict
uv run rdw schema packet --format jsonschema -o /tmp/packet.schema.json
uv run rdw schema batch --format jsonschema
uv run rdw schema task-contract --format jsonschema
```

Strict packets require non-empty required fields, registered/enabled domains, `high|medium|low` confidence, fact IDs, ISO-like dates, timezone-aware `last_updated`, valid source formats, and source-note `fact_ids` linkage. Disabled domains can only pass strict mode with `--allow-disabled-domain`.

Lifecycle and adapters:

```bash
uv run rdw status .rdw-runs/idempotency
uv run rdw task mark research-done .rdw-runs/idempotency
uv run rdw task mark qa-failed .rdw-runs/idempotency --reason "unsupported claim"
uv run rdw adapter list
uv run rdw adapter run local .rdw-runs/idempotency --dry-run
```

Use status names accepted by the lifecycle implementation (for example `planned`, `research-done`, `qa-failed`, and `final-done`) and preserve the generated history/log artifacts.

## Preferred APIs and idioms

- Prefer explicit task fields (`--domain`, `--entity`, `--output-type`, `--audience`, `--depth`, `--packet-id`, `--task-id`, `--output-format`) when router inference could be ambiguous.
- Depth aliases are `1=deep`, `2=standard`, `3=light`, `4=minimal`; use named values in new YAML for readability.
- Reuse packets by stable `id`/`packet_id`; refresh `last_updated` and retain source evidence.
- Add a domain through `rdw new-domain <id> <display-name>`, then edit the generated pack and register it in `config/domains.yaml`. Do not modify core prompts for a normal domain addition.
- Use `--no-overwrite` for guarded planning. `--force` and `--no-overwrite` are mutually exclusive.
- Use `root=` or `--root` when operating on a repository other than the current working directory.

## Error handling and safety

- Treat a nonzero CLI exit or `ValidationResult.errors` as a failed contract; warnings are not proof that a packet is safe to use.
- Never fabricate facts, citations, quotes, dates, metrics, or source access. Record only sources actually consulted.
- Keep research facts in `key_facts`/domain metrics and interpretation in `interpretation_notes`; link source notes to fact IDs.
- Never hard-code API keys or tokens. RDW core does not need them, and provider stubs do not make external calls.
- Avoid destructive filesystem operations. Inspect `rdw install --target ... --dry-run`; use `--backup` before replacing an existing integration directory and reserve `--force` for an intentional replacement.
- Do not treat synthetic examples, especially the basketball demo, as real-world evidence.

## Common mistakes to avoid

- Assuming `rdw task plan` or `rdw batch plan` performs research, model calls, drafting, QA, or humanization.
- Using the legacy wrapper scripts as a new integration surface; use the CLI, keeping wrappers only for compatibility.
- No deprecated Python API is listed for `0.2.0`; if a later changelog marks an API or import path deprecated, migrate to the replacement instead of preserving it in new code.
- Skipping strict packet validation, source-note linkage, domain registration, or the QA-before-humanizer order.
- Writing directly to generated run artifacts without preserving `status.json`, `summary.yaml`, or `batch-log.jsonl` semantics.
- Passing unsupported output formats or research depths; validate the batch before planning.
- Copying unreleased `docs/superpowers` designs into production code. The current package is `0.2.0`; source and release docs win when notes disagree.
- Depending on private `_...` functions, undocumented YAML keys, or a fictional API implied by the `openai`/`anthropic` stub names.
- RDW exposes synchronous file/CLI workflows only; do not invent async variants or mix them with an assumed async provider API.

## Testing and validation

Run the repository gates after code or prompt changes:

```bash
uv run ruff check .
uv run ruff format --check .
uv run basedpyright src tests scripts
uv run pytest -q
uv build
```

Useful smoke checks are `uv run rdw doctor`, strict validation of the shipped basketball packet, validation/planning of `examples/batch-tasks.yaml`, and a task plan written under `/tmp` or `.rdw-runs/`. For a built wheel, install it into a disposable virtualenv and run `rdw doctor` plus strict packet validation. Do not commit generated smoke outputs.

## Migration and release notes

The released changelog contains `0.2.0` and `0.1.0`. SemVer guidance says patch releases preserve task/output shapes, minor releases add domains/formats/templates/validation fields, and major releases may change prompt order, packet schema, install surface, or output contracts. There is no migration API; when schemas or statuses change, inspect generated JSON Schemas, changelog, tests, and release notes before editing packets or consumers.

When the package version changes, update this skill’s version/range, command and schema/status guidance, deprecated/removed API warnings, and source-of-truth list. Re-run the package quality gates and CLI/wheel smoke checks, then compare the skill against `README.md`, `CHANGELOG.md`, `RELEASE.md`, tests, and shipped assets. Do not describe an unreleased design as supported behavior.

## Before finalizing generated code or artifacts

- Confirm the installed/runtime version and Python compatibility.
- Prefer documented CLI commands and stable public helpers; no private APIs or invented options.
- Validate packets/batches, inspect warnings, and confirm output paths and status transitions.
- Check claims against source notes and domain QA before any style-only pass.
- Run the narrowest relevant smoke command, then the full repository gates for code changes.
