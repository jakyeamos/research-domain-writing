---
name: rdw-batch
description: Batch research-domain-writing tasks from a YAML task list (prompt-driven orchestration)
argument-hint: [path/to/batch-tasks.yaml] | tier=1|2|3|4
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
Run multiple research-domain-writing tasks from a batch file. Reuse existing packets; log low-confidence outputs; separate `needs_review`.
</objective>

<paths>
`RDW_ROOT`: **__RDW_ROOT__**
</paths>

<files_to_read>
1. __RDW_ROOT__/SKILL.md
2. __RDW_ROOT__/prompts/batch-runner.md
3. __RDW_ROOT__/docs/LIMITATIONS.md
</files_to_read>

<context>
$ARGUMENTS

Defaults:
- Batch file: `__RDW_ROOT__/examples/batch-tasks.yaml` if no path given
- Append each task result to `__RDW_ROOT__/outputs/batch-log.jsonl`
</context>

<process>
1. Read batch file YAML.
2. Follow `prompts/batch-runner.md` for each task (full pipeline per task).
3. After batch, write summary counts: completed, needs_review, failed.
</process>
