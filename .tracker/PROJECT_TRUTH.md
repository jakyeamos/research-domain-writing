---
schemaVersion: 1
projectName: Research Domain Writing
summary: Standalone research-grounded domain writing pipeline with prompts, domain packs, packet validation, examples, skill distribution, and release governance is extracted from AIOS.
healthScore: 74
statusLabel: needs_attention
nextStep: Build the dedicated batch CLI runner, then add stronger packet merge/conflict handling and schema validation.
blockers:
  - Batch execution is still prompt-driven rather than a dedicated CLI runner.
  - Packet merge/conflict resolution for concurrent updates is not implemented.
lastUpdated: 2026-06-27
tags: [aios, writing, research, skill, python]
areas: [engineering, writing]
goals: []
repoType: tool
sourceOfTruth: mixed
primaryLanguage: Python
activeBranch: main
lastCommitDate: 2026-06-27
quality:
  lint: pass
  types: pass
  tests: pass
  deadCode: unknown
  structure: warning
canonicalCommands:
  install: uv sync
  dev: unknown
  lint: uv run ruff check scripts tests
  typecheck: uv run basedpyright scripts tests
  test: uv run pytest -q
  deadcode: unknown
agentExpectationsVersion: 1
---

## Current State

Research Domain Writing is a standalone, file-based pipeline for turning research into grounded domain copy, QA output, and a human style pass. It separates research, domain copywriting, domain QA, and humanizer/blader responsibilities so style transformation does not invent domain knowledge.

The repo has prompts, starter domain packs, knowledge packet patterns, examples, a Codex/Claude/Cursor skill distribution surface, packet validation, release governance, and a substantial README. The main v1 limitation remains mechanical: batch execution is prompt-driven rather than handled by a dedicated CLI runner.

## What Exists

- `README.md` explaining the full pipeline, slash-command usage, batch workflow, domain packs, and limitations.
- `SKILL.md` as the agent skill entrypoint.
- `prompts/` for router, planner, researcher, packet builder, copywriter, QA, humanizer, orchestrator, and batch runner flows.
- `domains/` and `config/` for domain-specific writing and source rules.
- `knowledge/` examples and reusable packet patterns.
- `examples/` with end-to-end sample tasks.
- `scripts/validate-packet.py` for packet validation.
- `docs/LIMITATIONS.md` and `docs/FUTURE-AIOS-INTEGRATION.md` documenting v1 boundaries.
- `RELEASE.md` and `CHANGELOG.md` for release governance.

## What Does Not Exist Yet

- No dedicated batch CLI runner.
- No robust packet merge/conflict resolution for concurrent updates.
- No stronger JSON-schema validation beyond the current packet validator.
- No mature legal, finance, or medicine domain packs.
- No diff-based regression tests on QA rules.
- No dead-code scanner is configured.

## Next Step

Implement the dedicated batch CLI runner that orchestrates existing prompts, `examples/batch-tasks.yaml`, and `outputs/batch-log.jsonl` without changing the core research/copy/QA/humanizer separation.

## Quality Ladder Notes

Checks run on 2026-06-27:

| Step | Status | Evidence |
| --- | --- | --- |
| Lint | Pass | `uv run ruff check scripts tests` passed. |
| Format | Pass | `uv run ruff format --check scripts tests` reported 3 files already formatted. |
| Type check | Pass | `uv run basedpyright scripts tests` passed with 0 errors and 0 warnings. |
| Tests | Pass | `uv run pytest -q` passed with 10 tests. |
| Structure | Warning | `pre-cr run --json --workspace .` exited 1 because no changed files were present, while the emitted health payload reported `ready: true` and coverage loaded at 89 percent. |
| Dead code | Unknown | No Vulture or equivalent dead-code command is configured. |

## Agent Notes

Do not collapse research and humanizer responsibilities. If a draft needs new facts, route back to research rather than allowing the humanizer/blader step to invent content. AIOS may add thin adapters, but RDW pipeline prompts, domain packs, and batch runner work belong in this repo.
