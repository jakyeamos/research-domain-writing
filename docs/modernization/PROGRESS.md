# RDW Modernization Progress

- Updated: 2026-07-15
- Baseline: `main` / `9860d38` / `v0.2.0`
- Branch: `codex/rdw-gpt56-modernization`
- Current phase: M6 adversarial review and final validation
- Implementation phase: in progress
- Application-code changes: M0–M5 complete; M6 remediation in progress

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

## Current findings

- The no-LLM core boundary, CLI names, packet semantics, and run-artifact paths
  remain intact.
- Source checkout and installed wheel now share the critical asset and config
  resolution path.
- M6 review remediation has now shared required-field definitions between
  validation and schema export, exposed low-confidence general routing,
  atomized the developer asset sync, and removed remaining direct writes from
  CLI/adapter artifacts.
- Remaining product risk is operational rather than architectural: the final
  remote CI run and slash-command smoke in each target agent are still release
  boundary checks.

## Next step

Complete the M6 checks against the full branch:
contract compatibility, lifecycle/data integrity, installer safety, package
parity, documentation drift, and the complete quality ladder. Only after that
review should a maintainer decide whether to merge, tag, or publish.

## Blockers and boundaries

- Do not publish, retag, or modify external agent homes from this branch.
- Manual slash-command smoke remains a release-boundary check because it
  requires an actual fresh Claude/Cursor/agent session.
- The pre-existing untracked skill file is outside this change set.
