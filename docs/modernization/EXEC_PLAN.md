# RDW Modernization Execution Plan

- Status: proposed
- Baseline: `main` / `8f3387f` / `v0.2.0`
- Owner: one lead implementation agent; specialist review passes are bounded and read-heavy
- Application-code implementation: not started

## Chosen strategy

### A. Deep refactor in place — chosen

RDW is a small package with no hosted service, database, authentication system,
or production data store. Its current module boundaries and tests contain
valuable behavior that should be improved rather than discarded. A clean
rewrite would recreate the same packet, prompt, install, and release contracts
while making regressions harder to detect.

The refactor will preserve the user-facing CLI and artifact shapes while
replacing duplicated contract definitions, unsafe state writes, and manually
maintained package mirrors.

### B. Parallel v2 — not chosen by default

There is no large live system that requires a gradual production cutover. A
parallel v2 would create two content and lifecycle paths precisely where the
current audit found drift.

### C. Clean rewrite — rejected

The package is only about 2,600 lines of Python and already has focused golden,
contract, workflow, and wheel coverage. Rewriting it would spend the migration
budget on re-establishing behavior instead of improving the real risks.

## Operating rules

- Work from a protected baseline in a dedicated `codex/` branch/worktree before
  changing application code.
- Keep the current `main` deployable and leave the pre-existing untracked
  `skills/` file outside the modernization commit set.
- One lead owns contract and architecture decisions. Review agents may inspect,
  test, and report; they do not independently redesign shared foundations.
- Keep every milestone runnable and end it with a coherent commit plus a
  truth-file update.
- Preserve existing CLI spellings and artifact paths unless a compatibility
  reader/alias is implemented in the same milestone.
- Do not add a model SDK, crawler, database, or hosted service.
- Do not weaken strict validation, types, tests, or source-linkage rules to make
  a migration green.
- Run focused checks during a milestone and the full quality ladder at its
  boundary.
- No browser check is applicable: this product has no browser UI. CLI subprocess
  and fresh-wheel checks are the equivalent critical-journey proof.

## Milestone map

| Milestone | Vertical outcome | Depends on |
| --- | --- | --- |
| M0 | Protected baseline, truthful docs, and drift gates | none |
| M1 | One resolved contract model and canonical content pipeline | M0 |
| M2 | Predictable router and machine-readable CLI | M1 |
| M3 | Safe lifecycle state and batch projections | M1, M2 |
| M4 | Atomic installer and fresh-consumer parity | M1, M2, M3 |
| M5 | Release/CI hardening and cleanup | M1–M4 |
| M6 | Adversarial review, cutover, and rollback-ready release | M5 |

## M0 — Establish the protected modernization baseline

### Objective

Make the audit/target/plan/progress surfaces truthful, repair only baseline
metadata drift that is unambiguously wrong, and add checks that prevent the
known source/package divergence from returning.

### Affected directories and systems

- `docs/modernization/`
- `.tracker/PROJECT_TRUTH.md`
- `pyproject.toml`, `uv.lock`
- `.github/workflows/ci.yml`
- release/package metadata and scripts only where the version is demonstrably
  stale

### Dependencies

- Audit evidence from `AUDIT.md`.

### Preserve

- v0.2.0 package name, console script, command names, and current source layout.
- Existing untracked `skills/research-domain-writing/SKILL.md`.

### Intentionally change

- Truth-file branch/release state.
- Lockfile editable package version.
- CI from “can run tests” to “source/package/release surfaces agree.”

### Checks

