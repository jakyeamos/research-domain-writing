# Release Governance

## Versioning

- Use SemVer-style versions: `MAJOR.MINOR.PATCH`.
- Current release target: `0.1.0`.
- `PATCH`: prompt clarifications, validator fixes, or docs updates that preserve task/output shapes.
- `MINOR`: additive domains, output formats, command templates, or validation fields.
- `MAJOR`: breaking prompt pipeline order, packet schema, install surface, or output contract changes.

## Release Checklist

1. Update version references in `pyproject.toml`, `src/rdw/__init__.py`, `SKILL.md`, install templates, `CHANGELOG.md`, and this file.
2. Update `CHANGELOG.md`.
3. Run quality gates:

```bash
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
```

5. Run wheel smoke:

```bash
python -m venv /tmp/rdw-wheel-smoke
/tmp/rdw-wheel-smoke/bin/pip install dist/*.whl
/tmp/rdw-wheel-smoke/bin/rdw doctor
/tmp/rdw-wheel-smoke/bin/rdw validate-packet knowledge/basketball/demo-guard-2026-demo.yaml --strict
/tmp/rdw-wheel-smoke/bin/rdw task plan --request "explain idempotency keys" --domain technical --out /tmp/rdw-wheel-task
/tmp/rdw-wheel-smoke/bin/rdw batch plan examples/batch-tasks.yaml --out /tmp/rdw-wheel-batch
```

6. Run manual slash smoke after installing templates:

```bash
uv run rdw install --target all
```

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
9. Commit release changes, merge to `main`, tag `v0.1.0`, push `main` and the tag.
10. Publish to PyPI.

## Release Framing

RDW is an agent-first research-grounded writing harness. It creates structured, auditable writing runs; your agent performs research and drafting through explicit prompts.

## AIOS Compatibility

AIOS should consume RDW as a skill/tool. AIOS may add thin adapters for packet suggestions, humanizer guards, or reviewable writeback proposals, but RDW pipeline prompts, domain packs, and batch planning belong in this repo.
