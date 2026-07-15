---
schemaVersion: 1
projectName: Research Domain Writing
summary: RDW v0.2.0 is a healthy installable agent-first CLI/package with explicit contracts, guarded lifecycle state, transactional installs, and a documented fresh-wheel release proof on the modernization branch.
healthScore: 95
statusLabel: modernization_m5
nextStep: Run M6 adversarial review and final validation, then decide whether the branch is ready for merge/tag/publish.
blockers:
  - Slash-command behavior still needs a manual post-install smoke in each target agent before broader announcement.
  - The modernization branch is not a release action; publishing remains explicitly deferred until final review and cutover.
lastUpdated: 2026-07-15
tags: [aios, writing, research, skill, python, cli, pypi]
areas: [engineering, writing]
goals: []
repoType: tool
sourceOfTruth: mixed
primaryLanguage: Python
activeBranch: codex/rdw-gpt56-modernization
lastCommitDate: 2026-07-15
quality:
  lint: pass
  types: pass
  tests: pass
  deadCode: pass
  structure: pass
  lock: pass
  package: pass
  shell: pass
canonicalCommands:
  install: uv sync
  dev: unknown
  lint: uv run ruff check .
  format: uv run ruff format --check .
  typecheck: uv run basedpyright src tests scripts
  test: uv run pytest -q
  build: uv build
  deadcode: vulture src scripts tests --min-confidence 70
  lockcheck: uv lock --check
  shellcheck: shellcheck scripts/*.sh
agentExpectationsVersion: 1
---

## Current State

Research Domain Writing is a standalone, installable, file-based pipeline for turning research into grounded domain copy, QA output, and a human style pass. It separates research, domain copywriting, domain QA, and humanizer/blader responsibilities so style transformation does not invent domain knowledge.

The v0.2.0 repo has a real `rdw` Python CLI that validates packets and batches, creates deterministic task/batch planning folders with explicit output-format contracts, emits prompt bundles, installs agent skills/templates, exports schemas, records lifecycle state, and packages curated assets for wheel installs. The CLI intentionally does not call LLM APIs, browse, research, or draft autonomously.

The 2026-07-15 modernization baseline is green for lint, formatting, types,
tests, build, CLI smoke, shellcheck, scoped dead-code, and isolated wheel use.
The modernization branch derives release version truth from `pyproject.toml`,
checks the lockfile, verifies root/package asset parity, resolves explicit
planner overrides into the final contract, supports JSON diagnostics, enforces
legal lifecycle transitions, atomically persists run state, stages managed
package assets before replacement, and documents the full isolated-wheel proof
in CI and `RELEASE.md`.

## What Exists

- `README.md` explaining the full pipeline, slash-command usage, batch workflow, domain packs, and limitations.
- `SKILL.md` as the agent skill entrypoint.
- `src/rdw/` as the installable Python package and CLI surface.
- `prompts/` for router, planner, researcher, packet builder, copywriter, QA, humanizer, orchestrator, and batch runner flows.
- `domains/` and `config/` for domain-specific writing and source rules.
- `knowledge/` examples and reusable packet patterns.
- `examples/` with end-to-end sample tasks.
- `rdw doctor`, `rdw validate-packet`, `rdw validate-batch`, `rdw new-domain`, `rdw task plan`, `rdw batch plan`, and `rdw install`.
- Lifecycle commands: `rdw status`, `rdw task mark`, `rdw batch status`, `rdw batch resume`.
- Schema export: `rdw schema packet|batch|task-contract --format jsonschema`.
- Optional adapter stubs: `rdw adapter list`, `rdw adapter run <name> <run-dir>`.
- Task and batch planning now carry `output_format` through inferred contracts, CLI overrides, warnings for unknown formats, and golden prompt bundles.
- Compatibility wrappers in `scripts/` and `install/install.sh`.
- `scripts/publish-pypi-wizard.sh` for guided PyPI token capture, artifact rebuild, dry-run check, and confirmed publish.
- `docs/LIMITATIONS.md` and `docs/FUTURE-AIOS-INTEGRATION.md` documenting v1 boundaries.
- `RELEASE.md` and `CHANGELOG.md` for release governance.
- `docs/modernization/AUDIT.md`, `TARGET.md`, `EXEC_PLAN.md`, and `PROGRESS.md`
  for the proposed in-place modernization.
- `scripts/sync-package-assets.py --check|--sync` as the canonical root/package
  asset parity check and synchronization tool.
- `--json` output for validation, task/batch planning, status, resume, and
  doctor commands.
- `rdw` lifecycle transitions owned by `src/rdw/lifecycle.py`, with atomic
  status/summary writes and append-only batch events.
- Transactional package-asset installation with a managed-root marker,
  explicit unmanaged-root protection, backup/force behavior, and rollback on
  interrupted swaps.
- Installed-wheel fallback to packaged knowledge/config assets when a caller
  has no source checkout root.

## What Does Not Exist Yet

- No autonomous batch execution runner; `rdw batch plan` validates and expands planned task bundles only.
- No robust packet merge/conflict resolution for concurrent updates.
- No mature legal, finance, or medicine domain packs.
- Adapter extras are stubs; RDW does not call model APIs by default.
- No diff-based regression tests on QA rules.
- No dedicated dead-code CI gate is configured; the scoped Vulture baseline is clean.
- Release CI still needs the full fresh-wheel critical-flow matrix and the
- Remote CI has not yet run on this branch; local source, wheel, lock, asset,
  shell, type, test, and pre-CR checks are green.

## Next Step

Run M6 from `docs/modernization/EXEC_PLAN.md`: adversarially review contract
compatibility, lifecycle/data integrity, installer safety, package parity,
documentation drift, and the complete quality ladder. Do not publish from this
branch as part of the review.

## Quality Ladder Notes

2026-07-15: Baseline passed `uv run ruff check .`, `uv run ruff format --check .`,
`uv run basedpyright src tests scripts`, `uv run pytest -q` (36), the pre-CR
coverage wrapper, `shellcheck scripts/*.sh`, scoped Vulture, `uv build`, and
source/isolated-wheel CLI smoke.

2026-07-15: M0/M1 committed as `5bc91e3`: `uv.lock`, packaged release metadata,
the PyPI wizard version, CI lock/shell/package checks, and the canonical
root/package asset sync are aligned for v0.2.0.

2026-07-15: M2 committed as `ab2ef1f`: explicit planner overrides now shape
the resolved task contract, ambiguous routing emits warnings, malformed YAML
returns a controlled error, and JSON diagnostics are parseable on the CLI.

2026-07-15: M3 committed as `ae0510b` plus formatter follow-up `9c790df`:
legal lifecycle transitions, required QA-failure reasons, atomic state writes,
read-only batch status, and append-only batch events are covered by 42 tests.

2026-07-15: M4 committed as `c627bc7`: staged managed asset replacement,
unmanaged-root protection, command-file safety, packaged-resource fallback, and
isolated-wheel proof passed with 46 tests.

2026-07-15: M5 committed as `8dff263`: CI and release docs now prove locked
source/package/wheel/install parity; the PyPI wizard runs lock, asset, and
shell preflights; local release ladder passes 47 tests and pre-CR coverage.

2026-07-15: Modernization strategy is deep refactor in place. Preserve the
no-LLM core boundary, CLI names, packet semantics, and run-artifact paths;
replace duplicated contracts, unsafe lifecycle writes, and manual asset mirrors.

2026-07-15: Committed the modernization planning packet in `d6d9212`; the
approved implementation branch is now `codex/rdw-gpt56-modernization`.

## Agent Notes

Do not collapse research and humanizer responsibilities. If a draft needs new facts, route back to research rather than allowing the humanizer/blader step to invent content. AIOS may add thin adapters, but RDW pipeline prompts, domain packs, and batch runner work belong in this repo.

Router logic now lives in `config/router-inference.yaml` + `src/rdw/router.py`; do not reintroduce hard-coded inference in `planner.py`.
