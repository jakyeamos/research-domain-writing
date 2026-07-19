# RDW Modernization Progress

- Updated: 2026-07-19
- Baseline: `main` / `9860d38` / `v0.2.0`
- Branch: `codex/rdw-gpt56-modernization`
- Current phase: M6 complete; bounded batch executor slice complete; release-ready pending review/merge
- Implementation phase: batch executor ticket #10 complete
- Application-code changes: M0–M6 plus the serial batch executor slice complete;
  merge/tag/publish remain separate release decisions

## Completed

- Established live git/version state and preserved the pre-existing untracked
  `skills/research-domain-writing/SKILL.md`.
- Added `AUDIT.md`, `TARGET.md`, and `EXEC_PLAN.md` for the in-place strategy.
- M0/M1 (`5bc91e3`): aligned v0.2.0 lock/release truth, derived the publish
  wizard version from `pyproject.toml`, and added canonical root/package asset
  parity plus CI gates.
- M2 (`ab2ef1f`): made planner overrides authoritative, scored route signals,
  surfaced ambiguity warnings, added controlled YAML errors, and added JSON
  diagnostics for the main CLI surfaces.
- M3 (`ae0510b`, `9c790df`): enforced legal lifecycle transitions, required
  reasons for QA failures, made projections atomic, made batch events append-only,
  and kept read-only status views from rewriting files.
- M4 (`c627bc7`): staged and verified package assets before replacement,
  protected unmanaged roots and command files, added rollback coverage, and
  made installed validation fall back to packaged config/knowledge assets.
- M5 (`8dff263`): added locked source/package/wheel/install CI proof, the
  reproducible Vulture gate, release documentation, and publish preflights.
- Built and exercised a fresh wheel through doctor, strict packet validation,
  packaged-resource batch validation/planning, task planning, schema export,
  lifecycle marking, and all-target installation.
- Added `scripts/smoke-install.py`, a disposable-home CLI smoke that invokes
  `rdw install` separately for the Claude, Cursor, and agents targets and
  verifies each consumer surface plus the managed packaged root.
- Ticket #10: added the serial filesystem-first fixture batch executor with a
  typed policy, one-writer lease, input-order dispatch, immutable receipt
  attempts, bounded retry/backoff, event-ID replay projection, cooperative
  pause/cancel, partial-success counts, and explicit unknown-attempt recovery.
  Focused executor coverage is now 9 tests; the full suite is 61 tests.

## Current findings

- The no-LLM core boundary, CLI names, packet semantics, and run-artifact paths
  remain intact.
- Source checkout and installed wheel now share the critical asset and config
  resolution path.
- M6 review remediation has now shared required-field definitions between
  validation and schema export, exposed low-confidence general routing,
  atomized the developer asset sync, and removed remaining direct writes from
  CLI/adapter artifacts.
- Remaining product risk is operational rather than architectural: actual
  fresh-session slash-command behavior in each target agent remains a release
  boundary check; the install materialization path now has a repeatable local
  CLI proof.
- The executor remains intentionally fixture-backed. Provider adapters, live
  research execution, parallel workers, cost accounting, hosted queues, and
  packet auto-merge remain outside this slice.

## Next step

The implementation and local adversarial checks for the bounded batch slice are
complete. A maintainer can now review this branch and decide whether to merge
it. Tagging and publishing remain separate explicitly authorized release
actions.

## Blockers and boundaries

- Do not publish, retag, or modify external agent homes from this branch.
- Manual slash-command smoke remains a release-boundary check because it
  requires an actual fresh Claude/Cursor/agent session.
- The pre-existing untracked skill file is outside this change set.
