---
name: research-domain-writing
description: |
  Research-grounded domain writing pipeline. Use when producing jargon-heavy or
  knowledge-heavy copy (sports analytics, music criticism, technical writing, policy,
  finance, medicine, academic, etc.). Separates research, domain drafting, QA, and
  final humanizer/blader style pass. Do NOT use humanizer alone for domain knowledge.
  Slash commands: /rdw (single task), /rdw-batch (YAML batch).
version: 0.1.0
---

# Research Domain Writing

## When to use

- User wants **accurate, domain-specific** copy, not generic fluent AI prose
- Task needs local research packets, concept/jargon banks, or QA before styling
- User mentions: player writeups, stat interpretation, album blurbs, feature docs, policy memos
- User already has a humanizer skill but writing keeps sounding shallow or wrong

## When NOT to use

- Pure style polish on already-correct text → use `humanizer` only
- Fiction/creative writing without factual grounding requirements

## Research (you do this; skill structures it)

Run planner + researcher prompts. **Use your tools** (web, files, APIs) to gather facts; save YAML under `knowledge/<domain>/`. The skill does not include a built-in crawler — that is by design.

## v0.1 limitation

- `rdw task plan` and `rdw batch plan` validate inputs and emit deterministic prompt bundles.
- The CLI does not call an LLM, browse, research, draft, or complete batch tasks by itself.
- The agent executes the emitted prompts and updates run artifacts.

Details: `docs/LIMITATIONS.md`

## Pipeline (do not skip steps)

1. **Router** — `prompts/domain-router.md`
2. **Research planner** — `prompts/research-planner.md` (skip only if fresh packet exists)
3. **Researcher** — `prompts/researcher.md` → save `knowledge/<domain>/*.yaml`
4. **Knowledge packet builder** — `prompts/knowledge-packet-builder.md`
5. **Domain copywriter** — `prompts/domain-copywriter.md` → `outputs/drafts/`
6. **Domain QA** — `prompts/domain-qa.md` → must pass before step 7
7. **Humanizer/blader** — `prompts/humanizer-blader.md` → `outputs/final/`

Orchestration: `prompts/pipeline-orchestrator.md`  
Batch: `prompts/batch-runner.md`

## Hard rule

**Humanizer/blader never adds facts.** If QA fails or packet is thin, return to research/copywriter.

## Slash commands

After `rdw install --target all` or source checkout `./install/install.sh`:

| Tool | Command |
|------|---------|
| Claude Code | `/rdw`, `/rdw-batch` |
| Cursor | `/rdw`, `/rdw-batch` (skills with `disable-model-invocation`) |
| Codex / agents | `/rdw` or skill `research-domain-writing` |

## Natural language (preferred)

Pass one sentence. Router infers the rest (`config/router-inference.yaml`):

```
/rdw improve the copy on my LIS leaderboard
```

→ domain `basketball`, entity `LIS leaderboard`, `ranking_explanation`, fantasy/analytics audience, depth `standard`. Agent shows the contract and proceeds.

Overrides optional: `domain=`, `entity=`, `output-type=`, `audience=`, `depth=`, `packet-id=`.

**RDW is not omnipotent** — it orchestrates research → draft → QA → style. You research with normal tools; you ship copy to your app.

Load `config/style-profile.yaml` for voice.

## Add a domain

```bash
rdw new-domain my-domain "My Domain"
```

Edit `domains/my-domain/`, register in `config/domains.yaml`, store packets in `knowledge/my-domain/`.

## References

- Full docs: `README.md`
- Examples: `examples/basketball-example/`, `examples/music-example/`, `examples/technical-example/`
- v1 limits: `docs/LIMITATIONS.md`
- Future AIOS hook: `docs/FUTURE-AIOS-INTEGRATION.md`
