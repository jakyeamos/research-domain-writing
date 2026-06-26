# Research Domain Writing

Research Domain Writing is a standalone, local-first writing workflow for producing domain-grounded drafts from explicit research packets, domain packs, style profiles, and QA prompts.

Current state as of 2026-06-26:

- The project has been extracted from AIOS into its own repository.
- Runtime distribution is through slash-command templates and Codex/Cursor/Claude skill installers under `install/`.
- The package uses `uv` with Python 3.12+ metadata in `pyproject.toml`.
- The validator surface is covered by focused tests in `tests/test_rdw_contract.py`.
- Pre-CR changed-line readiness is configured through `.pre-cr.json`, with repo-local LCOV emitted by `scripts/run-pre-cr-python-tests.py`.
- Generated writing outputs are intentionally ignored under `outputs/`, with `.gitkeep` files preserving the expected directory shape.

Quality proof for the extraction:

- `uv run ruff check scripts tests`
- `uv run ruff format --check scripts tests`
- `uv run basedpyright scripts tests`
- `uv run pytest -q`
- `pre-cr run --workspace .`

AIOS integration posture:

- AIOS should consume this repo through installed skills, plugin/CLI/MCP adapters, or explicit workflow invocation.
- AIOS should not own RDW's core prompts, domain packs, packet validator, examples, or release process.
- Future AIOS integration should be adapter-level: packet suggestions, quality/evidence hooks, memory writeback proposals, and optional humanizer guardrails.
