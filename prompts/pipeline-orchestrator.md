# Pipeline Orchestrator (Single Task)

Run the full research-domain-writing pipeline for one task.

## Research & batch

- **Research:** agent executes `researcher.md` (may use any tools); skill saves structured packets (`docs/LIMITATIONS.md`).
- **Batch (v0.1):** `rdw batch plan <batch.yaml>` creates task bundles; agent follows `prompts/batch-runner.md` to execute them.

## Load order

1. `config/domains.yaml`, `config/router-inference.yaml`, `config/style-profile.yaml`, `config/output-formats.yaml`
2. `prompts/domain-router.md` → router output (**infer** domain, entity, output_type, audience, depth from user text if omitted)
3. Present inferred contract to user; proceed without requiring `key=value` args
3. If research needed: `prompts/research-planner.md` → `prompts/researcher.md`
4. `prompts/knowledge-packet-builder.md`
5. `prompts/domain-copywriter.md`
6. `prompts/domain-qa.md` — if fail with blockers, loop copywriter once
7. `prompts/humanizer-blader.md`
8. Save artifacts per `config/output-formats.yaml`

## Artifact map

| Stage | Path |
|-------|------|
| Research packet | `knowledge/<domain>/<id>.yaml` |
| Knowledge packet | `outputs/research/<task_id>-knowledge.md` |
| Draft | `outputs/drafts/<output_id>.md` |
| QA | `outputs/qa/<output_id>-qa.yaml` |
| Final | `outputs/final/<output_id>.md` |

## Principle

**Knowledge stages may add facts. Humanizer may not.**

## User invocation (agent)

Provide in one message:

```
Task: <writing request>
Domain (optional): <domain>
Entity: <name>
Output type: <type>
Audience: <audience>
Research depth: light|standard|deep
Existing packet (optional): <packet_id>
```

Then execute orchestrator steps in order without skipping QA before humanizer.
