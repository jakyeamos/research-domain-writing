# Research Domain Writing

Research Domain Writing (RDW) is an agent-first harness for research-grounded writing. It validates structured research packets, plans repeatable writing runs, emits exact prompt bundles, and keeps outputs auditable.

The `rdw` CLI in v0.2 is not an LLM runner. It does not browse, call model APIs, or draft autonomously. Your agent performs the research and writing by following the emitted prompts.

## Install

From PyPI:

```bash
pip install research-domain-writing
rdw doctor
```

Package page: [research-domain-writing on PyPI](https://pypi.org/project/research-domain-writing/).

From a source checkout:

```bash
uv run rdw doctor
```

Install agent slash commands and skills:

```bash
rdw install --target all
```

For source checkouts, the compatibility wrapper still works:

```bash
./install/install.sh
```

## First Run Paths

### 1. Check the install

```bash
rdw doctor
```

`doctor` checks Python version, packaged assets, writable output directories, and install target readiness.

### 2. Plan one task

```bash
rdw task plan \
  --request "improve the copy on my LIS leaderboard" \
  --out .rdw-runs/lis-leaderboard
```

This writes:

- `.rdw-runs/lis-leaderboard/task-contract.yaml`
- `.rdw-runs/lis-leaderboard/prompt-bundle.md`
- `.rdw-runs/lis-leaderboard/status.json`

Give the prompt bundle to your agent. The agent is responsible for research, drafting, QA, and final output.

### 3. Execute the deterministic vertical-slice fixture

The repository includes a fixture-backed runtime for proving the handoff and
lifecycle boundary without calling a model API:

```bash
rdw task execute .rdw-runs/demo-task \
  --fixture examples/fixtures/basketball-vertical-slice.yaml \
  --root .
```

The fixture stages a research packet, knowledge packet, draft, QA result, and
final artifact under the run directory, validates the packet and QA gate, and
advances the existing lifecycle. Use the QA-failed fixture with `--resume` to
exercise an auditable retry.

### 4. Plan a batch

```bash
rdw batch plan examples/batch-tasks.yaml --out .rdw-runs/demo-batch
```

This validates the batch file, expands each task into a deterministic task folder, and writes `summary.yaml` plus `batch-log.jsonl` with `planned` statuses.

For deterministic integration checks, a serial fixture-backed executor can run
the planned tasks without a model, browser, provider SDK, or database. Create a
fixture map covering every task:

```yaml
batch_id: demo-batch-001
execution:
  max_concurrency: 1
  max_attempts: 2
  retry_backoff_seconds: [5, 30]
  failure_policy: continue
fixtures:
  batch-demo-guard-summary: examples/fixtures/basketball-vertical-slice.yaml
```

Then run the additive executor controls:

```bash
rdw batch execute .rdw-runs/demo-batch \
  --fixture-map path/to/fixture-map.yaml --root .
rdw batch pause .rdw-runs/demo-batch
rdw batch cancel .rdw-runs/demo-batch
rdw batch execute .rdw-runs/demo-batch \
  --fixture-map path/to/fixture-map.yaml --root . --resume
```

The executor is intentionally serial and filesystem-first. Receipts remain
immutable, retries keep the task idempotency key but receive new attempt
directories, completed tasks survive partial failure or cancellation, and an
unknown attempt requires explicit reconciliation. `rdw batch resume` remains a
read-only next-task view.

### 5. Inspect and advance a run

Lifecycle state is explicit and ordered:

```text
planned -> research-done -> draft-done -> qa-passed -> final-done
                                      \-> qa-failed -> research-done or draft-done
```

Use `--reason` when marking `qa-failed`. Invalid jumps are rejected without
changing the run artifacts. Status and batch views are read-only; automation
can use `--json` on doctor, validators, planners, status, resume, and task
marking commands.

## Core Commands

```bash
rdw doctor
rdw validate-packet knowledge/basketball/demo-guard-2026-demo.yaml --strict
rdw validate-batch examples/batch-tasks.yaml
rdw new-domain finance "Finance Writing"
rdw task plan --request "explain idempotency keys" --domain technical --out .rdw-runs/idempotency
rdw batch plan examples/batch-tasks.yaml --out .rdw-runs/demo-batch
rdw task execute .rdw-runs/demo-task --fixture examples/fixtures/basketball-vertical-slice.yaml --root .
rdw batch execute .rdw-runs/demo-batch --fixture-map path/to/fixture-map.yaml --root .
rdw batch pause .rdw-runs/demo-batch
rdw batch cancel .rdw-runs/demo-batch
rdw install --target claude
rdw install --target cursor
rdw install --target agents
rdw validate-packet knowledge/basketball/demo-guard-2026-demo.yaml --strict --json
rdw validate-packet examples/acceptance/basketball/packets/ranking-usage-ts-change.yaml --mature --json
rdw validate-claim-ledger examples/acceptance/basketball/packets/ranking-usage-ts-change.yaml examples/acceptance/basketball/qa/ranking-usage-ts-change.yaml --mature --json
rdw status .rdw-runs/lis-leaderboard --json
rdw batch status .rdw-runs/demo-batch --json
```

`rdw install` stages packaged assets before replacing its managed install root.
Existing unrelated real directories and managed command files are protected by
default; use `--backup` or `--force` explicitly when replacing them.

Legacy scripts remain as thin wrappers:

```bash
python scripts/validate-packet.py knowledge/basketball/demo-guard-2026-demo.yaml
./scripts/new-domain.sh finance "Finance Writing"
```

## What RDW Provides

```text
research-domain-writing/
  src/rdw/                # installable CLI and validators
  SKILL.md                # agent skill entrypoint
  config/                 # domain registry, style, sources, output formats
  domains/                # domain packs
  knowledge/              # reusable research packets
  prompts/                # stage prompts and orchestrators
  examples/               # curated example artifacts
  install/                # slash command and skill templates
  docs/                   # limitations and integration notes
```

Starter domains:

- `basketball` - stat interpretation and player/ranking copy
- `music` - review blurbs with explicit evidence limits
- `technical` - product and feature explainers

## Research Model

RDW separates knowledge work from style work:

| Layer | Responsibility |
| --- | --- |
| Research | Facts, sources, uncertainty, terminology |
| Domain copywriter | Structured, grounded draft |
| Domain QA | Grounding, jargon, overclaiming |
| Humanizer/blader | Style, rhythm, author voice only |

Packets live in `knowledge/<domain>/*.yaml` and must include source notes, confidence, timestamps, and domain-specific extension data when required.

See [docs/LIMITATIONS.md](docs/LIMITATIONS.md) for current boundaries.

## Validation

`rdw validate-packet` checks:

- required packet fields
- registered domains
- ISO-like `last_updated`
- confidence values: `high`, `medium`, `low`
- `source_notes` shape and strict fact-id linkage
- domain extension presence when strict mode requires it

With `--mature`, the validator applies the opt-in basketball acceptance
contract: source-grounded metric semantics, role and sample context, ranking
metadata and freshness, confidence rules for small samples, and rejection of
synthetic/demo provenance. `rdw validate-claim-ledger` checks QA issue counts
and maps every accepted claim to a source-linked packet fact. These gates are
deterministic and do not browse or call a provider.

`rdw validate-batch` checks:

- unique task IDs
- supported depth values: `1`, `2`, `3`, `4`, `deep`, `standard`, `light`, `minimal`
- packet references when supplied
- supported output formats

## Examples

| Example | Artifacts |
| --- | --- |
| `examples/basketball-example/` | synthetic task, packet-derived knowledge, draft, QA, final |
| `examples/music-example/` | thin-evidence music task, research packet, knowledge, draft, QA, final |
| `examples/technical-example/` | technical feature task, research packet, knowledge, draft, QA, final |
| `examples/acceptance/basketball/` | source-grounded mature-pack packets, QA claim ledgers, and positive/negative gates |
| `examples/batch-tasks.yaml` | deterministic batch planning input |

The basketball example is explicitly fictional. It demonstrates schema and claim-boundary behavior, not real player analysis.

## Add A Domain

```bash
rdw new-domain finance "Finance Writing"
```

Then edit:

- `domains/finance/domain-config.yaml`
- `domains/finance/research-packet-template.yaml`
- `domains/finance/qa-checklist.md`
- `domains/finance/writing-templates.md`
- `config/domains.yaml`
- `config/research-sources.yaml`

No core prompt edits should be required for normal domain additions.

## Agent Usage

After `rdw install --target all`, start a fresh agent session and use:

```text
/rdw improve the copy on my LIS leaderboard
```

or:

```text
/rdw-batch examples/batch-tasks.yaml
```

Natural language is usually enough. The router infers domain, entity, output type, audience, and research depth; override only when needed.

## Quality Bar

Before release or a serious PR:

```bash
uv sync --locked
uv lock --check
python3 scripts/sync-package-assets.py --check
shellcheck scripts/*.sh
uv run ruff check .
uv run ruff format --check .
uv run basedpyright src tests scripts
uv run pytest -q
uv build
```

Wheel smoke:

```bash
python -m venv /tmp/rdw-wheel-smoke
/tmp/rdw-wheel-smoke/bin/pip install dist/*.whl
/tmp/rdw-wheel-smoke/bin/rdw doctor --json
```

The wheel smoke should run the critical doctor, strict packet, batch
validation/planning, schema export, lifecycle, and install commands against
the wheel's packaged assets, not paths from the source checkout. See
[RELEASE.md](RELEASE.md) for the complete sequence.

## License

MIT. See [LICENSE](LICENSE).
