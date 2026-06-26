# Research Domain Writing

A standalone, file-based pipeline that turns **research → grounded domain copy → QA → human style pass**. It upgrades a humanizer/blader workflow from “sound natural” to “be correct *and* sound natural.”

## Problem

Humanizer/blader skills fix AI rhythm and voice. They should **not** carry domain knowledge. In jargon-heavy domains (sports analytics, music criticism, technical writing, law, finance, medicine, academia), fluent generic copy often:

- uses wrong jargon or decorative jargon
- flattens nuance and role context
- invents stats, citations, or reception history
- overstates claims from thin evidence

## Principle

| Layer | Responsibility |
|-------|----------------|
| Research | Facts, sources, uncertainty, terminology |
| Domain copywriter | Structured, grounded draft |
| Domain QA | Grounding, jargon, overclaiming |
| Humanizer/blader | Style, rhythm, author voice **only** |

**Knowledge generation and style transformation are separate.**

## What’s in the box

```
research-domain-writing/
  README.md
  SKILL.md                 # Agent skill entrypoint
  config/                  # domains registry, style, sources, formats
  domains/                 # Domain packs (template + examples)
  knowledge/               # Persistent research packets (YAML)
  prompts/                 # Stage prompts + orchestrator
  outputs/                 # drafts, final, qa, research
  examples/                # End-to-end samples
  scripts/                 # validate-packet, new-domain scaffold
  docs/LIMITATIONS.md          # research model (agent) vs v1 gap (batch CLI)
  docs/FUTURE-AIOS-INTEGRATION.md
```

Starter domain packs (examples, not core identity):

- **basketball** — player/stat copy
- **music** — criticism blurbs
- **technical** — product/feature explainers

Any domain can be added via config + pack folder without changing core prompts.

## Research model

**The skill instructs; the agent researches.** Planner and researcher prompts define what to gather and how to save it. The agent may use browser tools, APIs, exports, or pasted material — this package does not ship its own fetch layer. Grounding lives in `knowledge/<domain>/*.yaml` with `source_notes` and explicit uncertainty.

See `docs/LIMITATIONS.md`.

## Current limitation (v1)

- **Batch is prompt-driven** — no dedicated CLI runner yet. Use `prompts/batch-runner.md` with an agent and `examples/batch-tasks.yaml`. A small CLI for batch orchestration is the main planned mechanical upgrade.

## Pipeline (10 steps)

1. Identify domain and writing task (**router**)
2. Retrieve local knowledge (`knowledge/<domain>/`)
3. Plan missing research (**research planner**)
4. Research gaps (**researcher** → update packet)
5. Save structured research packet (YAML)
6. Build task-specific knowledge packet (**builder**)
7. Write analytical draft (**domain copywriter**)
8. Run domain QA (**domain QA**)
9. Humanizer/blader style pass (**humanizer/blader**)
10. Save final output + QA notes + research artifacts

See `prompts/pipeline-orchestrator.md` for agent execution order.

## Slash commands (Claude / Cursor / Codex)

From this directory:

```bash
chmod +x install/install.sh
./install/install.sh
```

| Command | Purpose |
|---------|---------|
| `/rdw` | One writing task — full pipeline |
| `/rdw-batch` | Many tasks from `examples/batch-tasks.yaml` or a path you pass |

**Claude Code** installs `~/.claude/commands/rdw.md` and links `~/.claude/skills/research-domain-writing` → this folder.

**Cursor** installs `~/.cursor/skills/rdw/` and `rdw-batch/` (and project `.cursor/skills/` when run from AIOS).

**Codex / agents** links `~/.agents/skills/research-domain-writing` → this folder.

Restart the IDE or start a new session if `/rdw` does not appear in the slash menu.

Natural language is enough — the router infers domain, entity, output type, audience, and depth:

```text
/rdw improve the copy on my LIS leaderboard
```

Override only when needed:

```text
/rdw improve LIS leaderboard copy depth=deep
```

## Single task — how to run

### With an AI agent (recommended)

Install slash commands (above) or reference `SKILL.md`, then send:

```text
Run research-domain-writing pipeline.

Task: Explain why TS% matters for Brunson's 2024-25 usage profile; note skeptic angles.
Domain: basketball
Entity: Jalen Brunson
Output type: stat_interpretation
Audience: analytics-literate fans
Research depth: standard
Packet id: basketball-player-jalen-brunson-2024-25
```

The agent should load prompts in order and write artifacts under `outputs/`.

### Manual / step-by-step

