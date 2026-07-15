# RDW Modernization Audit

- Date: 2026-07-15
- Baseline commit: `8f3387f` (`v0.2.0`)
- Baseline branch: `main`
- Scope: repository architecture, CLI behavior, content contracts, packaging, release path, quality, and migration risk
- Application-code changes during this audit: none

## Executive finding

Research Domain Writing is a healthy but early-stage Python CLI/package, not a
large application that needs a clean rewrite. Its strongest decisions are the
local-first agent boundary, deterministic planning, strict packet validation,
and explicit separation between research, drafting, QA, and humanizer work.

The highest-leverage modernization is an in-place refactor around one contract
model and one canonical content source. The current blast-radius risk is not
module count; it is that the source checkout, packaged assets, generated run
artifacts, release wizard, lockfile, and truth files can describe different
versions of the product.

Recommended strategy: **deep refactor in place**, preserving current CLI names,
run-directory shapes, packet meanings, and the no-LLM-in-core boundary.

## Baseline evidence

### Repository state

- `git status --short --branch`: `main` at `origin/main`, with one pre-existing
  untracked file at `skills/research-domain-writing/SKILL.md`. It was not edited
  or staged.
- The checked-in tag and `pyproject.toml` both identify `0.2.0`.
- `.tracker/PROJECT_TRUTH.md` was stale at the start of the audit: it named
  `feat/v0.2-hardening` as the active branch and still described the v0.2
  release as the next step.

### Quality and runtime checks

| Check | Result | Evidence |
| --- | --- | --- |
| Ruff lint | pass | `uv run ruff check .` |
| Ruff format | pass | `uv run ruff format --check .` — 21 files formatted |
| BasedPyright | pass | `uv run basedpyright src tests scripts` — 0 errors/warnings/notes |
| Tests | pass | `uv run pytest -q` — 36 passed |
| Pre-CR Python coverage wrapper | pass | `uv run python scripts/run-pre-cr-python-tests.py` — 36 passed |
| Shell lint | pass | `shellcheck scripts/*.sh` |
| Scoped dead-code scan | pass | `vulture src scripts tests --min-confidence 70` — no findings |
| Package build | pass | `uv build` produced sdist and wheel for `0.2.0` |
| CLI smoke | pass | `rdw doctor`, strict packet validation, batch validation, task plan, batch plan |
| Fresh wheel smoke | pass | isolated `/tmp` environment: install wheel + PyYAML, `rdw doctor`, strict packet validation, task plan |
| Lock consistency | **fail** | `uv lock --check` reports that `uv.lock` needs updating; its editable package entry still says `0.1.0` |

The first sandboxed `uv build` invocation could not read the normal uv cache;
the approved local-cache rerun passed. This is an environment limitation, not
a package-build failure.

## Current architecture and flows

### Runtime modules

The installable package is concentrated in `src/rdw/`:

- `cli.py` is the argparse composition root and owns all command handlers.
- `router.py` loads YAML inference rules and returns a small `RouteResult`.
- `planner.py` turns a `TaskRequest` into a YAML task contract, prompt bundle,
  and initial `status.json`; batch planning composes the same path.
- `validation.py` validates packets and batch files in lenient or strict mode.
- `lifecycle.py` mutates task status, projects batch counts, and appends batch
  events.
- `schema_export.py` hand-builds JSON Schema documents.
- `config.py`, `yaml_io.py`, and `resources.py` provide config, serialization,
  and package-asset access.
- `install.py` materializes package assets and installs Claude, Cursor, and
  agent skill surfaces.
- `adapters/` provides a local recorder plus provider-neutral OpenAI and
  Anthropic stubs.

### Request flow

```text
CLI args
  -> TaskRequest
  -> YAML router
  -> inferred contract
  -> prompt-bundle.md + task-contract.yaml + status.json
  -> external agent performs research/draft/QA/humanizer
  -> agent marks lifecycle status
```

Batch planning validates one YAML input, creates one task directory per item,
then writes `summary.yaml` and `batch-log.jsonl`. Lifecycle reads task status
files and rewrites the batch summary projection.

### Content and packaging flow

The repository contains authoring content at the root (`config/`, `domains/`,
`examples/`, `knowledge/`, `install/`, and `prompts/`) plus a package mirror at
`src/rdw/assets/`. The directories currently compare equal, but the top-level
release-facing files are manually duplicated and have drifted:

- `README.md` and `src/rdw/assets/README.md` differ.
- `RELEASE.md` targets `0.2.0`; `src/rdw/assets/RELEASE.md` targets `0.1.0`.
- `CHANGELOG.md` contains the complete v0.2 entries; the packaged changelog is
  abbreviated.
