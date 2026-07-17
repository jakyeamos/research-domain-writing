---
schemaVersion: 1
projectName: Research Domain Writing
summary: RDW 0.2.2 release candidate fixes the guided PyPI wizard's Bash set -e exits while preserving the canonical rdw CLI and packaged asset parity.
healthScore: 90
statusLabel: release_candidate
nextStep: Verify the 0.2.2 source tip, integrate it from a clean isolated worktree, tag v0.2.2, and rerun the publish wizard preflight before any upload.
blockers:
  - Slash-command behavior should still receive a manual post-install smoke in each target agent before broader announcement.
  - PyPI publication remains pending the verified v0.2.2 main/tag state, final token confirmation, and irreversible publish step; the live registry still reports 0.1.0.
  - Do not publish v0.2.1: its first wizard preflight exposed a Bash set -e control-flow bug, fixed by this 0.2.2 candidate.
  - Packet merge/conflict resolution for concurrent updates is a post-0.1 enhancement.
lastUpdated: 2026-07-17
tags: [aios, writing, research, skill, python, cli, pypi]
areas: [engineering, writing]
goals: []
repoType: tool
sourceOfTruth: mixed
primaryLanguage: Python
activeBranch: codex/rdw-source-0.2.2
lastCommitDate: 2026-07-17
quality:
  lint: pass
  types: pass
  tests: pass
  deadCode: pass
  structure: pass
canonicalCommands:
  install: uv sync
  dev: unknown
  lint: uv run ruff check .
  format: uv run ruff format --check .
  typecheck: uv run basedpyright src tests scripts
  test: uv run pytest -q
  build: uv build
  deadcode: unknown
agentExpectationsVersion: 1
---

## Current State

Research Domain Writing is a standalone, installable, file-based pipeline for turning research into grounded domain copy, QA output, and a human style pass. It separates research, domain copywriting, domain QA, and humanizer/blader responsibilities so style transformation does not invent domain knowledge.

The repo now has a real `rdw` Python CLI that acts as an agent harness: it validates packets and batches, creates deterministic task/batch planning folders with explicit output-format contracts, emits prompt bundles, installs agent skills/templates, and packages the curated assets for wheel installs. The 0.2.2 candidate keeps `rdw` as the canonical human-facing command while retaining compatibility wrappers; it intentionally does not call LLM APIs, browse, research, or draft autonomously.

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

## What Does Not Exist Yet

- No autonomous batch execution runner; `rdw batch plan` validates and expands planned task bundles only.
- No robust packet merge/conflict resolution for concurrent updates.
- No mature legal, finance, or medicine domain packs.
- Adapter extras are stubs; RDW does not call model APIs by default.
- No diff-based regression tests on QA rules.
- No dead-code scanner is configured.

## Next Step

Complete the v0.2.2 release flow by integrating the reviewed candidate, tagging `v0.2.2`, running the manual post-install slash smoke, and publishing to PyPI with a valid account token. Keep the immutable `v0.2.1` tag unpublished; the registry remains at 0.1.0 until the corrected release is published.

## Quality Ladder Notes

2026-07-17 (codex/rdw-source-0.2.2): Found that the 0.2.1 publish wizard exited during its first stage under Bash `set -e`; corrected all library `&&` guards whose false path is expected, including stage timing, input defaults, and completion summaries. Focused ShellCheck and non-publishing wizard preflight are required before promotion.

2026-07-17 (v0.2.1): Verified remote source tip `feae190`, integrated from remote main `8f3387f` as `bc39099`, promoted that commit to live `main`, and tagged `v0.2.1`; the unmapped-package-file parity gap was fixed before promotion. `uv sync --locked`, `uv lock --check`, strict package-asset parity, ShellCheck, Ruff check/format, BasedPyright, 38 pytest tests, Vulture, `git diff --check`, `uv build`, source CLI/lifecycle smoke, and fresh wheel consumer/install smoke all passed. Manual slash smoke and PyPI publication remain pending.


Additional check on 2026-07-04: `uv run ruff check .`, `uv run basedpyright`,
and `uv run pytest` passed after the README install documentation update.

2026-07-05: Added golden snapshot tests and GitHub Actions CI (lint/format/types/tests/build/wheel-smoke).

2026-07-05 (feat/v0.2-hardening, Task 4): Extracted config-loading helpers from `src/rdw/validation.py` into a new shared module `src/rdw/config.py` (pure refactor, no behavior change). `config.py` exposes `config_root`, `load_config`, `known_domains`, `enabled_domains`, `output_formats`, `default_output_format`. Deleted the now-duplicated private helpers from `validation.py` (`_config_root`, `_load_config`, `_enabled_or_known_domains`, `_output_formats`) and their now-unused imports (`asset_path`, `load_yaml`, `normalize_yaml`). Renamed a local variable in `validate_batch` from `output_formats` to `known_formats` to avoid shadowing the imported `output_formats` function. `uv run ruff check .`, `uv run ruff format --check .`, and `uv run basedpyright src tests scripts` all pass clean; `uv run pytest -q` passed 17 tests (up from 12, includes new `test_config_domain_and_format_accessors`). Commit: `deb2e0c`.

2026-07-06 (feat/v0.2-hardening): Added explicit `output_format` propagation to `rdw task plan` and inferred task contracts. Contracts now default from `config/output-formats.yaml`, preserve CLI/batch overrides, and warn on unknown formats. Golden task contracts and prompt bundles were updated to include `output_format: markdown`; regression coverage now includes default, explicit, and unknown output formats. `uv run ruff check .`, `uv run ruff format --check .`, `uv run basedpyright src tests scripts`, `uv run pytest -q` (19 tests), and `uv build` all passed. No dead-code scanner is configured. Commit: `1f34d99`.

2026-07-07 (feat/v0.2-hardening, Wave 3): Lifecycle workflow (`rdw status`, `rdw task mark`, `rdw batch status/resume`), JSON Schema export (`rdw schema`), and provider-neutral adapter stubs (`rdw adapter`). Optional extras: `[openai]`, `[anthropic]`, `[local]`, `[adapters]`. `uv run ruff check .`, `uv run ruff format --check .`, `uv run basedpyright src tests scripts`, `uv run pytest -q` (36 tests), and `uv build` passed. No dead-code scanner is configured. Commit: `1b918e2`.

## Agent Notes

Do not collapse research and humanizer responsibilities. If a draft needs new facts, route back to research rather than allowing the humanizer/blader step to invent content. AIOS may add thin adapters, but RDW pipeline prompts, domain packs, and batch runner work belong in this repo.

Router logic now lives in `config/router-inference.yaml` + `src/rdw/router.py`; do not reintroduce hard-coded inference in `planner.py`.
