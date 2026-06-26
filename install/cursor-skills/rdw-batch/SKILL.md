---
name: rdw-batch
description: >-
  Batch run of research-domain-writing tasks from YAML (examples/batch-tasks.yaml).
  Reuses knowledge packets, tiered research depth, logs needs_review. Explicit /rdw-batch only.
disable-model-invocation: true
---

# /rdw-batch

**Root:** `__RDW_ROOT__`

1. Read `prompts/batch-runner.md` and the batch YAML (user path or `examples/batch-tasks.yaml`).
2. For each task, run the full rdw pipeline.
3. Append `outputs/batch-log.jsonl` per task.
4. Summarize completed vs needs_review.
