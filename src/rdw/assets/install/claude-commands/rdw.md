---
name: rdw
description: Research-grounded domain writing — research, grounded draft, QA, then humanizer (not style-only)
argument-hint: <task> | domain=<d> entity=<name> output-type=<t> depth=light|standard|deep packet-id=<id>
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - WebSearch
  - WebFetch
---

<objective>
Run one **research-domain-writing** task end-to-end: router → research (agent-gathered) → knowledge packet → copywriter → QA → humanizer/blader.

**The skill instructs; you research** (browser, files, APIs). Grounding lives in YAML packets under `knowledge/`. Humanizer must not add facts.
</objective>

<paths>
Set `RDW_ROOT` to: **__RDW_ROOT__**

All paths below are relative to `RDW_ROOT` unless absolute.
</paths>

<files_to_read>
1. __RDW_ROOT__/SKILL.md
2. __RDW_ROOT__/prompts/pipeline-orchestrator.md
3. __RDW_ROOT__/config/style-profile.yaml
4. __RDW_ROOT__/docs/LIMITATIONS.md
</files_to_read>

<context>
$ARGUMENTS
</context>

<inference>
**Default: infer the full task contract from the user's words.** Read `config/router-inference.yaml` and run `prompts/domain-router.md`.

Only parse `key=value` when the user supplies them — overrides beat inference.

Do **not** ask the user to fill domain/entity/output-type/audience/depth unless inference confidence is low or they object to your summary.

Example: "improve the copy on my LIS leaderboard" → basketball, entity `LIS leaderboard`, `ranking_explanation`, fantasy/analytics audience, `standard` depth.

RDW orchestrates the pipeline; the agent uses normal tools for research and deployment. RDW does not need to publish to production.
</inference>

<process>
1. Read `<files_to_read>` plus `config/router-inference.yaml`.
2. **Router first** — emit inferred contract; show user a short table; then continue.
3. Execute `prompts/pipeline-orchestrator.md` — do not skip QA before humanizer.
3. **Research:** run planner + researcher; use your tools; save/update packets under `knowledge/<domain>/`.
4. Write artifacts to `outputs/drafts/`, `outputs/qa/`, `outputs/final/`.
5. Report: `output_id`, `confidence_level`, `needs_review`, paths to final copy and packet.
</process>

<subcommands>
- If `$ARGUMENTS` is `help` or empty: print usage from __RDW_ROOT__/README.md#single-task--how-to-run
- If `$ARGUMENTS` starts with `batch`: tell user to run `/rdw-batch` instead
</subcommands>
