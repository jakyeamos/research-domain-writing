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

The CLI does not call an LLM, browse the web, conduct autonomous research, or write final copy in v0.1.

## Batch

`rdw batch plan` is not an autonomous batch writer. It validates and expands tasks so an agent can execute them consistently.

Each planned task starts at status `planned`. The agent or a future adapter is responsible for moving tasks through research, draft, QA, final, and review states.

## Workarounds

| Need | v0.1 approach |
| --- | --- |
| Live stats or docs | Agent researches and saves packets under `knowledge/<domain>/` |
| Repeatable single task | `rdw task plan ... --out <run-dir>` |
| Repeatable batch setup | `rdw batch plan <batch.yaml> --out <run-dir>` |
| Agent slash command | `rdw install --target all` |

## Future upgrades

- Optional adapters for specific research sources.
- Resume and status update commands for planned runs.
- Direct integration with agent runtimes that can execute prompt bundles.
- Richer packet schema migrations.
