# Changelog

## 0.2.0 - 2026-07-09

- Added lifecycle commands for task and batch status, marking, and resume flows.
- Added JSON Schema export for packet, batch, and task contracts.
- Added provider-neutral adapter stubs and optional adapter extras.
- Added explicit output-format contracts to task planning and prompt bundles.
- Added golden contract coverage and CI quality and wheel-smoke workflows.
- Made explicit planner overrides authoritative in task IDs, topics, and output
  contracts; ambiguous routing now surfaces a warning.
- Added stable JSON diagnostics for validation, planning, doctor, status, resume,
  and lifecycle marking commands.
- Added ordered lifecycle transitions, atomic run projections, append-only batch
  events, transactional package-asset installation, and packaged-resource
  fallback for installed consumers.
- Added canonical root/package asset parity and locked-release CI checks.

## 0.1.0 - 2026-06-26

- Prepared RDW as a GitHub + PyPI product with an installable `rdw` CLI.
- Added deterministic agent-harness commands for doctor, packet validation, batch validation, domain scaffolding, task planning, batch planning, and agent-skill installation.
- Added MIT license, package metadata, package assets, console script entrypoint, and release governance.
- Strengthened packet and batch validation, including strict source-note/fact-id linkage and supported depth/output checks.
- Reworked examples so basketball, music, and technical demos expose task, research/knowledge, draft, QA, and final artifacts.
- Clarified that v0.1 does not browse, call LLM APIs, perform autonomous research, or draft final copy from the CLI.