1. Run router logic using `prompts/domain-router.md` + `config/domains.yaml`
2. If needed, planner → researcher; save packet to `knowledge/<domain>/<id>.yaml`
3. Build knowledge packet → draft → QA → final humanizer pass
4. Compare with `examples/basketball-example/` for expected artifact shapes

Validate a packet:

```bash
uv run python scripts/validate-packet.py knowledge/basketball/jalen-brunson-2024-25.yaml
# or: python3 scripts/validate-packet.py ...  (requires PyYAML)
```

## Batch writing

Use `examples/batch-tasks.yaml` as a template. Follow `prompts/batch-runner.md`.

| Tier | Use when |
|------|----------|
| 1 deep | Controversial, high-stakes, central claims |
| 2 standard | Normal outputs |
| 3 light | Short blurbs; reuse packets |
| 4 minimal | Packet-only; explicit thin-evidence warnings |

Batch outputs log to `outputs/batch-log.jsonl` (schema in `config/output-formats.yaml`). Low-confidence and `needs_review` tasks should land in a review queue, not silent publish.

## Research storage & reuse

- **Location:** `knowledge/<domain>/<packet-id>.yaml`
- **Schema:** `domains/_template/research-packet-template.yaml` + domain `extensions`
- **Reuse:** Router/planner checks `id` + `last_updated` + `used_in_outputs`
- **Updates:** Researcher updates same `id` instead of duplicating
- **Unknowns:** Use `unknown` — never hallucinate missing fields

Concept/jargon banks (`domains/<domain>/concepts/`, `jargon/`) accumulate reusable definitions; research packets reference them via `concepts_that_apply`.

## Humanizer / blader interaction

- Runs **only after** QA pass
- Reads `config/style-profile.yaml` for voice (independent of domain)
- Must preserve claims, metrics, caveats, and domain terms
- External [humanizer](https://github.com/) skill patterns apply for anti-AI rhythm, but **must obey** `prompts/humanizer-blader.md` constraints (no new facts)

If copy needs new facts → go back to researcher, not humanizer.

## Uncertainty & missing information

- Planner emits `must_not_claim` and `uncertainty_requirements`
- Copywriter hedges when `confidence_level` is medium/low
- QA flags overclaiming and dropped caveats
- Open questions stay in packet; may surface as limits in copy, not as invented answers

## Output formats

Configured in `config/output-formats.yaml`: **Markdown** (default), **JSON**, **YAML**.

Final metadata should include:

`output_id`, `domain`, `entity`, `output_type`, `final_copy`, `research_packet_ids_used`, `concepts_used`, `confidence_level`, `generated_at`, `warnings`, `needs_review`

## Add a new domain

```bash
chmod +x scripts/new-domain.sh
./scripts/new-domain.sh finance "Finance Writing"
```

Then:

1. Edit `domains/finance/domain-config.yaml` (entity types, forbidden phrases, extensions)
2. Customize `research-packet-template.yaml`, `qa-checklist.md`, `writing-templates.md`
3. Add concepts/jargon under `domains/finance/concepts/` and `jargon/`
4. Register in `config/domains.yaml` (`enabled: true`, paths)
5. Add source rules in `config/research-sources.yaml`
6. Store packets in `knowledge/finance/`

No core prompt edits required.

## Style profile

`config/style-profile.yaml` — author voice only. Copy to `style-profile-jakye.yaml` (or per-publication) and point the orchestrator at it. Domain packs handle knowledge; style profile handles tone, rhythm, and “sounds like me.”

## Examples

| Example | Path |
|---------|------|
| Basketball stat interpretation | `examples/basketball-example/` |
| Music blurb (thin evidence demo) | `examples/music-example/` |
| Technical feature explainer | `examples/technical-example/` |
| Batch task list | `examples/batch-tasks.yaml` |

Sample research packet: `knowledge/basketball/jalen-brunson-2024-25.yaml`

## Quality bar

Target feel: **research assistant + domain analyst + editor + humanizer**

Not: generic AI writer with jargon sprinkled on top.

## Future AIOS integration

See `docs/FUTURE-AIOS-INTEGRATION.md`. v1 deliberately avoids AIOS memory, registry, and workflows.

## What still needs improvement

- Dedicated batch CLI runner (orchestrate existing prompts + `batch-tasks.yaml` + `batch-log.jsonl`) *(see `docs/LIMITATIONS.md`)*
- Packet merge/conflict resolution for concurrent updates
- Stronger JSON-schema validation (optional PyYAML validator included)
- Dedicated packs for legal, finance, medicine (folders exist; use template)
- Diff-based regression tests on QA rules

## License

Use and adapt within your projects; basketball/music/technical packs are illustrative starters.
