---
schemaVersion: 1
projectName: Research Domain Writing
summary: RDW v0.2.0 modernization now includes the serial filesystem-first fixture batch executor and an executable basketball acceptance contract with source-grounded fixtures; the core remains offline and auditable.
healthScore: 97
statusLabel: acceptance_gates_implemented
nextStep: Run the full RDW writing pipeline and human review for the basketball acceptance fixtures; keep example_only true until graduation gates pass, with release actions separate.
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

The packet-lineage decision is now recorded in
`docs/architecture/ADR-002-packet-lineage-and-conflict-resolution.md`: keep one
accepted packet head, stage candidate revisions in run-local artifacts, require
parent-head matching for explicit replacement, and preserve stale candidates in
conflict/resolution artifacts. Automatic merges, last-write-wins behavior, and
hidden persistence remain out of scope.

The evidence-aware diff-QA contract is now recorded in
`docs/architecture/ADR-003-evidence-aware-diff-qa-regression-contract.md`:
compare approved, hash-pinned packet or draft baselines against normalized
claims, source links, uncertainty, and stable machine rules; require an
explicit draft claim ledger; and make missing or ambiguous evidence
indeterminate rather than an automatic pass. The diff report remains additive
to the existing QA artifact and blocks final promotion on blocker, major, or
indeterminate findings.

The bounded batch-executor decision is now recorded in
`docs/architecture/ADR-004-bounded-batch-executor-semantics.md`: keep the
filesystem event stream and task receipts authoritative, use one writer and
serial input-order dispatch first, bound attempts and time, make pause/cancel
cooperative, require explicit reconciliation for unknown attempts, continue
independent tasks after review/failure, and never roll back completed work.

ADR-005 now selects basketball analytics as RDW's first mature domain-pack
target. The contract narrows the initial surface to ranking explanations,
player/stat interpretation, comparisons, role context, team fit, and bounded
projections; it defines ranking packet metadata, source/freshness rules,
positive and negative acceptance fixtures, and objective QA gates. The current
synthetic basketball pack remains `example_only` until those gates pass.

Ticket #11 now implements an explicit `mature` basketball packet validator,
source-grounded ranking/player/team-fit acceptance packets, positive and
negative fixture coverage, deterministic claim-ledger and draft misuse checks
exposed through `rdw validate-claim-ledger`. The generic validator remains compatible
with the existing basketball demo, music packet, and technical packet; the
new acceptance corpus remains example-only and does not add browsing, provider
SDKs, ranking calculation, or model calls. Mature-only rules now live in
`src/rdw/mature_validation.py`; the generic validator remains below the source
size warning threshold.

Wayfinder ticket #10 is now implemented across the focused batch executor
modules in `src/rdw/batch_execution.py`, `batch_models.py`, `batch_support.py`,
`batch_events.py`, `batch_projection.py`, and `batch_leases.py`.
`rdw batch execute --fixture-map` runs the serial fixture slice with typed
policy bounds, an exclusive filesystem lease, immutable attempt receipts,
event-ID replay projection, cooperative pause/cancel, partial-success counts,
and explicit unknown-attempt recovery. The orchestration module is now below
the repository's preferred single-file source limit; the implementation does
not add a provider SDK, browser, model call, database, parallel worker, or
packet merge.

## What Exists

- `README.md` explaining the full pipeline, slash-command usage, batch workflow, domain packs, and limitations.
- `SKILL.md` as the agent skill entrypoint.
- `src/rdw/` as the installable Python package and CLI surface.
- `prompts/` for router, planner, researcher, packet builder, copywriter, QA, humanizer, orchestrator, and batch runner flows.
- `domains/` and `config/` for domain-specific writing and source rules.
- `knowledge/` examples and reusable packet patterns.
- `examples/` with end-to-end sample tasks.
- `rdw doctor`, `rdw validate-packet`, `rdw validate-claim-ledger`, `rdw validate-batch`, `rdw new-domain`, `rdw task plan`, `rdw batch plan`, `rdw batch execute`, `rdw batch pause`, `rdw batch cancel`, and `rdw install`.
- Opt-in `rdw validate-packet --mature` basketball acceptance gates for metric semantics, ranking metadata, source freshness, role/sample context, confidence, and synthetic provenance.
- Lifecycle commands: `rdw status`, `rdw task mark`, `rdw batch status`, and read-only `rdw batch resume`.
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
- `docs/architecture/ADR-002-packet-lineage-and-conflict-resolution.md` defining
  file-backed packet revisions, claim/source provenance, conflict categories,
  human resolution artifacts, and explicit promotion rules.
- `docs/architecture/ADR-003-evidence-aware-diff-qa-regression-contract.md`
  defining deterministic packet/draft comparison units, baseline approval,
  DQA diagnostic codes, fixture goldens, and lifecycle integration.
- `docs/architecture/ADR-004-bounded-batch-executor-semantics.md` defining
  serial-first batch scheduling, leases, retry/backoff bounds, pause/resume/
  cancel behavior, partial-success projection, recovery, and verification.
- `docs/architecture/ADR-005-first-mature-domain-pack.md` selecting basketball
  analytics and defining its packet contract, ranking extension, source policy,
  acceptance rubric, fixture matrix, and graduation sequence.
- `src/rdw/execution.py` as the core fixture executor and receipt/artifact
  validation gate.
