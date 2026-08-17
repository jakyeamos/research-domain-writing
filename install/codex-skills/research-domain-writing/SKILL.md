---
name: rdw
description: Research-grounded domain writing — agent researches, then draft, QA, humanizer. Full or lightweight lane. Slash /rdw.
---

# Research domain writing (Codex)

**Root:** `__RDW_ROOT__`

Invoke when the user runs `/rdw` or asks for grounded domain copy.

## Steps

1. Read `SKILL.md` and the orchestrator named by the task contract under root.
2. Agent performs the selected research pass; the full lane saves a reusable
   packet and packet diff-QA report, while the lightweight lane saves a
   run-local card and explicit draft-ledger diff-QA report.
3. Grounded copywriter → QA → passing diff-QA → humanizer; no new facts in
   humanizer.
4. For batch, use `rdw batch plan` to create task bundles, then follow
   `prompts/batch-runner.md`. The optional `rdw batch execute --fixture-map`
   command is a deterministic integration seam, not a model or research runner.

This skill creates local artifacts only. It does not send, upload, submit,
publish, or deploy externally. Human review remains mandatory before
consequential use.
