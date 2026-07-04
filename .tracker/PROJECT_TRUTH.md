---
schemaVersion: 1
projectName: Research Domain Writing
summary: Installable RDW 0.1 release candidate with an agent-first CLI harness, prompts, domain packs, packet/batch validation, packaged assets, examples, skill distribution, and release governance.
healthScore: 90
statusLabel: release_candidate
nextStep: Run scripts/publish-pypi-wizard.sh with a PyPI account token to complete the v0.1.0 PyPI upload.
blockers:
  - Slash-command behavior should still receive a manual post-install smoke in each target agent before broader announcement.
  - Packet merge/conflict resolution for concurrent updates is a post-0.1 enhancement.
lastUpdated: 2026-07-04
tags: [aios, writing, research, skill, python, cli, pypi]
areas: [engineering, writing]
goals: []
repoType: tool
sourceOfTruth: mixed
primaryLanguage: Python
activeBranch: main
lastCommitDate: 2026-07-04
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

The repo now has a real `rdw` Python CLI that acts as an agent harness: it validates packets and batches, creates deterministic task/batch planning folders, emits prompt bundles, installs agent skills/templates, and packages the curated assets for wheel installs. The CLI intentionally does not call LLM APIs, browse, research, or draft autonomously in v0.1.

## What Exists

- `README.md` explaining the full pipeline, slash-command usage, batch workflow, domain packs, and limitations.
- `SKILL.md` as the agent skill entrypoint.
- `src/rdw/` as the installable Python package and CLI surface.
- `prompts/` for router, planner, researcher, packet builder, copywriter, QA, humanizer, orchestrator, and batch runner flows.
- `domains/` and `config/` for domain-specific writing and source rules.
- `knowledge/` examples and reusable packet patterns.
- `examples/` with end-to-end sample tasks.
- `rdw doctor`, `rdw validate-packet`, `rdw validate-batch`, `rdw new-domain`, `rdw task plan`, `rdw batch plan`, and `rdw install`.
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

Complete the public v0.1 release flow by running `scripts/publish-pypi-wizard.sh`, publishing to PyPI with a valid account token, then running an installed `rdw doctor` smoke from PyPI.

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

## Agent Notes

Do not collapse research and humanizer responsibilities. If a draft needs new facts, route back to research rather than allowing the humanizer/blader step to invent content. AIOS may add thin adapters, but RDW pipeline prompts, domain packs, and batch runner work belong in this repo.
