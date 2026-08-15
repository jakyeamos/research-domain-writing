# Pipeline Orchestrator (Single Task)

Run the full research-domain-writing pipeline for one task.

## Research & batch

- **Research:** agent executes `researcher.md` (may use any tools); skill saves structured packets (`docs/LIMITATIONS.md`).
- **Batch (v0.1):** `rdw batch plan <batch.yaml>` creates task bundles; agent follows `prompts/batch-runner.md` to execute them.

## Load order

1. `config/domains.yaml`, `config/router-inference.yaml`, `config/style-profile.yaml`, `config/output-formats.yaml`, `config/artifacts.yaml`
2. `prompts/domain-router.md` → router output (**infer** domain, entity, output_type, audience, depth from user text if omitted)
3. Present inferred contract to user; proceed without requiring `key=value` args
4. If research needed: `prompts/research-planner.md` → `prompts/researcher.md`
5. `prompts/knowledge-packet-builder.md`
6. `prompts/domain-copywriter.md`
7. `prompts/domain-qa.md` — if fail with blockers, loop copywriter once
8. `prompts/diff-qa.md` — compare the structured candidate to the approved
   baseline in the contract's packet mode; stop on `fail` or `indeterminate`
9. `prompts/humanizer-blader.md` — style only after diff-QA passes
10. Save artifacts per `config/output-formats.yaml`
11. For externally consumed writing, create an artifact request with evidence and
   claim bindings, run `rdw validate-artifact`, and stop on a blocked receipt.
   A passing receipt advances only to human review.

## Artifact map

| Stage | Path |
|-------|------|
| Research packet | `knowledge/<domain>/<id>.yaml` |
| Knowledge packet | `outputs/research/<task_id>-knowledge.md` |
| Draft | `outputs/drafts/<output_id>.md` |
| QA | `outputs/qa/<output_id>-qa.yaml` |
| Diff-QA | `outputs/qa/<output_id>-diff.yaml` |
| Final | `outputs/final/<output_id>.md` |
| Approved baseline / draft ledger | Contract-configured local paths |
| Artifact receipt | next to the consuming artifact or in its governed run directory |

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
Research depth: standard|deep
Existing packet (optional): <packet_id>
```

Then execute orchestrator steps in order without skipping domain QA or
diff-QA before humanizer. A missing baseline or draft claim ledger is a hard
stop, not an invitation to infer approval.
