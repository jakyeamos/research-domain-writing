# Batch Runner

Process many writing tasks with reuse and tiered research.

## v0.1 constraint

`rdw batch plan <batch.yaml>` validates the batch, expands deterministic per-task prompt bundles, and writes initial `planned` statuses. It does not execute research, drafting, QA, humanizer, or model calls.

Execute each planned task by running the full pipeline in this agent session. Update task status and append log lines as work moves beyond `planned`.

## Inputs

- Batch file: `examples/batch-tasks.yaml` or user-provided YAML list

```yaml
batch_id: string
defaults:
  research_depth: standard
  output_format: markdown
tasks:
  - task_id: string
    request: string
    domain: optional
    entity_name: string
    output_type: string
    research_depth: optional  # override tier 1-4
    packet_id: optional       # skip research if fresh
```

## Research depth tiers (batch)

| Tier | Name | Behavior |
|------|------|----------|
| 1 | deep | Full planner + researcher + human_review_default |
| 2 | standard | Normal pipeline |
| 3 | light | Minimal new research; reuse packets aggressively |
| 4 | minimal | Write only from existing packet; explicit thin-evidence warnings |

## Per-task pipeline

1. Router → Planner
2. If packet exists and tier ≥ 3: skip research unless planner flags gaps
3. Researcher (if needed)
4. Knowledge packet builder
5. Copywriter → QA → (loop rev1 if blockers) → Humanizer
6. Save final + append/update batch log

## Batch outputs

```
<run-dir>/
  summary.yaml        # counts: completed, needs_review, failed
  batch-log.jsonl     # append-only status events
  tasks/<task_id>/    # task contract, prompt bundle, status
```

## Logging

Each line in batch-log:

```json
{"task_id","domain","status","confidence_level","needs_review","missing_info":[]}
```

## Rules

- Do not parallelize research that updates same packet id without merge discipline
- Completed ≠ reviewed: flag tier-1 outputs for human review by default
