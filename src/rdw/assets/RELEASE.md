# Release Governance

## Versioning

- Use SemVer-style versions: `MAJOR.MINOR.PATCH`.
- Current release target: `0.2.0`.
- `PATCH`: prompt clarifications, validator fixes, or docs updates that preserve task/output shapes.
- `MINOR`: additive domains, output formats, command templates, or validation fields.
- `MAJOR`: breaking prompt pipeline order, packet schema, install surface, or output contract changes.

## Release Checklist

1. Update version references in `pyproject.toml`, `SKILL.md`, install templates, `CHANGELOG.md`, and this file.
2. Update `CHANGELOG.md`.
3. Run quality gates:

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

4. Run CLI smoke:

```bash
uv run rdw doctor
uv run rdw validate-packet knowledge/basketball/demo-guard-2026-demo.yaml --strict
uv run rdw validate-batch examples/batch-tasks.yaml
uv run rdw task plan --request "improve the copy on my LIS leaderboard" --out /tmp/rdw-task-smoke
uv run rdw batch plan examples/batch-tasks.yaml --out /tmp/rdw-batch-smoke
uv run rdw task mark research-done /tmp/rdw-task-smoke
uv run rdw task mark draft-done /tmp/rdw-task-smoke
uv run rdw task mark qa-passed /tmp/rdw-task-smoke
uv run rdw task mark final-done /tmp/rdw-task-smoke

# Deterministic one-task adapter vertical slice
uv run rdw task plan --request "Explain why true shooting on high usage is the key read on Demo Guard in the 2026 synthetic sample" --domain basketball --entity "Demo Guard" --output-type stat_interpretation --audience "analytics-literate fans" --packet-id basketball-player-demo-guard-2026 --task-id basketball-example-demo-guard-stat-interpretation --out /tmp/rdw-fixture-task
uv run rdw task execute /tmp/rdw-fixture-task --fixture examples/fixtures/basketball-vertical-slice.yaml --root .
```

5. Run wheel smoke:

```bash
python -m venv /tmp/rdw-wheel-smoke
/tmp/rdw-wheel-smoke/bin/pip install dist/*.whl
ASSET_ROOT=$(/tmp/rdw-wheel-smoke/bin/python -c 'from importlib.resources import files; print(files("rdw.assets"))')
/tmp/rdw-wheel-smoke/bin/rdw doctor --json
/tmp/rdw-wheel-smoke/bin/rdw validate-packet "$ASSET_ROOT/knowledge/basketball/demo-guard-2026-demo.yaml" --strict --root /tmp/rdw-wheel-root --json
/tmp/rdw-wheel-smoke/bin/rdw validate-batch "$ASSET_ROOT/examples/batch-tasks.yaml" --root /tmp/rdw-wheel-root --json
/tmp/rdw-wheel-smoke/bin/rdw task plan --request "explain idempotency keys" --out /tmp/rdw-wheel-task --root /tmp/rdw-wheel-root --json
/tmp/rdw-wheel-smoke/bin/rdw batch plan "$ASSET_ROOT/examples/batch-tasks.yaml" --out /tmp/rdw-wheel-batch --root /tmp/rdw-wheel-root --json
/tmp/rdw-wheel-smoke/bin/rdw task mark research-done /tmp/rdw-wheel-task --json
/tmp/rdw-wheel-smoke/bin/rdw task mark draft-done /tmp/rdw-wheel-task --json
/tmp/rdw-wheel-smoke/bin/rdw task mark qa-passed /tmp/rdw-wheel-task --json
/tmp/rdw-wheel-smoke/bin/rdw task mark final-done /tmp/rdw-wheel-task --json
/tmp/rdw-wheel-smoke/bin/rdw install --target all --home /tmp/rdw-wheel-home
```

6. Run manual slash smoke after installing templates:

```bash
uv run rdw install --target all
```

Installation stages the packaged skill tree before replacing its managed root.
Existing unrelated real directories and command files are protected by
default; use `--backup` or `--force` deliberately when an existing consumer
surface must be replaced.

Then start a fresh agent session and verify:

- `/rdw improve the copy on my LIS leaderboard` produces an inferred task contract.
- `/rdw-batch examples/batch-tasks.yaml` follows batch-runner semantics.
- The agent states that the CLI planned the run and the agent performs research/writing.

7. If prompt behavior changed, run coverage adapter first:

```bash
uv run python scripts/run-pre-cr-python-tests.py
```

Use `pre-cr run --json --workspace .` only for changed-file readiness during PR work, not as the sole release coverage command.

8. Confirm generated run outputs are ignored and only curated examples/package assets are committed.
9. Confirm `git diff --check` is clean and `.tracker/PROJECT_TRUTH.md` records the final verification state.
10. Commit release changes, merge to `main`, tag `v0.2.0`, push `main` and the tag.
11. Publish to PyPI.

For an interactive PyPI token and publish flow, run:

```bash
scripts/publish-pypi-wizard.sh
```

The wizard opens the PyPI token page, captures the token with hidden input, rebuilds/verifies artifacts, runs a dry-run check, and only publishes after a final confirmation. It does not write the PyPI token to disk.

## Release Framing

RDW is an agent-first research-grounded writing harness. It creates structured, auditable writing runs; your agent performs research and drafting through explicit prompts.

## AIOS Compatibility

AIOS should consume RDW as a skill/tool. AIOS may add thin adapters for packet suggestions, humanizer guards, or reviewable writeback proposals, but RDW pipeline prompts, domain packs, and batch planning belong in this repo.