- `uv lock --check`
- `git diff --check`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run basedpyright src tests scripts`
- `uv run pytest -q`
- `shellcheck scripts/*.sh`

### Migration and rollback

Metadata-only changes are reversible by commit. Do not rewrite generated user
runs or install paths. If a parity gate exposes an intentional difference,
document it in the manifest before proceeding.

### Completion criteria

- The truth file matches live branch/tag/version state.
- `uv lock --check` passes.
- CI has an explicit parity/lock check.
- No stale version constant remains unexplained.

### Delete

- No runtime code is deleted in M0.
- Remove obsolete release constants only when the derived replacement is green.

## M1 — Establish the contract and canonical-content foundations

### Objective

Create one resolved contract path for packet/batch/task/status data and one
source-of-truth pipeline for package assets without changing the user-facing
artifact shapes.

### Affected directories and systems

- `src/rdw/` contract, config, serialization, and resource modules
- `config/`, `domains/`, `knowledge/`, `prompts/`, `examples/`, `install/`
- `src/rdw/assets/`
- `scripts/` for manifest/sync/check support
- `tests/` and `tests/golden/`
- `pyproject.toml` build configuration if a build hook is required

### Dependencies

- M0 version and parity gates.

### Preserve

- Packet fields, strict/lenient semantics, depth aliases, task contract fields,
  prompt execution order, output paths, and packaged asset availability.

### Intentionally change

- Hand-maintained schema/diagnostic duplication.
- Manual editing of `src/rdw/assets/` as a second source.
- Config/resource fallback behavior so source-root and installed consumers use
  the same resolver.

### Implementation shape

1. Introduce typed models or a shared contract definition for packet, batch,
   task, diagnostic, task status, and batch projection data.
2. Move strictness and domain-extension checks behind explicit policies.
3. Derive JSON Schema and serialized contract fields from the shared definition
   where possible.
4. Add a canonical asset manifest mapping root authoring paths to package paths.
5. Add `assets check` and `assets sync` developer/release operations. Keep the
   checked-in package mirror until clean builds prove the generated path.
6. Add parity tests for all mirrored content and version-bearing files.

### Checks

- Contract fixture tests for valid/invalid packets and batches.
- JSON Schema export checks against the same required fields.
- Root/package asset parity check.
- Source checkout and isolated wheel validation.
- Full quality ladder at milestone boundary.

### Migration and rollback

Existing YAML remains readable. New serializers must emit the current field
names and locations. If the shared model cannot represent an existing fixture,
stop and add a compatibility representation before changing the writer.

### Completion criteria

- One resolved contract is used by planner, validator, schema export, and CLI
  renderers.
- One asset manifest is the authoritative source/destination map.
- Drift between root and package assets fails locally and in CI.
- All existing tests/goldens pass or have an intentional, documented contract
  update.

### Delete

- Remove duplicate schema field lists and old asset-sync instructions after all
  callers use the shared contract/manifest.

## M2 — Rebuild routing and CLI interaction around the contracts

### Objective

Make routing deterministic and transparent, make overrides authoritative, and
give agents/CI a stable JSON surface without breaking human-readable output.

### Affected directories and systems

- `src/rdw/router.py`, `src/rdw/planner.py`, `src/rdw/cli.py`
- new command/rendering modules only if needed
- `config/router-inference.yaml`
- `prompts/domain-router.md`, `prompts/pipeline-orchestrator.md`
- golden bundles and contract/workflow tests

### Dependencies

- M1 resolved contract and diagnostic model.

### Preserve

- Existing CLI spellings and task IDs for the current golden requests.
- Explicit CLI overrides and current defaults where not ambiguous.
- The prompt bundle's research → packet → draft → QA → humanizer boundary.

### Intentionally change

- First-match router behavior becomes scored candidate resolution.
- Explicit overrides are applied before ID/path derivation.
- Low-confidence/unknown routes become visible warnings.
- Expected file/YAML/config errors become stable diagnostics.
- Add `--json` to doctor, validators, planners, status, and batch views.

### Checks

- Golden requests retain their current resolved IDs unless a documented contract
  correction is approved.
- Ambiguous-domain and explicit-override tests.
- Malformed YAML, missing file, missing config, and unsupported format tests.
- Subprocess tests for exit codes and JSON validity.
- Full quality ladder and package smoke.

### Migration and rollback

Keep human output and command aliases stable. Add JSON as an opt-in format. If
the new router would change an existing golden task ID, add a compatibility
normalization or treat it as an explicit behavior change before merging.

### Completion criteria

- `TaskRequest` overrides determine every resolved field, ID, path, and warning.
- Router output matches the documented prompt contract.
- No expected user error produces a traceback.
- JSON output is stable enough for CI/agent consumers.

### Delete

- Remove planner/router fallback lists and duplicate override bookkeeping after
  all resolution flows use the shared contract.

## M3 — Make lifecycle state safe and coherent

### Objective

Turn task/batch lifecycle into a legal transition and projection system that is
safe under interruption and has no read-command side effects.

### Affected directories and systems

- `src/rdw/lifecycle.py` and shared run/IO modules
- task/batch artifact serializers
- lifecycle tests and workflow fixtures
- `prompts/batch-runner.md`, `docs/superpowers/specs/2026-07-07-rdw-v0.3-workflow-design.md`

### Dependencies

- M1 contract/IO foundations and M2 diagnostic/CLI surface.

### Preserve

- Current status names and artifact paths.
- Existing valid sequential flows.
- Ability to inspect and resume existing planned runs.

### Intentionally change

- Define allowed transitions and reject rollback from terminal state unless an
  explicit recovery command is later designed.
- Append events without read-and-rewrite races.
- Atomically replace `status.json` and `summary.yaml`.
- Make status/resume views read-only.
- Centralize `needs_review` calculation and event/projection fields.

### Checks

- Transition matrix tests, including every invalid transition.
- Old status files without history.
- QA-failed reasons and recovery path.
- Batch counts after each status.
- Interrupted-write simulation using temp files and replacement failure.
- Sequential and controlled concurrent append tests.
- Full CLI and wheel smoke.

### Migration and rollback

Read old artifacts as version 1. New writes may add a format/version field but
must retain current fields. Do not rewrite all existing output directories. A
rollback is safe because old readers continue to see the preserved files.

### Completion criteria

- All accepted status changes produce one durable event and coherent projections.
- Read commands do not modify timestamps or contents.
- A killed write cannot leave invalid JSON/YAML at the canonical path.
- Batch summary and event log agree on review/complete/failed semantics.

### Delete

- Remove direct summary mutation from read paths and the old full-log rewrite
  helper after compatibility tests pass.

## M4 — Harden installation and fresh-consumer behavior

### Objective

Make package installation and agent-surface installation transactional and
prove source and installed consumers execute the same critical flows.

### Affected directories and systems

- `src/rdw/install.py`, `src/rdw/resources.py`
- package asset manifest/sync from M1
- `.github/workflows/ci.yml`
- installer tests and release smoke scripts

### Dependencies

- M1 canonical assets, M2 diagnostics, M3 safe IO.

### Preserve

- Claude, Cursor, `.agents`, and RDW config target paths.
- Explicit `--backup`, `--force`, and `--dry-run` semantics.
- Fallback copy behavior on filesystems without symlink support.

### Intentionally change

- Stage and verify before replacing managed roots.
- Track managed files/source manifest.
- Keep command files and skill links from silently overwriting unrelated real
  directories.

### Checks

- Temporary-home install for every target.
- Real-directory refusal, backup, force, symlink, fallback-copy, and dry-run.
- Simulated interrupted copy.
- Isolated wheel: doctor, strict packet, batch validation/plan, task plan,
  schema export, lifecycle mark.
- Package/source parity and `uv lock --check`.

### Migration and rollback

Existing install roots remain readable. A staged replacement can be rolled back
to the prior managed root or backup. Never delete a user-owned real directory
without the existing explicit flag.

### Completion criteria

- No package asset destination is removed before the replacement is ready.
- Fresh wheel smoke covers all critical command families.
- A package built from a clean checkout contains the current release metadata,
  prompts, config, domains, examples, and install templates.

### Delete

- Remove manual package-copy instructions and stale compatibility code that the
  manifest/sync path replaces.

## M5 — Release, CI, and documentation hardening

### Objective

Make the repository's release path prove the actual product, then remove stale
version constants and update all user-facing documentation from the canonical
source.

### Affected directories and systems

- `.github/workflows/ci.yml`
- `scripts/publish-pypi-wizard.sh`
- `README.md`, `RELEASE.md`, `CHANGELOG.md`, `SKILL.md`
- packaged generated assets
- `.tracker/PROJECT_TRUTH.md`
- `docs/LIMITATIONS.md`, `docs/FUTURE-AIOS-INTEGRATION.md`

### Dependencies

- M1–M4 complete.

### Preserve

- SemVer policy and current package identity.
- Honest no-LLM/no-crawler limitations.
- Existing publish confirmation and secret-handling boundaries.

### Intentionally change

- Derive `PROJECT_VERSION` from `pyproject.toml`.
- Add `uv lock --check`, shellcheck, scoped dead-code, parity, full wheel smoke,
  and release metadata checks to CI/preflight.
- Align root and package docs via the canonical pipeline.
- Update `.tracker/PROJECT_TRUTH.md` as a live snapshot, not a changelog.

### Checks

- Full quality ladder from a clean checkout.
- `uv build` and isolated install with declared dependencies.
- Release wizard preflight against a temporary tag/fixture where safe.
- Search for stale release versions and obsolete paths.
- Review all generated diffs.

### Migration and rollback

No publish occurs as part of implementation. Version/tag/push/PyPI actions remain
explicit cutover actions after review. If release preflight fails, keep the
modernization branch and fix the gate; do not retag or publish over an existing
version.

### Completion criteria

- One version source and one content source are enforced.
- CI proves source, package, wheel, install, and release surfaces.
- Release docs describe the shipped commands and limitations accurately.
- No unexplained stale `0.1.0`/`0.2.0` reference remains.

### Delete

- Remove hard-coded publish version and manual mirror caveats.
- Remove obsolete release instructions after their replacement is verified.

## M6 — Adversarial review and controlled cutover

### Objective

Have a fresh reviewer attack the complete branch against the baseline, target,
and plan; fix confirmed high/medium findings; then prepare a rollback-ready
release without performing irreversible publication automatically.

### Review lanes

1. Contracts, YAML compatibility, packet grounding, and schema parity.
2. Lifecycle transitions, atomic writes, interruption, and concurrency.
3. Routing/CLI behavior, exit codes, JSON, and compatibility aliases.
4. Package assets, installer safety, fresh wheel, and release metadata.
5. Tests, CI, dependency surface, dead code, documentation, and truth files.

### Checks

- Full quality ladder.
- Fresh-wheel critical journeys.
- Complete diff against `v0.2.0`.
- Search for dead code, stale flags, duplicate contract definitions, old version
  constants, TODOs, skipped/weakened checks, and temporary shims.
- Confirm no browser review is applicable; use CLI subprocess evidence.

### Completion criteria

- No confirmed P0/P1 issues remain.
- Every P2 is fixed or explicitly justified in the progress/release notes.
- Target, plan, progress, README, release docs, and truth file agree with code.
- Branch is clean except for explicitly preserved user files outside the commit.
- Release command, tag, and PyPI publication are documented and ready, but only
  executed when explicitly authorized.

## Final cutover and rollback

1. Review `TARGET.md` and approve the five human-direction defaults.
2. Execute M0–M6 on the modernization branch.
3. Run the full ladder from a clean checkout and verify exact tag/HEAD identity.
4. Merge the coherent modernization commit set to `main`.
5. Tag the selected release version only after the release ladder passes.
6. Run the package publish wizard only with explicit release authorization.
7. Verify PyPI package contents and fresh install behavior.
8. If a post-merge issue appears, revert the modernization commit(s) or return
   to the prior tag; existing run directories remain readable because no data
   store or destructive migration is introduced.

## Stop conditions

Pause for user direction only for:

- material risk of deleting or corrupting user run artifacts;
- a required external credential or irreversible publish action;
- a contract change that cannot preserve existing consumers;
- a product decision among the five listed in the audit.

Ordinary implementation ambiguity, failing tests, and stale documentation are
within the lead agent's authority to resolve and document.
