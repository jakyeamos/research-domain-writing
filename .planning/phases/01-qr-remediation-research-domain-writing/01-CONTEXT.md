# Phase 1: QR remediation: research-domain-writing - Context

**Gathered:** 2026-07-04
**Status:** Ready for planning
**Source:** PRD Express Path (/Users/jakyeamos/.local/state/quality-runner/fleet/per-repo-summaries-20260704/research-domain-writing.md)

<domain>
## Phase Boundary

Plan the remediation work for research-domain-writing from Quality Runner run qr-fleet-continue-20260704-research-domain-writing.
This phase is planning-only until execute-phase runs. Quality Runner remains advisory-only: it identifies findings, remediation clusters, and verification suggestions, but all source changes happen in /Users/jakyeamos/projects/research-domain-writing.

Findings: 4
Severity: `blocker` 2, `warning` 2
Categories: `capability` 4
Fleet phase candidate: Phase 1 - Quick Closers
Requirement: QR-RESEARCH-DOMAIN-WRITING

</domain>

<decisions>
## Implementation Decisions

### D-01 - QR summary is the planning source
- Use /Users/jakyeamos/.local/state/quality-runner/fleet/per-repo-summaries-20260704/research-domain-writing.md and the artifacts under /Users/jakyeamos/projects/research-domain-writing/.quality-runner/runs/qr-fleet-continue-20260704-research-domain-writing as the source of truth for this remediation phase.

### D-02 - Cluster-oriented remediation
- Plan and execute coherent remediation batches by QR cluster, not one isolated edit per finding row.

### D-03 - Behavior preservation
- Prefer behavior-preserving refactors, hardening, and simplification. Do not change product behavior unless a QR hardening cluster explicitly requires safer behavior.

### D-04 - Existing project conventions first
- Read the target files and local manifests before editing. Follow existing package-manager, formatter, test, and architecture conventions. Use pnpm for JavaScript package scripts.

### D-05 - Evidence-backed closure
- A cluster is done only when focused repo verification passes and a post-remediation QR run shows the fingerprints cleared or are dispositioned with evidence.

### Claude's Discretion
- Choose exact helper extraction boundaries, naming, and task order when the QR document identifies the finding but not the implementation shape.
- If a cluster turns out to require product, API, or design decisions, stop that cluster and capture the question instead of guessing.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Quality Runner Inputs
- `/Users/jakyeamos/.local/state/quality-runner/fleet/per-repo-summaries-20260704/research-domain-writing.md` - Per-repo QR summary used as this phase PRD.
- `/Users/jakyeamos/projects/research-domain-writing/.quality-runner/runs/qr-fleet-continue-20260704-research-domain-writing/quality-audit.json` - Quality audit report.
- `/Users/jakyeamos/projects/research-domain-writing/.quality-runner/runs/qr-fleet-continue-20260704-research-domain-writing/remediation-plan.json` - QR remediation plan.
- `/Users/jakyeamos/projects/research-domain-writing/.quality-runner/runs/qr-fleet-continue-20260704-research-domain-writing/code-quality-scan.json` - Code-quality scan fingerprints.
- `/Users/jakyeamos/projects/research-domain-writing/.quality-runner/runs/qr-fleet-continue-20260704-research-domain-writing/resolution-ledger.md` - Resolution ledger for closure evidence.
- `/Users/jakyeamos/projects/research-domain-writing/.quality-runner/runs/qr-fleet-continue-20260704-research-domain-writing/agent-handoff.md` - QR agent handoff.

</canonical_refs>

<specifics>
## Top Findings

- `missing-dead-code` blocker capability: Required quality capability is missing: dead_code. Fix: Add a Python dead-code gate such as vulture . --min-confidence 70. Evidence: Capability map lists dead_code as missing.; Missing command capability evidence: no quality command found for dead_code.
- `missing-tests` blocker capability: Required quality capability is missing: tests. Fix: Add a Python test gate such as pytest -q. Evidence: Capability map lists tests as missing.; Missing command capability evidence: no quality command found for tests.
- `missing-pre-pr` warning capability: Required quality capability is missing: pre_pr. Fix: Add a pull_request CI quality gate or document the equivalent pre-PR check. Evidence: Capability map lists pre_pr as missing.; Missing command capability evidence: no quality command found for pre_pr.
- `missing-runtime-smoke` warning capability: Required quality capability is missing: runtime_smoke. Fix: Add a Python smoke gate that exercises installed console scripts. Evidence: Capability map lists runtime_smoke as missing.; Missing command capability evidence: no quality command found for runtime_smoke.

## Remediation Clusters

No active remediation clusters; preserve the zero-finding baseline and verify QR stays clean.

</specifics>

<deferred>
## Deferred Ideas

- Broad rewrites outside the QR clusters.
- Running Quality Runner as an executor or letting QR mutate source code.
- Remediating repos outside research-domain-writing; each repo gets its own GSD phase.

</deferred>

---

*Phase: 1*
*Context gathered: 2026-07-04 via QR per-repo PRD*
