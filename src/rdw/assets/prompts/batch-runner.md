# Batch Runner

Process many writing tasks with reuse and tiered research.

## Deterministic core boundary

`rdw batch plan <batch.yaml>` validates the batch, expands deterministic per-task prompt bundles, and writes initial `planned` statuses. It does not execute research, drafting, QA, humanizer, or model calls.

The serial fixture executor is available for deterministic integration checks. It
stages checked-in or user-provided fixture receipts and artifacts; it does not
call a model, browse, conduct research, or replace the agent-led pipeline.

```bash
rdw batch execute <run-dir> \
  --fixture-map <fixture-map.yaml> \
  --root <repository-root>
rdw batch pause <run-dir>
rdw batch cancel <run-dir>
```

The fixture map must cover every planned task and keeps the batch provider-neutral:

```yaml
batch_id: demo-batch-001
execution:
  max_concurrency: 1
  max_attempts: 2
  retry_backoff_seconds: [5, 30]
  failure_policy: continue
fixtures:
  task-id: examples/fixtures/task-outcome.yaml
```

For real writing work, execute each planned task by following the lane named in
its prompt bundle. Update task status and append log lines as work moves beyond
`planned`.

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

## Per-task lanes

Full lane (`standard` or `deep`):

1. Router → Planner
2. If a packet exists, reuse it only when the planner confirms it is current
   and its required fields cover the task; otherwise research the declared gaps
3. Researcher (if needed) → Knowledge packet builder
4. Copywriter → QA → deterministic diff-QA → (loop rev1 if blockers) → Humanizer
5. Save final + append/update batch log

Lightweight lane:

1. Router → Planner → run-local research card
2. Grounded copywriter → compact QA
3. Deterministic diff-QA; missing ledgers or baselines remain review-required
4. Humanizer only after QA and diff-QA pass
5. Save final, artifact receipt when required, and append/update batch log

The planner maps `light` and `minimal` to the lightweight lane. Do not send
those tiers through the full-lane planner or treat them as a lower-cost full
research pass.

## Batch outputs

```
<run-dir>/
  summary.yaml        # lifecycle and executor projections
  batch-log.jsonl     # append-only lifecycle/executor events
  executor-lease.json  # short-lived one-writer lease while executing
  tasks/<task_id>/    # task contract, prompt bundle, status
```

## Logging

Each line in batch-log:

```json
{"task_id","domain","status","confidence_level","needs_review","diff_qa_status","diff_qa_codes":[],"missing_info":[]}
```

Executor events additionally carry an `event_id`, `event_type`, executor state,
attempt number, and receipt or failure fields. Duplicate executor event IDs are
ignored when projections are replayed. `rdw batch resume` remains a read-only
next-task view; use `rdw batch execute --resume` to continue a paused or
reviewed fixture batch.

## Rules

- Do not parallelize research that updates same packet id without merge discipline
- Completed ≠ reviewed: flag tier-1 outputs for human review by default
