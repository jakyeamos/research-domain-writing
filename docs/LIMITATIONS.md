# Scope: limitations vs design

## Research (by design — not a gap)

**The skill does not perform research itself. The agent does**, following `prompts/research-planner.md` and `prompts/researcher.md`.

That means:

- The agent may use whatever tools it already has (browser, APIs, pasted stats, local files, notebooks).
- The skill’s job is to **structure, save, and reuse** what was gathered — YAML packets, `source_notes`, uncertainty, concept bank updates.
- There is **no built-in fetch layer** inside this repo (no crawlers, no domain API adapters shipped here). That is intentional: research stays in the agent layer; grounding stays in files.

`config/research-sources.yaml` tells the agent what kinds of sources to prefer, not what to call automatically.

**If research feels weak**, fix the agent step (better sources, deeper planner tier), not by bolting web crawl into the skill package.

---

## Batch (v1 limitation — CLI has merit)

**Batch is prompt-driven (no dedicated CLI runner yet).**

- Multi-task runs follow `prompts/batch-runner.md` inside an agent session.
- `examples/batch-tasks.yaml` is the task list format; there is no `rdw batch` (or similar) that runs the pipeline end-to-end with stable exit codes and logging.
- `outputs/batch-log.jsonl` is append-only — agents write lines after each task.

**Why a CLI would help:** repeatable runs, tier flags, resume failed tasks, review queues — without re-explaining the pipeline in chat each time. The prompts stay the source of truth; the CLI would orchestrate them.

---

## Workarounds (until batch CLI exists)

| Need | v1 approach |
|------|-------------|
| Live stats / docs | Agent researches per researcher prompt; save to `knowledge/<domain>/` |
| Repeatable batch | Agent loops `batch-runner.md`; or wrap stages in your own shell script |
| Validate packets | `scripts/validate-packet.py` (optional PyYAML) |

See README **What still needs improvement** for the roadmap (batch CLI first).