- The batch executor split into policy/data models, shared filesystem support,
  event replay, projections, leases, and serial orchestration modules under
  `src/rdw/`.
- `src/rdw/adapters/fixture.py` plus `examples/fixtures/` as the deterministic
  external-runtime seam and success, uncertain, and rejected fixtures.
- `examples/acceptance/basketball/` as the source-grounded mature-pack corpus:
  one ranking surface, two player contexts, one team-fit context, QA ledgers,
  and negative provenance/semantic fixtures.
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

- No live/provider-backed autonomous batch execution runner yet. The bounded
  serial fixture executor exists for deterministic integration proof; real
  research, drafting, QA, and humanizer work remain agent-led.
- No production-ready mature domain pack yet; the basketball acceptance
  contract and source-grounded fixtures exist, but `example_only` remains true
  until the full writing pipeline and human graduation review pass.
- No packet merge/conflict resolution implementation yet; ADR-002 defines the
  next filesystem-backed implementation contract.
- No mature legal, finance, or medicine domain packs.
- No real provider adapter or autonomous external-runtime integration exists;
  the typed receipt/promotion path is currently exercised by the deterministic
  fixture adapter only. RDW does not call model APIs by default.
- No diff-based regression implementation or tests yet; ADR-003 defines the
  deterministic contract and fixture/golden requirements.
- No fresh Codex task slash smoke has been captured; the installed Codex/agents
  surface has been verified by symlink and skill-content inspection.

## Next Step

The modernization and release verification boundary are complete on
`codex/rdw-gpt56-modernization`, and the provider-neutral adapter boundary, the
first deterministic vertical slice, the packet-lineage decision, the
evidence-aware diff-QA contract, the bounded batch-executor implementation,
the first mature-domain decision, and the basketball acceptance implementation
are recorded. The next map action is the full RDW writing-pipeline and human
graduation review for the source-grounded basketball fixtures. Review/merge of
draft PR #9, tagging, and publishing remain separate release actions; do not
infer them from local or remote verification.

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

2026-07-15: Ticket #5 committed in `f859b4a`: ADR-002 defines stable packet
identity, content-addressed revisions, claim/source provenance, append-only
candidate review, explicit replacement, conflict artifacts, and human
resolution rules. Architecture review evidence passed; full checks remain at
52 tests with lint, types, lock, package parity, and shell gates green.

2026-07-15: Ticket #6 committed in `dae826c`: ADR-003 defines approved
hash-pinned baselines, normalized packet/draft claim records, explicit draft
claim ledgers, DQA-001 through DQA-010 diagnostics, fixture/golden coverage,
and fail/indeterminate lifecycle gates. TMCP review `tmcp-review-plan-5ec3d9c0`
passed all validations; full checks remain at 52 tests with lint, types, lock,
package parity, and shell gates green.

2026-07-15: Ticket #7 committed in `eb48c25`: ADR-004 defines serial-first
input-order dispatch, one-writer leases, bounded retries/backoff/time, honest
pause/resume/cancel behavior, partial-success projection, explicit unknown-
attempt reconciliation, and no rollback. TMCP review
`tmcp-review-plan-3f488911` passed all validations; full checks remain at 52
tests with lint, types, lock, package parity, and shell gates green.

2026-07-15: Ticket #10 implementation committed in `aae6dcd`: serial
filesystem-first fixture batch execution, typed policy bounds, exclusive
leases, immutable attempt receipts, retry/backoff, event replay dedupe,
cooperative pause/cancel, partial success, and unknown-attempt recovery. Full
checks passed with 62 tests, Ruff, basedpyright, Vulture, package parity, and
the final sdist/wheel build; pre-CR also warned that the new executor module is
larger than the preferred single-file source limit and needs a maintainability
follow-up.

2026-07-15: Maintainability follow-up committed in `33bcb45`: split the batch
executor by responsibility into models, shared support, events, projections,
leases, and orchestration. The behavior-neutral refactor passed all 62 tests,
Ruff, formatting, basedpyright, Vulture, package parity, diff checks, and a
fresh sdist/wheel build; the source-size warning is resolved.

2026-07-15: ADR-005 committed in `4adf92a`: basketball analytics is the first
mature-domain target. The contract defines ranking packet metadata, source and
freshness rules, confidence boundaries, five positive and seven negative
acceptance fixtures, and promotion gates; the existing synthetic pack remains
example-only until the rubric passes.

2026-07-15: Ticket #11 implementation committed in `c3e6449`: opt-in mature
basketball packet validation, ranking metadata and metric semantics, a
deterministic claim-ledger CLI, four source-grounded packets, five positive
matrix cases, and five negative provenance/semantic cases. Full checks passed
with 66 tests, Ruff, formatting, basedpyright, Vulture, shellcheck, lock
verification, package parity, pre-CR, sdist/wheel build, and isolated-wheel
mature packet plus claim-ledger smoke. `example_only` remains true pending
full pipeline and human review.

2026-07-15: Ticket #11 QA follow-up committed in `8eef1bb`: executable
unsupported-injury and forbidden-generic-praise negatives now run through the
claim-ledger gate; full tests, Ruff, basedpyright, and package parity remain
green. Pre-CR initially flagged `src/rdw/validation.py` at 617 nonblank lines;
the maintainability split in `f7d639a` reduces the generic validator to 466
lines and the final changed-line readiness check passes without that warning.

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
