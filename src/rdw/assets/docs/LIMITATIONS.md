# Scope: limitations vs design

## Research

RDW does not perform research by itself. The agent does the research by following `prompts/research-planner.md` and `prompts/researcher.md`.

That means:

- The agent may use whatever tools it already has: browser, APIs, pasted stats, local files, notebooks, or user-provided material.
- RDW structures, validates, saves, and reuses what was gathered.
- There is no built-in crawler, live stats connector, publication database client, or model API runner in the current `v0.2.2` release.

`config/research-sources.yaml` tells the agent what kinds of sources to prefer. It is not an automatic fetch configuration.

## CLI

The `rdw` CLI is a deterministic planning and validation harness:

- `rdw validate-packet` validates research packets.
- `rdw validate-packet --mature` applies the opt-in basketball acceptance gates.
- `rdw validate-claim-ledger` validates QA issue counts and packet fact traceability.
- `rdw validate-batch` validates batch YAML.
- `rdw validate-artifact` validates a caller-supplied artifact request and emits
  a content-bound quality receipt. It does not research or draft the content.
- `rdw task plan` writes a task contract, prompt bundle, and initial status file.
- `rdw task plan` selects a full pipeline or lightweight research-card lane;
  both are agent-executed prompt bundles, not autonomous model runs.
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
- `rdw diff-qa` performs the ADR-003 deterministic comparison for packet mode
  or explicit draft-claim-ledger mode. Full-lane contracts select packet mode;
  lightweight contracts select draft mode. It requires an approved,
  hash-pinned local baseline and emits `outputs/qa/<output_id>-diff.yaml` when
  requested.
- `rdw schema` exports JSON Schemas for packets, batches, task contracts,
  approved diff baselines, draft claim ledgers, diff-QA reports, artifact
  requests, and artifact receipts.
- `rdw adapter` exposes optional provider-neutral runtime stubs plus the local
  `fixture` adapter used by the single-task vertical-slice prototype.

The CLI does not call an LLM, browse the web, conduct autonomous research, or write final copy.
An artifact receipt is deterministic QA evidence only. Even
`approved_for_human_review` does not authorize sending, submission, publication,
or a factual claim that the supplied evidence does not actually support.

The lightweight lane is intentionally agent-led and run-local: the CLI does not
validate a research-card schema or execute its compact QA. The checked-in
fixture executor currently proves the full vertical slice only; it is not a
lightweight-lane executor.

The artifact validator verifies that every supplied claim binding is
well-formed, references known evidence, and is represented in the submitted
body. The ADR-003 diff-QA gate now closes the structured regression boundary:
packet facts/metrics, source links, uncertainty, rules, or explicit draft claim
ledgers are compared deterministically against an approved baseline. It still
cannot prove that a dishonest ledger faithfully represents every sentence of
freeform Markdown; draft mode therefore never extracts claims from Markdown,
and a missing or malformed ledger is indeterminate rather than a pass.

The lifecycle recorder does not infer stage completion from arbitrary artifact
contents, does not require an external artifact receipt before `final-done`,
and does not record human approval as a terminal state. It does require a
structurally valid passing diff-QA report before `qa-passed` or `final-done`
when the task contract enables the gate. Minor-only findings may pass with a
review flag; fail and indeterminate reports remain blocked. The fixture
executor validates packet structure, artifact hashes, QA, and diff-QA outcome,
but does not prove that a final Markdown rewrite is semantically identical to
the draft unless that change is represented by the explicit ledger. Therefore
`final-done` is still only an operational completion marker—not permission to
send, submit, publish, upload, or skip mandatory human review.

## Batch

`rdw batch plan` is not an autonomous batch writer. It validates and expands
tasks so an agent can execute them consistently. The fixture-backed executor is
only a deterministic integration seam for planned batches; it does not replace
the agent-led research, drafting, QA, or humanizer pipeline.

Each planned task starts at status `planned`. The agent or a future adapter is responsible for moving tasks through research, draft, QA, final, and review states.

## Workarounds

| Need | v0.2.2 approach |
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
| Consequential writing gate | `rdw validate-artifact <request> --receipt <receipt> --json` |
| Structured regression gate | `rdw diff-qa <baseline> <candidate> --root <root> --output <report>` |
| Agent slash command | `rdw install --target all` |

## Future upgrades

- Real provider adapters that call external APIs (provider stubs exist today).
- Direct integration with agent runtimes that can execute prompt bundles.
- Richer packet schema migrations.
