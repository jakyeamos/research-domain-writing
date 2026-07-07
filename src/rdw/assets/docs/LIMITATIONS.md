# Scope: limitations vs design

## Research

RDW does not perform research by itself. The agent does the research by following `prompts/research-planner.md` and `prompts/researcher.md`.

That means:

- The agent may use whatever tools it already has: browser, APIs, pasted stats, local files, notebooks, or user-provided material.
- RDW structures, validates, saves, and reuses what was gathered.
- There is no built-in crawler, live stats connector, publication database client, or model API runner in v0.1.

`config/research-sources.yaml` tells the agent what kinds of sources to prefer. It is not an automatic fetch configuration.

## CLI

The `rdw` CLI is a deterministic planning and validation harness:

- `rdw validate-packet` validates research packets.
- `rdw validate-batch` validates batch YAML.
- `rdw task plan` writes a task contract, prompt bundle, and initial status file.
- `rdw batch plan` expands a batch into per-task planned folders and logs.
- `rdw install` installs slash command and skill templates.
- `rdw status`, `rdw task mark`, `rdw batch status`, and `rdw batch resume` track lifecycle state in run artifacts.
- `rdw schema` exports JSON Schemas for packets, batches, and task contracts.
- `rdw adapter` exposes optional provider-neutral runtime stubs (`local`, `openai`, `anthropic`).

The CLI does not call an LLM, browse the web, conduct autonomous research, or write final copy.

## Batch

`rdw batch plan` is not an autonomous batch writer. It validates and expands tasks so an agent can execute them consistently.

Each planned task starts at status `planned`. The agent or an adapter records progress through research, draft, QA, final, and review states.

## Workarounds

| Need | v0.1 approach |
| --- | --- |
| Live stats or docs | Agent researches and saves packets under `knowledge/<domain>/` |
| Repeatable single task | `rdw task plan ... --out <run-dir>` |
| Repeatable batch setup | `rdw batch plan <batch.yaml> --out <run-dir>` |
| Track task progress | `rdw task mark research-done <run-dir>` |
| Resume a batch | `rdw batch resume <run-dir>` |
| Editor/CI schema validation | `rdw schema packet --format jsonschema` |
| Agent slash command | `rdw install --target all` |

## Future upgrades

- Real provider adapters that call external APIs (stubs exist today).
- Direct integration with agent runtimes that can execute prompt bundles.
- Richer packet schema migrations.
