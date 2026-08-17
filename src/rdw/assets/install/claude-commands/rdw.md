---
name: rdw
description: Research-grounded domain writing — research, grounded draft, QA, then humanizer (not style-only)
argument-hint: <task> | domain=<d> entity=<name> output-type=<t> depth=light|standard|deep|minimal packet-id=<id>
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
Run one **research-domain-writing** task end-to-end using the lane selected by
the resolved contract: full pipeline or lightweight research card → grounded
draft → QA → humanizer/blader.

**The skill instructs; you research** (browser, files, APIs). The full lane
uses YAML packets under `knowledge/`; the lightweight lane uses a run-local
research card. Full-lane diff-QA compares the candidate against the approved
packet; lightweight diff-QA compares it against the explicit draft claim
ledger. Humanizer must not add facts.
</objective>

<paths>
Set `RDW_ROOT` to: **__RDW_ROOT__**

All paths below are relative to `RDW_ROOT` unless absolute.
</paths>

<files_to_read>
1. __RDW_ROOT__/SKILL.md
2. __RDW_ROOT__/prompts/pipeline-orchestrator.md or
   __RDW_ROOT__/prompts/lightweight-orchestrator.md, as selected by the plan
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

RDW orchestrates local research and artifact work; it does not send, upload,
submit, publish, or deploy anything externally. Human review remains required
before any consequential use of the output.
</inference>

<process>
1. Read `<files_to_read>` plus `config/router-inference.yaml`.
2. **Router first** — emit inferred contract; show user a short table; then continue.
3. Execute the orchestrator named by the prompt bundle — do not skip QA before humanizer.
4. **Research:** follow the selected lane; the lightweight lane saves only a run-local card.
5. Write artifacts to `outputs/drafts/`, `outputs/qa/`, `outputs/final/`.
6. Require QA and passing lane-appropriate diff-QA before humanizer; report
   `output_id`, `confidence_level`, `needs_review`, and paths to final copy,
   evidence, and diff-QA artifacts.
</process>

<subcommands>
- If `$ARGUMENTS` is `help` or empty: print usage from __RDW_ROOT__/README.md#single-task--how-to-run
- If `$ARGUMENTS` starts with `batch`: tell user to run `/rdw-batch` instead
</subcommands>