- Root `SKILL.md` declares `0.1.0`; packaged `SKILL.md` declares `0.2.0`.
- `scripts/publish-pypi-wizard.sh` hard-codes `PROJECT_VERSION="0.1.0"`.
- `uv.lock` records the editable package as `0.1.0` until uv updates it.

This means a source checkout can pass its tests while a built package, release
wizard, or installed skill surface carries stale release information.

## Valuable parts to retain

1. **Product boundary.** The CLI plans and validates; the agent researches and
   writes. The core does not silently become a model runner or crawler.
2. **Research/style separation.** The humanizer rule that it may not add facts
   is explicit in both skill and prompt surfaces.
3. **Deterministic planning.** A natural-language request produces stable
   contracts and golden prompt bundles.
4. **Evidence-aware packets.** Strict mode checks fact IDs, source linkage,
   confidence, timestamps, URLs/DOIs, and domain extensions.
5. **Provider-neutral adapter seam.** The stubs make the future integration
   boundary visible without coupling the core to vendor SDKs.
6. **Safe planning defaults.** `--no-overwrite`, run IDs, temp-home installer
   tests, and explicit `--force`/`--backup` behavior are useful foundations.
7. **Package assets.** The wheel contains the content needed by an installed
   consumer, and the isolated wheel smoke proves the basic path works.

## Findings

### P1 — Release and package truth is split across stale copies

Evidence: `pyproject.toml`, `uv.lock`, `SKILL.md`,
`src/rdw/assets/SKILL.md`, `RELEASE.md`, `src/rdw/assets/RELEASE.md`,
`CHANGELOG.md`, `src/rdw/assets/CHANGELOG.md`, and
`scripts/publish-pypi-wizard.sh` disagree about the active release.

Impact: the next release can build a `0.2.0` wheel while its packaged release
instructions or publish wizard target `0.1.0`. `uv sync` can silently repair the
lockfile in CI because CI does not use `--locked`, masking the source-of-truth
failure.

Recommendation: choose one authoring source, generate or package from it, add a
parity/lock gate, and derive release version data from `pyproject.toml`.

### P1 — Run state is not safe under interruption or concurrent agents

Evidence: `src/rdw/lifecycle.py:63-90` writes `status.json` directly;
`src/rdw/lifecycle.py:214-237` reads the entire log and rewrites it; and
`src/rdw/resources.py:36-39` removes the existing installed asset root before
copying a replacement.

Impact: a killed process can leave truncated JSON/YAML, lose a concurrent log
event, or leave a partial install. The current tests prove sequential behavior,
not recovery or concurrency behavior.

Recommendation: use atomic temp-file replacement for projections and staged
directory replacement for installs. Treat the batch log as an append-only event
stream and derive summaries from events/task status.

### P1 — Lifecycle semantics are permissive and internally inconsistent

Evidence: `mark_task_status` accepts any listed status from any prior status;
`load_batch_status_view` calls `_refresh_batch_counts`, which writes
`summary.yaml` during a read; initial batch logs mark planned tasks as
`needs_review: true` while the summary starts at zero; and the event projection
uses a different `needs_review` rule than the summary.

Impact: agents can move a completed run backwards, read commands have side
effects, and consumers cannot reliably interpret batch counts or review state.

Recommendation: define a transition matrix, make status changes event-driven,
make read commands read-only, and centralize review-policy projection.

### P1 — Public contracts are defined three times

Evidence: packet/batch rules live in `validation.py`, schemas are separately
hand-built in `schema_export.py`, and prompt/content templates repeat field
requirements. The JSON Schemas intentionally do not cover strict linkage and
domain-extension semantics.

Impact: a packet can pass one surface and fail another; contract evolution
requires synchronized edits across code, schemas, goldens, prompts, and mirrored
assets.

Recommendation: introduce typed contract definitions and diagnostic rules as the
single executable source, then derive JSON Schema and human diagnostics from the
same definitions. Keep domain-specific semantic checks as explicit validators.

### P2 — Router behavior is weaker than the documented routing contract

Evidence: `src/rdw/router.py:58-64` returns the first domain with any keyword,
while `prompts/domain-router.md` describes choosing the domain with the most
signals and surfacing confidence/warnings. The implementation always emits
`confidence: medium`, does not score ambiguity, and does not parse the
prompt-documented natural-language `key=value` overrides.

Impact: ambiguous requests can route differently when YAML order changes, and
users receive less transparency than the prompt promises.

Recommendation: return scored candidates and diagnostics from a pure router;
apply explicit CLI/request overrides before scoring; emit warnings for low
confidence and unknown domains.

### P2 — Planner overrides do not fully propagate

