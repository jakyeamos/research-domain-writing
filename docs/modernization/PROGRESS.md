# RDW Modernization Progress

- Updated: 2026-07-15
- Baseline: `main` / `8f3387f` / `v0.2.0`
- Current phase: audit and target definition complete
- Implementation phase: not started
- Application-code changes: none

## Completed

- Established live git/version state and preserved the pre-existing untracked
  `skills/research-domain-writing/SKILL.md`.
- Ran the source quality ladder: Ruff, format, BasedPyright, pytest (36),
  pre-CR coverage wrapper, shellcheck, and scoped Vulture.
- Built the sdist and wheel successfully.
- Ran source and isolated-wheel CLI smoke for doctor, strict packet validation,
  batch validation/planning, and task planning.
- Confirmed the tracked lockfile is stale with `uv lock --check`.
- Compared root authoring content with `src/rdw/assets/` and documented release,
  skill, changelog, publish-wizard, and package-version drift.
- Wrote `AUDIT.md`, `TARGET.md`, and `EXEC_PLAN.md`.

## Current findings

- The current implementation is healthy enough for an in-place refactor.
- The highest-risk surfaces are duplicated content/contracts, lifecycle writes,
  and release/package truth—not framework or runtime scale.
- The recommended target preserves the no-LLM-in-core boundary, CLI names, and
  run-artifact paths.

## Next step

Review `TARGET.md` and `EXEC_PLAN.md`. After the target direction is accepted,
create the protected modernization branch/worktree and begin M0.

## Blockers and boundaries

- Implementation is intentionally paused at the single product-direction review
  point from the modernization brief.
- Do not publish, retag, or modify external agent homes during this planning
  phase.
- The pre-existing untracked skill file is outside this change set.
