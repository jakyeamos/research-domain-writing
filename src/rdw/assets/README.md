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

### 3. Plan a batch

```bash
rdw batch plan examples/batch-tasks.yaml --out .rdw-runs/demo-batch
```

This validates the batch file, expands each task into a deterministic task folder, and writes `summary.yaml` plus `batch-log.jsonl` with `planned` statuses.

## Core Commands

```bash
rdw doctor
rdw validate-packet knowledge/basketball/demo-guard-2026-demo.yaml --strict
rdw validate-batch examples/batch-tasks.yaml
rdw new-domain finance "Finance Writing"
rdw task plan --request "explain idempotency keys" --domain technical --out .rdw-runs/idempotency
rdw batch plan examples/batch-tasks.yaml --out .rdw-runs/demo-batch
rdw install --target claude
rdw install --target cursor
rdw install --target agents
```

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
/tmp/rdw-wheel-smoke/bin/rdw doctor
```

## License

MIT. See [LICENSE](LICENSE).
