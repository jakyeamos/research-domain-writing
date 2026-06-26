# Release Governance

## Versioning

- Use SemVer-style versions: `MAJOR.MINOR.PATCH`.
- `PATCH`: prompt clarifications, validator fixes, or docs updates that preserve task/output shapes.
- `MINOR`: additive domains, output formats, command templates, or validation fields.
- `MAJOR`: breaking prompt pipeline order, packet schema, install surface, or output contract changes.

## Release Checklist

1. Update `pyproject.toml` version.
2. Update `CHANGELOG.md`.
3. Run:

```bash
uv run ruff check scripts tests
uv run ruff format --check scripts tests
uv run basedpyright scripts tests
uv run pytest -q
pre-cr run --json --workspace .
```

4. Run a manual `/rdw` smoke or dry-run review when prompt behavior changes.
5. Commit release changes.
6. Tag with `vX.Y.Z`.
7. Push `main` and the tag.

## AIOS Compatibility

AIOS should consume RDW as a skill/tool. AIOS may add thin adapters for packet suggestions, humanizer guards, or reviewable writeback proposals, but RDW pipeline prompts, domain packs, and batch CLI work belong in this repo.
