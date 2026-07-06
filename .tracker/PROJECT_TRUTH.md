---
schemaVersion: 1
projectName: Research Domain Writing
summary: Installable RDW release candidate with an agent-first CLI harness, prompts, domain packs, packet/batch validation, packaged assets, examples, skill distribution, release governance, and explicit task output-format contracts.
healthScore: 90
statusLabel: release_candidate
nextStep: Run scripts/publish-pypi-wizard.sh with a PyPI account token to complete the v0.1.0 PyPI upload.
blockers:
  - Slash-command behavior should still receive a manual post-install smoke in each target agent before broader announcement.
  - Packet merge/conflict resolution for concurrent updates is a post-0.1 enhancement.
lastUpdated: 2026-07-06
tags: [aios, writing, research, skill, python, cli, pypi]
areas: [engineering, writing]
goals: []
repoType: tool
sourceOfTruth: mixed
primaryLanguage: Python
activeBranch: feat/v0.2-hardening
lastCommitDate: 2026-07-06
quality:
  lint: pass
  types: pass
  tests: pass
  deadCode: unknown
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

The repo now has a real `rdw` Python CLI that acts as an agent harness: it validates packets and batches, creates deterministic task/batch planning folders with explicit output-format contracts, emits prompt bundles, installs agent skills/templates, and packages the curated assets for wheel installs. The CLI intentionally does not call LLM APIs, browse, research, or draft autonomously in v0.1.

## What Exists

- `README.md` explaining the full pipeline, slash-command usage, batch workflow, domain packs, and limitations.
- `SKILL.md` as the agent skill entrypoint.
- `src/rdw/` as the installable Python package and CLI surface.
- `prompts/` for router, planner, researcher, packet builder, copywriter, QA, humanizer, orchestrator, and batch runner flows.
- `domains/` and `config/` for domain-specific writing and source rules.
- `knowledge/` examples and reusable packet patterns.
- `examples/` with end-to-end sample tasks.
- `rdw doctor`, `rdw validate-packet`, `rdw validate-batch`, `rdw new-domain`, `rdw task plan`, `rdw batch plan`, and `rdw install`.
- Task and batch planning now carry `output_format` through inferred contracts, CLI overrides, warnings for unknown formats, and golden prompt bundles.
- Compatibility wrappers in `scripts/` and `install/install.sh`.
- `scripts/publish-pypi-wizard.sh` for guided PyPI token capture, artifact rebuild, dry-run check, and confirmed publish.
- `docs/LIMITATIONS.md` and `docs/FUTURE-AIOS-INTEGRATION.md` documenting v1 boundaries.
- `RELEASE.md` and `CHANGELOG.md` for release governance.

## What Does Not Exist Yet

- No autonomous batch execution runner; `rdw batch plan` validates and expands planned task bundles only.
- No robust packet merge/conflict resolution for concurrent updates.
- No stronger JSON-schema validation beyond the current packet validator.
- No mature legal, finance, or medicine domain packs.
- No diff-based regression tests on QA rules.
- No dead-code scanner is configured.

## Next Step

Complete the public v0.1 release flow by running `scripts/publish-pypi-wizard.sh`, publishing to PyPI with a valid account token, then running an installed `rdw doctor` smoke from PyPI. The README now points readers at the PyPI package page while keeping source-checkout installation documented separately.

## Quality Ladder Notes

Checks run on 2026-07-04:

| Step | Status | Evidence |
| --- | --- | --- |
| Lint | Pass | `uv run ruff check .` passed. |
| Format | Pass | `uv run ruff format --check .` passed. |
| Type check | Pass | `uv run basedpyright src tests scripts` passed with 0 errors and 0 warnings. |
| Tests | Pass | `uv run pytest -q` passed with 12 tests. |
| Build | Pass | `uv build` built sdist and wheel. |
| Wheel smoke | Pass | Built wheel installed in a temp venv; installed `rdw doctor`, `rdw task plan`, `rdw batch plan`, and packaged-asset `rdw install --target all` passed. |
| Dead code | Unknown | No Vulture or equivalent dead-code command is configured. |

Additional check on 2026-07-04: `uv run ruff check .`, `uv run basedpyright`,
and `uv run pytest` passed after the README install documentation update.

2026-07-05: Added golden snapshot tests and GitHub Actions CI (lint/format/types/tests/build/wheel-smoke).

2026-07-05 (feat/v0.2-hardening, Task 4): Extracted config-loading helpers from `src/rdw/validation.py` into a new shared module `src/rdw/config.py` (pure refactor, no behavior change). `config.py` exposes `config_root`, `load_config`, `known_domains`, `enabled_domains`, `output_formats`, `default_output_format`. Deleted the now-duplicated private helpers from `validation.py` (`_config_root`, `_load_config`, `_enabled_or_known_domains`, `_output_formats`) and their now-unused imports (`asset_path`, `load_yaml`, `normalize_yaml`). Renamed a local variable in `validate_batch` from `output_formats` to `known_formats` to avoid shadowing the imported `output_formats` function. `uv run ruff check .`, `uv run ruff format --check .`, and `uv run basedpyright src tests scripts` all pass clean; `uv run pytest -q` passed 17 tests (up from 12, includes new `test_config_domain_and_format_accessors`). Commit: `deb2e0c`.

2026-07-06 (feat/v0.2-hardening): Added explicit `output_format` propagation to `rdw task plan` and inferred task contracts. Contracts now default from `config/output-formats.yaml`, preserve CLI/batch overrides, and warn on unknown formats. Golden task contracts and prompt bundles were updated to include `output_format: markdown`; regression coverage now includes default, explicit, and unknown output formats. `uv run ruff check .`, `uv run ruff format --check .`, `uv run basedpyright src tests scripts`, `uv run pytest -q` (19 tests), and `uv build` all passed. No dead-code scanner is configured. Commit: `1f34d99`.

## Agent Notes

Do not collapse research and humanizer responsibilities. If a draft needs new facts, route back to research rather than allowing the humanizer/blader step to invent content. AIOS may add thin adapters, but RDW pipeline prompts, domain packs, and batch runner work belong in this repo.
