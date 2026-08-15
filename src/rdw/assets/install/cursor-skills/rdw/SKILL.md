---
name: rdw
description: >-
  Research-grounded domain writing pipeline (sports analytics, music criticism,
  technical copy, policy, etc.). Agent researches per skill instructions; then
  grounded draft, domain QA, humanizer. Use when /rdw or domain-specific copy
  must be factual. Not for style-only polish — use humanizer alone for that.
disable-model-invocation: true
---

# /rdw — Research domain writing

**Root:** `__RDW_ROOT__`

## On invoke

1. Read `__RDW_ROOT__/SKILL.md`, `config/router-inference.yaml`, and
   `prompts/domain-router.md`. Read the full or lightweight orchestrator named
   by the task plan.
2. **Infer** domain, entity, output_type, audience, depth from the user's message (`key=value` only if they provide overrides).
3. Show inferred contract briefly; proceed unless they correct you.
4. Run the selected lane. **You research** (tools/browser/files); the full lane
   structures reusable packets and packet diff-QA; the lightweight lane
   structures a run-local card and explicit draft-ledger diff-QA.
5. Do not humanize before QA passes.
6. Save outputs under `__RDW_ROOT__/outputs/` and report QA/diff-QA paths.

The task produces local artifacts only. It must not send, upload, submit,
publish, or deploy externally; human review remains mandatory before
consequential use.

RDW is not omnipotent — it does not replace your repo tools or deploy copy; it produces grounded artifacts you apply.

## User message (minimal)

```
improve the copy on my LIS leaderboard
```

No other fields required.

## Also

- Batch: use skill `rdw-batch` or `/rdw-batch`
- Docs: `__RDW_ROOT__/README.md`
