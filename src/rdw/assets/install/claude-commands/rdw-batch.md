---
name: rdw-batch
description: Batch research-domain-writing tasks from a YAML task list (planned by rdw; executed by agent)
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
Plan and then execute multiple research-domain-writing tasks from a batch file. `rdw batch plan` validates and expands prompt bundles; the agent performs research, drafting, QA, and final output.
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

Default batch file: `__RDW_ROOT__/examples/batch-tasks.yaml` if no path is given.
</context>

<process>
1. Run `rdw batch plan <batch-file>` when the CLI is available; otherwise read the batch YAML directly.
2. Read `prompts/batch-runner.md`.
3. Execute each planned task through the full RDW pipeline.
4. Update task status/log artifacts and summarize completed vs needs_review.
</process>
