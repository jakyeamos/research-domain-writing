---
schemaVersion: 1
projectName: Research Domain Writing
summary: RDW v0.2.0 is a healthy installable agent-first CLI/package with green code checks, but modernization planning found stale lock, release, and source/package truth surfaces.
healthScore: 82
statusLabel: modernization_baseline
nextStep: Review docs/modernization/TARGET.md and EXEC_PLAN.md, then begin the protected M0 modernization slice.
blockers:
  - Current release surfaces are not publish-ready until uv.lock, packaged release metadata, and the PyPI wizard version are aligned.
  - Slash-command behavior still needs a manual post-install smoke in each target agent before broader announcement.
lastUpdated: 2026-07-15
tags: [aios, writing, research, skill, python, cli, pypi]
areas: [engineering, writing]
goals: []
repoType: tool
sourceOfTruth: mixed
primaryLanguage: Python
activeBranch: main
lastCommitDate: 2026-07-09
quality:
  lint: pass
  types: pass
  tests: pass
  deadCode: pass
  structure: warning
  lock: fail
  package: warning
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
The baseline also confirms stale lock/package/release metadata and lifecycle/
contract duplication risks; these are captured in `docs/modernization/`.

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

## What Does Not Exist Yet

- No autonomous batch execution runner; `rdw batch plan` validates and expands planned task bundles only.
- No robust packet merge/conflict resolution for concurrent updates.
- No mature legal, finance, or medicine domain packs.
- Adapter extras are stubs; RDW does not call model APIs by default.
- No diff-based regression tests on QA rules.
- No dedicated dead-code CI gate is configured; the scoped Vulture baseline is clean.
- No canonical source/package asset parity gate exists yet.

## Next Step

Review the modernization target and execution plan. If accepted, create the
protected implementation branch/worktree and begin M0. Do not publish or retag
until the lockfile, package assets, release docs, and publish wizard are aligned.

## Quality Ladder Notes

2026-07-15: Baseline passed `uv run ruff check .`, `uv run ruff format --check .`,
`uv run basedpyright src tests scripts`, `uv run pytest -q` (36), the pre-CR
coverage wrapper, `shellcheck scripts/*.sh`, scoped Vulture, `uv build`, and
source/isolated-wheel CLI smoke. `uv lock --check` failed because the editable
package entry still says 0.1.0.

2026-07-15: Root/package content directories match, but packaged RELEASE.md,
root SKILL.md, packaged CHANGELOG.md, publish wizard version, and uv.lock drift
from the v0.2.0 source release. See `docs/modernization/AUDIT.md`.

2026-07-15: Modernization strategy is deep refactor in place. Preserve the
no-LLM core boundary, CLI names, packet semantics, and run-artifact paths;
replace duplicated contracts, unsafe lifecycle writes, and manual asset mirrors.

## Agent Notes

Do not collapse research and humanizer responsibilities. If a draft needs new facts, route back to research rather than allowing the humanizer/blader step to invent content. AIOS may add thin adapters, but RDW pipeline prompts, domain packs, and batch runner work belong in this repo.

Router logic now lives in `config/router-inference.yaml` + `src/rdw/router.py`; do not reintroduce hard-coded inference in `planner.py`.
