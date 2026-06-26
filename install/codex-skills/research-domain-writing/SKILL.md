---
name: rdw
description: Research-grounded domain writing — agent researches, then draft, QA, humanizer. Slash /rdw.
---

# Research domain writing (Codex)

**Root:** `__RDW_ROOT__`

Invoke when the user runs `/rdw` or asks for grounded domain copy.

## Steps

1. Read `SKILL.md` + `prompts/pipeline-orchestrator.md` under root.
2. Agent performs research; save `knowledge/<domain>/*.yaml`.
3. Copywriter → QA → humanizer; no new facts in humanizer.
4. See `README.md` for batch: `prompts/batch-runner.md`.
