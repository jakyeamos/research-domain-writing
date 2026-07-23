# Scope: limitations vs design

## Research

RDW does not perform research by itself. The agent does the research by following `prompts/research-planner.md` and `prompts/researcher.md`.

That means:

- The agent may use whatever tools it already has: browser, APIs, pasted stats, local files, notebooks, or user-provided material.
- RDW structures, validates, saves, and reuses what was gathered.
- There is no built-in crawler, live stats connector, publication database client, or model API runner in the current `v0.3.0` release candidate.

`config/research-sources.yaml` tells the agent what kinds of sources to prefer. It is not an automatic fetch configuration.

## CLI

The `rdw` CLI is a deterministic planning and validation harness:

- `rdw validate-packet` validates research packets.
- `rdw validate-packet --mature` applies the opt-in basketball acceptance gates.
- `rdw validate-claim-ledger` validates QA issue counts and packet fact traceability.
- `rdw validate-batch` validates batch YAML.
- `rdw task plan` writes a task contract, prompt bundle, and initial status file.
- `rdw batch plan` expands a batch into per-task planned folders and logs.
- `rdw install` installs slash command and skill templates.
- `rdw status`, `rdw task mark`, `rdw batch status`, and `rdw batch resume` track lifecycle state in run artifacts.
- `rdw task execute --fixture` runs one deterministic fixture through the
  adapter receipt, artifact validation, and existing task lifecycle. It is a
  prototype seam, not a provider runtime.
- `rdw batch execute --fixture-map` runs the bounded serial fixture executor.
  It owns a filesystem lease, immutable fixture attempts, bounded retry/backoff,
  event IDs, cooperative pause/cancel controls, and explicit unknown-attempt
  recovery. It does not call an LLM, browse, or execute real research.
- `rdw schema` exports JSON Schemas for packets, batches, and task contracts.
- `rdw adapter` exposes optional provider-neutral runtime stubs plus the local
  `fixture` adapter used by the single-task vertical-slice prototype.

The CLI does not call an LLM, browse the web, conduct autonomous research, or write final copy.

## Batch

`rdw batch plan` is not an autonomous batch writer. It validates and expands
tasks so an agent can execute them consistently. The fixture-backed executor is
only a deterministic integration seam for planned batches; it does not replace
the agent-led research, drafting, QA, or humanizer pipeline.

Each planned task starts at status `planned`. The agent or a future adapter is responsible for moving tasks through research, draft, QA, final, and review states.

## Workarounds

| Need | v0.3 approach |
| --- | --- |
| Live stats or docs | Agent researches and saves packets under `knowledge/<domain>/` |
| Basketball acceptance gate | `rdw validate-packet ... --mature` plus `rdw validate-claim-ledger ... --mature` |
| Repeatable single task | `rdw task plan ... --out <run-dir>` |
| Repeatable batch setup | `rdw batch plan <batch.yaml> --out <run-dir>` |
| Deterministic batch fixture | `rdw batch execute <run-dir> --fixture-map <map.yaml> --root <repo>` |
| Pause or cancel fixture batch | `rdw batch pause|cancel <run-dir>` |
| Track task progress | `rdw task mark research-done <run-dir>` |
| Resume a batch | `rdw batch resume <run-dir>` |
| Editor/CI schema validation | `rdw schema packet --format jsonschema` |
| Agent slash command | `rdw install --target all` |

## Future upgrades

- Real provider adapters that call external APIs (provider stubs exist today).
- Direct integration with agent runtimes that can execute prompt bundles.
- Richer packet schema migrations.