Evidence: `src/rdw/planner.py:143-184` computes `output_type` and `entity_type`
from the route, uses `task.output_type` only when writing one contract field,
and derives `task_id`/`packet_id` from routed values. `_has_overrides` and
`_fields_explicit` also omit `output_format` and `task_id`.

Impact: an explicit override can produce a contract whose identifiers and
metadata still reflect the inferred request. That is a correctness risk for
batch reuse and packet lookup.

Recommendation: normalize all overrides into one resolved contract before
deriving IDs, paths, warnings, or inference metadata.

### P2 — Installed validation does not fully use packaged domain metadata

Evidence: `config.py` falls back to package assets, but
`validation.py:279-298` only finds domain extension schemas under a caller-provided
repository root. An installed consumer outside the source checkout therefore
gets registry fallback but can skip packaged extension enforcement.

Impact: source and installed validation can accept different packet shapes.

Recommendation: make all config/domain lookups go through one asset resolver
that supports root overrides and packaged defaults consistently.

### P2 — CLI error and automation surfaces are thin

Evidence: `src/rdw/cli.py:23-30` catches `ValueError` only, output is human text,
and there is no JSON mode for doctor, validation, planning, or lifecycle views.

Impact: malformed YAML, missing files, and filesystem failures can produce
tracebacks; agent/CI callers must scrape prose.

Recommendation: define diagnostic codes and stable exit classes, add `--json`
to read/validate/plan surfaces, and convert expected filesystem/YAML failures to
structured command errors.

### P2 — CI proves the Python code but not the release surface

Evidence: `.github/workflows/ci.yml` runs lint, formatting, types, tests, build,
and only `rdw doctor` after wheel installation. It does not run `uv lock --check`,
shellcheck, package/source parity, strict packet validation from the wheel,
batch planning from the wheel, or the publish wizard's version check.

Impact: the exact drift found in this audit can reach a tagged release while all
current CI jobs remain green.

Recommendation: add release-surface checks and make the wheel smoke exercise the
same critical commands as the source smoke.

### P3 — Early-stage constraints are documented but not yet productized

The CLI does not execute research, models, or final copy; packet merge/conflict
resolution is absent; domain packs beyond the current starters are limited; and
there is no database or hosted service. These are honest v0.x boundaries, not
reasons to add infrastructure during this modernization.

## External contracts and migration constraints

The following are externally relied upon or user-authored and must be preserved
or migrated explicitly:

- CLI command names and documented aliases, including compatibility scripts.
- Packet YAML meaning, strict/lenient validation behavior, and fact IDs.
- Batch input fields and depth aliases `1`–`4`.
- Task contract fields, prompt bundle path, and output-format paths.
- Task `status.json` and batch `summary.yaml`/`batch-log.jsonl` locations.
- Existing lifecycle status names, unless a compatibility reader maps them.
- Installed paths under Claude, Cursor, `.agents`, and the RDW config root.
- The package name, console script `rdw`, PyPI metadata, and source distribution.
- The explicit boundary that core RDW does not browse, call model APIs, or draft.

There is no database, authentication system, billing behavior, hosted API, or
production data migration in this repository.

## Current scorecard

| Dimension | Score | Evidence |
| --- | ---: | --- |
| Product coherence | 4/5 | Clear agent-first research-to-style pipeline and honest limitations |
| Correctness/data integrity | 3/5 | Strong packet checks; unsafe lifecycle/install writes and override drift |
| Architectural coherence | 3/5 | Sensible small modules; duplicated contracts and asset mirrors |
| Maintainability | 3/5 | Manageable code size; CLI, schemas, prompts, and release data repeat rules |
| Testability | 3/5 | 36 focused tests and goldens; weak malformed-input, packaging, and concurrency proof |
| Security/privacy | 4/5 | No network/secrets in core; installer has explicit destructive modes |
| CLI quality/accessibility | 3/5 | Good command grouping; prose-only output and surprising read side effects |
| Performance | 4/5 | Small local files and simple operations; repeated packet scans will not scale indefinitely |
| Operability | 2/5 | Lifecycle artifacts exist; no stable machine output or structured diagnostics |
| Developer experience | 3/5 | uv/CI/docs are usable; lock, mirror, truth, and release surfaces drift |

## Human decisions for target review

The plan makes defaults for everything else. Only these decisions materially
change the product direction:

1. Keep the no-LLM-in-core boundary as the default product promise: **yes**.
2. Preserve current CLI and run-artifact compatibility during the refactor:
   **yes**.
3. Make the repository root the authoring source and generate package assets:
   **recommended**.
4. Treat lifecycle logs as the source for projections while retaining current
   file paths: **recommended**.
5. Release the modernized contract as the next minor version if public output
   semantics change: **recommended; choose the exact version at cutover**.
