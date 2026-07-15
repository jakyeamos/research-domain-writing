# RDW Modernization Target

- Target status: proposed
- Baseline: `v0.2.0` / commit `8f3387f`
- Strategy: deep refactor in place
- Product identity: local-first, agent-first research-grounded writing harness

## Product principles

1. **Grounding before fluency.** Facts, sources, uncertainty, and domain rules
   remain explicit before copy or style work begins.
2. **One contract, many surfaces.** CLI output, YAML artifacts, JSON Schema,
   prompts, package assets, and installed skills derive from the same contract
   definitions.
3. **Deterministic core, replaceable runtime.** RDW plans, validates, and records
   state deterministically. External agents and optional provider adapters remain
   replaceable and do not become hidden core dependencies.
4. **Readable for humans, stable for machines.** Every important command keeps a
   concise human view and can emit structured JSON with stable diagnostic codes.
5. **Safe files are part of the product.** Run state, logs, and installed assets
   survive interruption and do not silently lose concurrent work.
6. **Compatibility is intentional.** Existing command names, artifact paths,
   packet meanings, and agent-install locations remain valid until a documented
   migration is available.
7. **Boring dependencies win.** Add a dependency only when it removes a proven
   correctness or maintenance risk; do not add a database, hosted service, or
   model SDK to the core to make the architecture look newer.

## Target product and user journeys

RDW remains a CLI/package that creates auditable handoffs for an agent. It does
not become a browser application, autonomous researcher, or general LLM
orchestrator in this modernization.

### Plan a single task

```text
request + overrides
  -> resolved route with candidates, confidence, and warnings
  -> validated task contract
  -> prompt bundle + initial status artifact
  -> external agent executes research -> packet -> draft -> QA -> humanizer
```

The contract must show which fields were explicit, which were inferred, which
packet/pack paths exist, and what the agent must not claim.

### Validate a packet or batch

The validator returns ordered diagnostics with a code, path, severity, and
message. Human output remains short; `--json` returns the complete diagnostic
payload. Strict mode preserves the current grounding checks and adds no silent
fallbacks.

### Plan and resume a batch

Batch planning validates the input, resolves each task through the same single
task use case, writes planned task folders, and records a batch event. Resume
and status read projections from task state/events without mutating files.

### Advance a task

Status changes go through a transition policy. A valid change records one event,
atomically updates the task projection, and refreshes the batch projection. An
invalid transition returns a stable diagnostic and leaves all files unchanged.

### Install agent surfaces

Installation stages its managed asset tree, verifies the manifest, then swaps it
into place atomically. Existing real directories are still protected by
default. `--backup` and `--force` remain explicit, and every managed file has a
known owner/source.

### Use an installed wheel

An installed consumer sees the same prompt, config, skill, domain, and release
metadata as a source checkout. The release build verifies that package assets
are generated from the canonical authoring tree and that the wheel can perform
the critical doctor, validation, and planning flows without the source repo.

## Target information architecture

Keep current commands as compatibility-preserving entrypoints while making the
grouping explicit internally:

```text
rdw doctor [--json]
rdw validate-packet ... [--json]
rdw validate-batch ... [--json]
rdw schema packet|batch|task-contract
rdw task plan|mark|status
rdw batch plan|status|resume
rdw adapter list|run
rdw install
rdw new-domain
```

Future aliases may introduce `rdw validate packet` and `rdw task status`, but
the existing spellings must continue to work during this modernization.

## Target architecture

The code should stay small, but responsibilities should be explicit:

```text
src/rdw/
  cli/          argument parsing, rendering, exit-code mapping
  contracts/    typed task/packet/batch/status models and serialization rules
  routing/      pure scored inference and route diagnostics
  validation/   semantic packet/batch policies and diagnostic construction
  runs/         task/batch use cases, transitions, event projections
  assets/       packaged generated content and manifest
  io/           YAML/JSON, atomic writes, append-only events, clocks
  adapters/     provider-neutral external runtime seam
```

This is a responsibility map, not a demand to create one file per label. A
small implementation may keep `config.py`, `resources.py`, or `yaml_io.py`
until the new boundaries are proven. Avoid replacing a 2,600-line repository
with a large framework-shaped directory tree.

### Contracts

Create one executable definition for:

- research packets and strictness policies;
- batch input and defaults;
- resolved task contracts;
- task lifecycle and batch projections;
- diagnostics and exit categories.

Use typed Python models at public seams. Generate JSON Schema from those models
or from one shared schema definition, rather than maintaining an independent
hand-written schema copy. Domain extension rules remain explicit semantic
validators because they depend on the selected domain pack.

### Routing

The router becomes a pure function over request text, explicit overrides, and a
resolved configuration snapshot. It returns:

- the resolved fields;
- ranked candidate domains/output types when ambiguous;
- confidence and warnings;
- explicit versus inferred fields;
- the rationale used in the contract.

All IDs and paths are derived only after the resolved contract exists. Explicit
overrides always win. Unknown domains and low-confidence routes remain visible.

### Run state

Preserve the current artifact paths:

- task: `status.json`, `task-contract.yaml`, `prompt-bundle.md`;
- batch: `summary.yaml`, `batch-log.jsonl`, `tasks/<task_id>/`.

Internally, treat lifecycle changes as events and projections:

- append one event for each accepted transition;
- atomically replace task and batch projections;
- centralize the `needs_review` policy;
- support old status files with missing `history` as a compatibility read;
- reject illegal transitions without writing anything.

