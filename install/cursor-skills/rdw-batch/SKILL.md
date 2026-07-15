---
name: rdw-batch
description: >-
  Batch plan and execution guide for research-domain-writing tasks from YAML.
  rdw batch plan validates and expands prompt bundles; the agent executes tasks.
  The optional fixture executor is only a deterministic integration seam.
disable-model-invocation: true
---

# /rdw-batch

**Root:** `__RDW_ROOT__`

1. Run `rdw batch plan <batch-yaml>` when the CLI is available; otherwise read the batch YAML (user path or `examples/batch-tasks.yaml`).
2. Read `prompts/batch-runner.md`.
3. For each planned task, run the full RDW pipeline.
4. Update status/log artifacts and summarize completed vs needs_review.

For fixture-only verification, use `rdw batch execute <run-dir>
--fixture-map <map.yaml> --root <repo>`. It does not call models, browse, or
replace the agent-led pipeline.
