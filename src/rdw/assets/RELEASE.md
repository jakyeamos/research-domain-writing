# Release Governance

## Versioning

- Use SemVer-style versions: `MAJOR.MINOR.PATCH`.
- Current release target: `0.2.2`.
- `pyproject.toml` is the package version source; the new `v0.2.2` tag and
  PyPI's current `v0.1.0` release are separate states until publication.
- `PATCH`: prompt clarifications, validator fixes, or docs updates that preserve task/output shapes.
- `MINOR`: additive domains, output formats, command templates, or validation fields.
- `MAJOR`: breaking prompt pipeline order, packet schema, install surface, or output contract changes.

## Release Checklist

1. Update the version in `pyproject.toml`, then synchronize package assets with `scripts/sync-package-assets.py`.
2. Update `CHANGELOG.md`.
3. Run quality gates:

```bash
uv sync --locked
uv lock --check
uv run python scripts/sync-package-assets.py --check
shellcheck scripts/*.sh
uv run ruff check .
uv run ruff format --check .
uv run basedpyright src tests scripts
uv run pytest -q
uv build
```

4. Run CLI smoke:

```bash
uv run rdw --version
uv run rdw doctor
uv run rdw validate-packet knowledge/basketball/demo-guard-2026-demo.yaml --strict
uv run rdw validate-batch examples/batch-tasks.yaml
uv run rdw task plan --request "improve the copy on my LIS leaderboard" --out /tmp/rdw-task-smoke
uv run rdw status /tmp/rdw-task-smoke
uv run rdw task mark research-done /tmp/rdw-task-smoke
uv run rdw batch plan examples/batch-tasks.yaml --out /tmp/rdw-batch-smoke
uv run rdw batch status /tmp/rdw-batch-smoke
uv run rdw batch resume /tmp/rdw-batch-smoke
uv run rdw schema task-contract --format jsonschema -o /tmp/rdw-task-contract.schema.json
```

Execution is agent-owned: do not substitute an undocumented `rdw task execute`
command for the prompt-bundle handoff described in `README.md`.

5. Run wheel smoke:

```bash
python -m venv /tmp/rdw-wheel-smoke
/tmp/rdw-wheel-smoke/bin/pip install dist/*.whl
ASSET_ROOT=$(/tmp/rdw-wheel-smoke/bin/python -c 'from importlib.resources import files; print(files("rdw.assets"))')
/tmp/rdw-wheel-smoke/bin/rdw --version
/tmp/rdw-wheel-smoke/bin/rdw doctor
/tmp/rdw-wheel-smoke/bin/rdw validate-packet "$ASSET_ROOT/knowledge/basketball/demo-guard-2026-demo.yaml" --strict --root "$ASSET_ROOT"
/tmp/rdw-wheel-smoke/bin/rdw validate-batch "$ASSET_ROOT/examples/batch-tasks.yaml" --root "$ASSET_ROOT"
/tmp/rdw-wheel-smoke/bin/rdw task plan --request "explain idempotency keys" --domain technical --out /tmp/rdw-wheel-task --root "$ASSET_ROOT"
/tmp/rdw-wheel-smoke/bin/rdw batch plan "$ASSET_ROOT/examples/batch-tasks.yaml" --out /tmp/rdw-wheel-batch --root "$ASSET_ROOT"
/tmp/rdw-wheel-smoke/bin/rdw schema task-contract --format jsonschema -o /tmp/rdw-wheel-task-contract.schema.json
/tmp/rdw-wheel-smoke/bin/rdw install --target all --home /tmp/rdw-wheel-home
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
9. Confirm `git diff --check` is clean and `.tracker/PROJECT_TRUTH.md` records the final verification state.
10. Commit release changes, merge to `main`, tag `v0.2.2`, push `main` and the tag.
11. Publish to PyPI only after the tag and registry state are verified.

For an interactive PyPI token and publish flow, run:

```bash
scripts/publish-pypi-wizard.sh
```

The wizard opens the PyPI token page, captures the token with hidden input, rebuilds/verifies artifacts, runs a dry-run check, and only publishes after a final confirmation. It does not write the PyPI token to disk.

## Release Framing

RDW is an agent-first research-grounded writing harness. It creates structured, auditable writing runs; your agent performs research and drafting through explicit prompts.

## AIOS Compatibility

AIOS should consume RDW as a skill/tool. AIOS may add thin adapters for packet suggestions, humanizer guards, or reviewable writeback proposals, but RDW pipeline prompts, domain packs, and batch planning belong in this repo.
