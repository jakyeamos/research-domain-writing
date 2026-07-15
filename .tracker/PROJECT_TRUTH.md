---
schemaVersion: 1
projectName: Research Domain Writing
summary: RDW v0.2.0 modernization is implementation-complete and release-proofed on a feature branch; the provider-neutral adapter contract and first deterministic research-to-QA vertical slice are now verified while the core remains offline and auditable.
healthScore: 97
statusLabel: fixture_vertical_slice_verified
nextStep: Design packet lineage and conflict resolution in Wayfinder ticket #5; review/merge draft PR #9, tagging, and publishing remain separate authorized release actions.
blockers:
  - A fresh Codex task was not opened for slash smoke; the installed Codex/agents surface was verified by symlink and skill-content inspection.
  - The modernization branch is not a release action; merge, tagging, and publishing remain explicitly deferred.
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
planner overrides into the final contract, supports JSON diagnostics with
stable exit categories, enforces legal lifecycle transitions, atomically
persists run state, stages managed package assets before replacement, and
documents the full isolated-wheel proof in CI and `RELEASE.md`.

The release boundary is now verified by draft PR #9: GitHub Actions run #3
passed on Python 3.12 and 3.13, and fresh Claude and Cursor sessions both
recognized `/rdw improve the copy on my LIS leaderboard`, inferred a task
contract, and stopped when grounded LIS source material was missing. The
Codex/agents install surface is present and points at this checkout; a fresh
Codex task smoke remains intentionally unrun.

The next-phase trust boundary is now explicit in
`docs/architecture/ADR-001-provider-neutral-adapter-contract.md`: one task at
a time, adapter-owned namespaced staging and receipts, core-owned validation,
promotion, and lifecycle events, with network and credentials kept outside
the deterministic core. No provider SDK has been added.

The first executable slice now runs `rdw task execute --fixture` through the
same boundary. It validates a research packet and QA result, promotes only
validated artifacts, records every attempt under `adapter-runs/fixture/`, and
uses the existing lifecycle for `final-done`, `qa-failed`, and auditable retry
behavior. The fixture runtime is deterministic and is not a provider API.

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
- `docs/architecture/ADR-001-provider-neutral-adapter-contract.md` defining
  the provider-neutral one-task adapter receipt and trust boundary.
- `src/rdw/execution.py` as the core fixture executor and receipt/artifact
  validation gate.
- `src/rdw/adapters/fixture.py` plus `examples/fixtures/` as the deterministic
  external-runtime seam and success, uncertain, and rejected fixtures.
- `scripts/sync-package-assets.py --check|--sync` as the canonical root/package
  asset parity check and synchronization tool.
- `--json` output for validation, task/batch planning, status, resume, and
  doctor commands.
- `src/rdw/contracts.py` shared required-field definitions used by validation
  and schema export.
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
- No real provider adapter or autonomous external-runtime integration exists;
  the typed receipt/promotion path is currently exercised by the deterministic
  fixture adapter only. RDW does not call model APIs by default.
- No diff-based regression tests on QA rules.
- No fresh Codex task slash smoke has been captured; the installed Codex/agents
  surface has been verified by symlink and skill-content inspection.

## Next Step

The modernization and release verification boundary are complete on
`codex/rdw-gpt56-modernization`, and the provider-neutral adapter boundary plus
the first deterministic vertical slice are verified. The next Wayfinder slice
is [Design packet lineage and conflict resolution](https://github.com/jakyeamos/research-domain-writing/issues/5).
Review/merge of draft PR #9, tagging, and publishing remain separate release
actions; do not infer them from local or remote verification.

## Quality Ladder Notes

2026-07-15: Baseline passed `uv run ruff check .`, `uv run ruff format --check .`,
`uv run basedpyright src tests scripts`, `uv run pytest -q` (36), the pre-CR
coverage wrapper, `shellcheck scripts/*.sh`, scoped Vulture, `uv build`, and
source/isolated-wheel CLI smoke.

2026-07-15: M0/M1 committed as `5bc91e3`: `uv.lock`, packaged release metadata,
the PyPI wizard version, CI lock/shell/package checks, and the canonical
root/package asset sync are aligned for v0.2.0.

2026-07-15: Release boundary verified in draft PR #9: GitHub Actions run #3
passed on Python 3.12 and 3.13; fresh Claude and Cursor `/rdw` smoke sessions
inferred the LIS task contract and requested missing grounding instead of
inventing facts. Codex/agents surface inspection passed; no fresh Codex task
was opened.

2026-07-15: Ticket #3 decision committed as `c2fdd40`: ADR-001 defines a
provider-neutral, one-task artifact-first adapter contract. Adapters stage
namespaced receipts and artifacts; the core validates, promotes, and owns
lifecycle events. Provider SDKs, browsing, and autonomous batch execution
remain deferred.

2026-07-15: Ticket #4 implemented in `602d049`: the deterministic fixture
 adapter and core executor validate receipt identity, hashes, packet and QA
 gates, promote five run-local artifacts, preserve rejected/uncertain work,
 and demonstrate `qa-failed` -> `--resume` -> `final-done`. Full checks passed
 with 52 tests, package/build gates, and isolated wheel execution.

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

2026-07-15: M6 remediation committed as `1bcfe25`: shared required-field
contracts, low-confidence general routing, atomic developer asset sync,
atomic CLI/adapter artifacts, reproducible Vulture CI, and regenerated goldens
are green across 48 tests plus fresh-wheel critical-flow smoke.

2026-07-15: Modernization strategy is deep refactor in place. Preserve the
no-LLM core boundary, CLI names, packet semantics, and run-artifact paths;
replace duplicated contracts, unsafe lifecycle writes, and manual asset mirrors.

2026-07-15: Committed the modernization planning packet in `d6d9212`; the
approved implementation branch is now `codex/rdw-gpt56-modernization`.

## Agent Notes

Do not collapse research and humanizer responsibilities. If a draft needs new facts, route back to research rather than allowing the humanizer/blader step to invent content. AIOS may add thin adapters, but RDW pipeline prompts, domain packs, and batch runner work belong in this repo.

Router logic now lives in `config/router-inference.yaml` + `src/rdw/router.py`; do not reintroduce hard-coded inference in `planner.py`.
