# Batch Runner

Process many writing tasks with reuse and tiered research.

## v1 constraint

**Batch is prompt-driven (no dedicated CLI runner yet).** Execute each task by running the full pipeline in this agent session. Append results to `outputs/batch-log.jsonl` manually; there is no `rdw batch` executable.

## Inputs

- Batch file: `examples/batch-tasks.yaml` or user-provided YAML/JSON list

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
6. Save final + append `outputs/batch-log.jsonl`

## Batch outputs

```
outputs/batch/{batch_id}/
  summary.yaml        # counts: completed, needs_review, failed
  needs-review/       # low confidence or QA fail
  completed/
```

## Logging

Each line in batch-log:

```json
{"task_id","domain","status","confidence_level","needs_review","missing_info":[]}
```

## Rules

- Do not parallelize research that updates same packet id without merge discipline
- Completed ≠ reviewed: flag tier-1 outputs for human review by default