No database is needed. The filesystem remains the persistence layer.

### Canonical content and package assets

The repository root remains the authoring source because it is where users edit
domain packs, prompts, examples, and config. `src/rdw/assets/` becomes a
generated package mirror, not a second hand-edited source.

The implementation should provide:

- a manifest of canonical source paths and package destinations;
- a sync operation for development/release builds;
- a check operation that fails on drift;
- a build hook or equivalent release command that cannot silently package stale
  assets;
- parity coverage for version, README/limitations, release instructions,
  prompts, config, domains, examples, and install templates.

The first implementation may retain checked-in generated assets for transparent
source distributions, but every change must flow one way from the root source
and be checked in CI.

### CLI and errors

Expected input, config, YAML, and filesystem failures should become structured
diagnostics rather than tracebacks. Define stable exit categories:

- `0`: command completed and validation passed;
- `1`: user input or domain/contract validation failed;
- `2`: usage/configuration/environment failure;
- `3`: internal unexpected failure, with a concise reference for debugging.

Add `--json` to doctor, validators, planners, and lifecycle views. Human output
continues to be the default. JSON must not include timestamps or absolute paths
unless those fields are already part of the artifact contract, so deterministic
tests remain practical.

### Install safety

Stage generated assets in a sibling temporary directory, validate the manifest,
and atomically replace the managed destination. Never remove an arbitrary path
before a replacement is ready. Keep explicit backup/force behavior and test
symlink, real-directory, interrupted-copy, and fallback-copy cases.

## Data ownership and compatibility

| Data | Owner | Compatibility rule |
| --- | --- | --- |
| Packet YAML | User/agent research workflow | Preserve fields and strict semantics; add migrations only for schema changes |
| Batch input YAML | User/agent | Preserve current fields and depth aliases |
| Task contract | Planner | Preserve existing required fields and path meanings |
| `status.json` | Lifecycle use case | Read old files; write new versioned projections |
| `summary.yaml` | Batch projection | Preserve location and counts; derive from events/task state |
| `batch-log.jsonl` | Lifecycle event stream | Keep existing event fields; append new fields compatibly |
| Prompt bundle | Planner/content source | Preserve execution order and fact/style boundary |
| Installed skills/templates | Installer/package | Preserve target locations and command names |

No production database, auth, billing, public HTTP API, or hosted deployment is
in scope. There is no irreversible data migration required; existing run
directories are the migration fixture set.

## Testing and verification target

The target quality ladder is:

1. Ruff lint and format.
2. BasedPyright.
3. Vulture over tracked project paths.
4. Shellcheck for shell scripts.
5. Focused contract/transition tests.
6. Full pytest suite.
7. `uv lock --check`.
8. Canonical-source/package-asset parity check.
9. Clean `uv build`.
10. Fresh wheel consumer smoke: doctor, strict packet validation, batch
    validation/planning, task planning, schema export, and lifecycle mark.
11. Release preflight with version derived from `pyproject.toml`.

Verification must include malformed YAML, missing files, invalid transitions,
explicit planner overrides, ambiguous routing, stale/missing package assets,
interrupted-safe-write simulations, and installer safety cases. Tests should
protect these contracts rather than mirror private helper implementations.

## Deployment and migration approach

1. Keep the current `main` checkout as the protected baseline.
2. Implement on a dedicated modernization branch/worktree.
3. Preserve CLI aliases and artifact shapes through the refactor.
4. Add compatibility readers before changing state writers.
5. Migrate existing generated run fixtures through read/mark/status tests; do
   not rewrite user output folders automatically.
6. Switch package assets to the canonical-source pipeline only after parity and
   fresh-wheel checks pass.
7. Remove old duplicated contract helpers, stale release constants, and manual
   mirror instructions once all consumers use the new path.
8. Cut a version only after the complete release ladder passes.

Rollback is a git branch/commit rollback plus retention of existing run folders.
Because no database or remote state is introduced, rollback does not require a
data restore.

## Explicit non-goals

- Built-in browsing, live statistics, crawler, or publication-database client.
- Model API calls in the core package.
- Autonomous research, drafting, QA, or final-copy execution.
- SQLite or hosted persistence.
- AIOS runtime coupling.
- Browser UI or web application surface.
- New legal, finance, or medical domain packs as part of architecture work.
- A new framework or dependency without a measured contract benefit.

## Target scorecard

| Dimension | Current | Target | Proof |
| --- | ---: | ---: | --- |
| Product coherence | 4 | 5 | Stable agent-first journeys and explicit limits |
| Correctness/data integrity | 3 | 5 | Typed contracts, legal transitions, atomic projections |
| Architectural coherence | 3 | 5 | Thin CLI, one contract source, one content source |
| Maintainability | 3 | 4 | Removed duplication and stale release constants |
| Testability | 3 | 5 | Contract, package, transition, malformed-input, and installer coverage |
| Security/privacy | 4 | 5 | Safe staged installs and no hidden network/secrets |
| CLI quality/accessibility | 3 | 5 | Stable JSON plus concise human output and predictable side effects |
| Performance | 4 | 4 | Keep local file model; avoid unnecessary scans and rewrites |
| Operability | 2 | 5 | Structured diagnostics, state projections, and release checks |
| Developer experience | 3 | 5 | Lock/parity gates, one source, truthful docs, reproducible wheel |
