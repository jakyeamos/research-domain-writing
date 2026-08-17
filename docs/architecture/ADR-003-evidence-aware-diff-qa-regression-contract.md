# ADR-003: Evidence-aware diff QA regression contract

- Status: Accepted for the next implementation slice
- Date: 2026-07-15
- Scope: deterministic comparison of research packets, draft claim ledgers, and machine-readable domain rules
- Builds on: [ADR-001](ADR-001-provider-neutral-adapter-contract.md) and [ADR-002](ADR-002-packet-lineage-and-conflict-resolution.md)

## Decision

RDW will add an evidence-aware diff QA contract as a deterministic companion to
the existing QA artifact. The first implementation will compare normalized,
structured evidence representations rather than arbitrary Markdown or model
judgments.

The comparison must answer a narrower question than a prose diff:

> Did the candidate add, remove, alter, or weaken a claim, its evidence,
> uncertainty, or a machine-readable domain rule relative to an explicitly
> approved baseline?

The contract has two modes:

1. **Packet mode** compares the structured fields already present in a
   knowledge packet. `key_facts[].id` is the stable claim identity and
   `source_notes[].fact_ids` is the authoritative claim-to-evidence link.
2. **Draft mode** compares an explicit claim ledger beside a draft. RDW will
   not pretend that it can reliably extract semantic claims from freeform
   Markdown in a deterministic first version. A draft without a claim ledger
   produces an indeterminate, review-required result and can never receive an
   automatic diff-QA pass.

Machine-readable domain rule snapshots are optional inputs to both modes. The
current Markdown checklists remain useful human guidance, but they cannot be
treated as an automatically diffable rule set until they have stable rule IDs
and structured results.

The report is additive. It does not replace the existing
`outputs/qa/<output_id>-qa.yaml` artifact or its `blocker | major | minor`
severity vocabulary. It adds a `diff_qa` artifact that can block promotion or
make the required human review explicit.

## Why this is the right boundary

The current pipeline already separates knowledge, drafting, QA, and style work:

- the domain QA prompt treats grounding as a gate before the humanizer;
- packets have stable fact IDs and source-note links;
- the fixture executor validates receipts and promotes only validated
  run-local artifacts; and
- lifecycle status already distinguishes `qa-passed`, `qa-failed`, and
  `final-done`.

The current QA validator, however, only requires `qa.pass` to be a boolean.
Freeform drafts do not carry claim IDs, and domain checklists are readable
Markdown rather than machine-readable rules. Comparing only the boolean would
miss evidence regressions; comparing raw prose would mistake style changes for
grounding changes. Requiring structured representations makes missing evidence
visible instead of silently treating an uncheckable candidate as safe.

This ADR therefore keeps three responsibilities separate:

| Responsibility | Deterministic diff QA | Human review or humanizer |
| --- | --- | --- |
| Claim identity and additions/removals | Yes, when stable IDs exist | Review ambiguous identity changes |
| Claim-to-source linkage | Yes | Review source quality or relevance |
| Required uncertainty and caveats | Yes, when represented as fields | Review nuanced wording and scope |
| Machine-readable domain rules | Yes, when rules have stable IDs | Define or revise the rules |
| Markdown rhythm, voice, elegance, and style | No | Humanizer and human review |
| Semantic equivalence of unstructured prose | No | Human review; no automatic pass |

## Comparison units

### Packet mode

Packet mode uses a normalized claim/source graph derived from the packet YAML.
The first version treats the following as semantic inputs:

- packet logical identity: `(domain, id)`;
- packet revision identity from [ADR-002](ADR-002-packet-lineage-and-conflict-resolution.md),
  or a deterministic legacy content hash when lineage is absent;
- `key_facts[].id` and `key_facts[].text`;
- explicit structured values such as `relevant_metrics`, when they are
  explicitly linked to a fact or source;
- source identity and source metadata from `source_notes`;
- claim-to-source links from `source_notes[].fact_ids`;
- explicit uncertainty requirements and uncertainty entries; and
- an optional machine-readable domain-rule snapshot.

`interpretation_notes`, prose ordering, YAML ordering, and presentation-only
metadata are not independent claims. They may still be included in the
artifact hash, but they do not create a semantic diff finding.

The existing packet format permits extension fields. For the first
implementation, a `key_facts` record is the authoritative claim unit. A
`relevant_metrics` entry becomes an independent claim unit only when it carries
stable linkage such as `fact_ids` or `source_ids`. An unlinked new or changed
metric cannot be auto-approved; it produces an unsupported or indeterminate
finding rather than being silently treated as context.

### Draft mode

Draft mode requires a sidecar claim ledger. A draft frontmatter entry may point
to it, or the executor may resolve the conventional path
`outputs/qa/<output_id>-claims.yaml`.

The ledger is a structured QA attestation, not a claim extractor. It gives the
deterministic core stable identifiers and evidence links; it does not prove
that a prose sentence is faithfully represented by its ledger entry. That
semantic responsibility remains with the existing QA stage and human review.

Minimum ledger shape:

```yaml
schema_version: 1
kind: draft_claim_ledger
output_id: demo-guard-profile
draft_path: outputs/drafts/demo-guard-profile.md
claims:
  - claim_id: fact-001
    text: "The player averaged 18.4 points per game."
    fact_ids: [fact-001]
    source_ids: [source-boxscore]
    uncertainty: required
    location: "paragraph-2"
    required: true
rules:
  - rule_id: basketball.stats.must-show-sample
    status: pass
    evidence: "The paragraph names the 2025-26 sample."
```

The ledger must contain stable claim IDs, normalized evidence links, and any
required uncertainty state needed by the output contract. If it is missing,
malformed, or cannot be matched to the draft/baseline, the result is
`indeterminate` and `needs_human_review: true`; it is never an automatic pass.

### Source identity

An explicit `source_id` is preferred. A legacy source note without one is
identified by a deterministic fingerprint of its normalized source identity
and source type. Access date and analyst note changes must not accidentally
turn the same underlying source into a different source identity, but a source
whose identity or evidence boundary changes must be reported for review.

The diff engine may verify that a source link exists. It must not infer source
quality, credibility, recency, or semantic relevance from a URL, title, or
source type alone.

## Normalized representation

The implementation should compare a typed normalized representation equivalent
to the following shape. This is a contract shape, not a requirement to expose a
new public Python API before the implementation slice is planned.

```yaml
schema_version: 1
artifact_kind: packet
logical_id:
  domain: basketball
  packet_id: basketball-player-demo-guard-2026
revision_id: rev-7f5f7d2c9b4e1a00
claims:
  - claim_id: fact-001
    kind: fact
    text_normalized: "the player averaged 18.4 points per game."
    fact_ids: [fact-001]
    source_ids: [source-boxscore]
    uncertainty: none
    required: false
sources:
  - source_id: source-boxscore
    source_normalized: "official box score"
    source_type: url
    fact_ids: [fact-001]
rules:
  - rule_id: basketball.stats.must-show-sample
    status: pass
```

Normalization rules:

1. Preserve stable IDs, numeric values, units, population, time period, and
   scope. Do not normalize away meaning.
2. Normalize only safe whitespace, line-ending, and case differences where the
   field is explicitly declared case-insensitive.
3. Sort claims, source IDs, fact IDs, and rule IDs by stable identifier. Array
   order alone is not a change.
4. Preserve an explicit `none`, `required`, or `unknown` uncertainty state;
   absence is not equivalent to a verified lack of uncertainty.
5. Do not fuzzy-match claim text, infer that two metrics are equivalent, or use
   an LLM to choose a correspondence. A changed stable ID is an addition and
   removal unless an explicit human mapping is supplied later.
6. Exclude timestamps, absolute paths, generated run IDs, and presentation
   ordering from golden semantic output. Preserve artifact hashes and paths in
   the report for auditability.

If a field needed for a comparison is absent, the normalizer must surface the
absence. It must not manufacture a confident default.

## Baseline approval

Diff QA compares against an immutable, explicitly approved baseline. A moving
file path or the latest accepted packet head is not approval by itself.

The first version uses a small manifest artifact:

```yaml
schema_version: 1
kind: diff_baseline
baseline_id: baseline-demo-guard-2026-001
artifact_kind: packet
artifact_path: knowledge/basketball/demo-guard-2026.yaml
content_sha256: sha256:7f5f7d2c9b4e1a00...
packet_id: basketball-player-demo-2026
packet_revision_id: rev-7f5f7d2c9b4e1a00
qa_status: pass
approved: true
approved_by: human
approved_at: "2026-07-15T21:00:00Z"
```

Before comparison, the engine must verify:

- the manifest is structurally valid and explicitly approved;
- the baseline bytes still match `content_sha256`;
- a packet baseline passes strict packet and domain validation;
- a draft baseline has a passing QA artifact and a valid claim ledger;
- the claimed packet or output identity matches the artifact; and
- the baseline is not itself indeterminate, blocked, or awaiting review.

Any failure emits `DQA-001 baseline_invalid` and blocks an automatic pass. A
legacy packet may use a synthetic revision derived from its content hash, but
the hash must still be pinned in the manifest. `final-done` is evidence that a
previous pipeline completed; it is not a substitute for explicit baseline
approval.

The candidate is hashed at comparison time. A report that names a baseline and
candidate without content hashes is not auditable and must be rejected by the
future report validator.

## Diff report artifact

The report is written beside the existing QA artifact as
`outputs/qa/<output_id>-diff.yaml` and has artifact kind `diff_qa`.

```yaml
schema_version: 1
kind: diff_qa
output_id: demo-guard-profile
comparison:
  mode: packet
  baseline:
    artifact_kind: packet
    path: knowledge/basketball/demo-guard-2026.yaml
    sha256: sha256:1111111111111111...
    packet_id: basketball-player-demo-guard-2026
    packet_revision_id: rev-aaaaaaaaaaaaaaaa
    baseline_id: baseline-demo-guard-2026-001
  candidate:
    artifact_kind: packet
    path: outputs/research/basketball-player-demo-guard-2026.yaml
    sha256: sha256:2222222222222222...
    packet_id: basketball-player-demo-guard-2026
    packet_revision_id: rev-bbbbbbbbbbbbbbbb
summary:
  status: pass
  pass: true
  needs_human_review: false
  blocking_issue_count: 0
  major_issue_count: 0
  minor_issue_count: 0
  counts:
    claims_added: 1
    claims_removed: 0
    claims_changed: 0
    source_links_removed: 0
    uncertainty_removed: 0
    rules_regressed: 0
issues: []
```

When issues exist, each issue has stable diagnostic data:

```yaml
issues:
  - id: dqa-0001
    code: DQA-002
    severity: blocker
    category: unsupported_claim
    subject_type: fact
    subject_id: fact-006
    baseline: null
    candidate:
      claim_id: fact-006
      source_ids: []
    evidence:
      - "candidate key_facts.fact-006 has no source_notes.fact_ids link"
    description: "The candidate adds a claim without linked evidence."
    suggested_fix: "Add a valid source link or remove the claim."
```

The generated issue ID is only a report-local stable identifier. The `DQA-*`
code is the durable vocabulary used by tests, fixtures, and downstream review.
Reports must use deterministic ordering for issues and counts. Generated time,
absolute paths, and run-specific IDs must be excluded from golden comparisons.

## Diagnostic vocabulary and severity

The following codes are normative for the first implementation:

| Code | Category | Default severity | Meaning and automatic result |
| --- | --- | --- | --- |
| `DQA-001` | `baseline_invalid` | blocker | Baseline is missing, unapproved, hash-mismatched, identity-mismatched, or fails strict validation. Block automatic pass. |
| `DQA-002` | `unsupported_claim` | blocker | Candidate claim has no valid fact/source support, or a new structured metric lacks required evidence linkage. Block automatic pass. |
| `DQA-003` | `evidence_removed` | major | An existing claim remains while its source links or evidence boundary are removed or weakened. Block automatic pass unless an explicit human decision exists. |
| `DQA-004` | `claim_changed` | major | A stable claim ID changes in text, value, unit, scope, population, or time period. Require review; do not infer equivalence. |
| `DQA-005` | `claim_removed` | minor by default | A claim is absent from the candidate. Optional removals may pass with review; required removals are major. |
| `DQA-006` | `uncertainty_removed` | major | Required uncertainty, caveat, or hedge is removed, or confidence is raised without the evidence needed by the contract. Block automatic pass. |
| `DQA-007` | `rule_regression` | major | A baseline machine rule passed and the candidate fails it. A candidate `unknown` is indeterminate, not a pass. |
| `DQA-008` | `source_changed` | major | Source identity or source evidence boundary changes. The engine reports the change; it does not score source quality. |
| `DQA-009` | `ledger_missing` | major | Draft mode has no valid explicit claim ledger. Result is indeterminate and review-required, never pass. |
| `DQA-010` | `indeterminate` | major | Required representation, correspondence, uncertainty state, or rule result cannot be compared deterministically. Result is indeterminate and review-required. |

Severity can be raised by the output contract. For example, removing a
required claim is major even though optional claim removal is minor. A minor
finding may coexist with `status: pass`, but it sets
`needs_human_review: true` unless a later policy explicitly permits
minor-only auto-approval.

## Outcome semantics

The report summary has exactly one of three statuses:

- `pass`: baseline and candidate are valid, all required representations are
  present, and there are no blocker, major, or indeterminate findings. A
  supported new claim is counted as an addition and is not a finding by itself.
- `fail`: at least one blocker or major finding exists. The candidate cannot
  advance to final promotion through the automatic lifecycle.
- `indeterminate`: the engine lacks a required ledger, rule snapshot, stable
  correspondence, or other representation needed to make a safe deterministic
  decision. `pass` must be `false`, `needs_human_review` must be `true`, and
  no final promotion is allowed.

The `pass` boolean is retained for compatibility with the current QA artifact,
but it must be derived from `status == pass`; it must never override an
indeterminate status. The report must also include counts for additions,
removals, changed claims, removed source links, removed uncertainty, and rule
regressions so a reviewer can distinguish an ordinary supported expansion from
a grounding regression.

Specific comparison semantics:

- adding a claim with valid evidence is a supported addition and may pass;
- adding a claim without valid evidence is `DQA-002`;
- adding uncertainty is not a regression;
- removing required uncertainty is `DQA-006`;
- removing an optional claim is a minor review finding by default;
- removing a required claim is major;
- keeping a claim while removing all supporting source links is
  `DQA-003`;
- changing a source identity or evidence boundary is `DQA-008`;
- a baseline rule `pass` followed by candidate `fail` is `DQA-007`;
- a baseline or candidate rule `unknown` makes the comparison indeterminate;
  and
- raw Markdown wording or styling changes are outside semantic diff QA unless
  they are represented by a claim ledger field that changed.

## Lifecycle and human review integration

The existing QA artifact remains the agent-level QA result. The diff report is
an additional gate in the same task attempt:

1. `draft-done` may produce the ordinary QA artifact and the diff report.
2. Only `diff_qa.status: pass` may advance the task to `qa-passed`.
3. `fail` and `indeterminate` advance to `qa-failed` with a reason that names
   the report status and diagnostic codes. The candidate and report remain in
   the run-local artifact directory.
4. `final-done` is prohibited unless the diff report passed. A future explicit
   human override may be added as a separate artifact, but v1 does not silently
   infer one from a note, a path, or a prior final artifact.
5. Minor-only findings may leave the task at `qa-passed` with
   `needs_review: true`, consistent with the existing lifecycle's review
   semantics. Final promotion still carries that review flag.
6. Batch-log events retain their existing fields and add diff status, codes,
   and `needs_review` only through a backward-compatible extension.

Human decisions must remain inspectable artifacts. The baseline manifest is the
first explicit approval artifact. A later implementation may add a
`diff_qa-resolution.yaml` for an authorized decision on a finding; such a
resolution must name the report hash, diagnostic code, reviewer, decision, and
reason. It must not mutate the original report or erase the failing candidate.

## Fixture and golden-output contract

The first fixture suite should use the existing Demo Guard basketball packet
and vertical-slice artifact layout. Each fixture runs locally without a model,
network, database, browser, or provider credential. Goldens compare normalized
stable fields and ignore timestamps, absolute paths, and run-local IDs.

| Fixture | Change | Expected result |
| --- | --- | --- |
| `packet-add-supported` | Add `fact-005` with a valid source link. | `pass`; `claims_added: 1`; no DQA finding. |
| `packet-add-unsupported` | Add `fact-006` without a source link. | `fail`; blocker `DQA-002`; no final promotion. |
| `packet-source-weakened` | Keep a claim but remove its source link or replace its evidence boundary. | `fail`; `DQA-003` or `DQA-008` at major severity. |
| `packet-uncertainty-removed` | Remove a required uncertainty or caveat. | `fail`; major `DQA-006`. |
| `packet-claim-changed` | Reuse a fact ID while changing value, unit, scope, or period. | `fail`; major `DQA-004`. |
| `packet-claim-removed-optional` | Remove an optional fact. | `pass` with minor `DQA-005` and human review. |
| `packet-claim-removed-required` | Remove a required fact. | `fail`; major `DQA-005`. |
| `draft-ledger-missing` | Compare Markdown drafts without a claim ledger. | `indeterminate`; `DQA-009`; never false-pass. |
| `draft-ledger-supported` | Add a ledger claim with valid fact/source links. | `pass`; supported addition counted. |
| `rule-regression` | Change a stable rule from `pass` to `fail`. | `fail`; major `DQA-007`. |
| `rule-unknown` | Remove a rule result or change it to `unknown`. | `indeterminate`; `DQA-010`; review required. |
| `baseline-hash-mismatch` | Modify the approved baseline after manifest creation. | `fail`; blocker `DQA-001`. |

Each golden should assert at least:

- status and derived pass boolean;
- needs-review behavior;
- blocker/major/minor counts;
- stable diagnostic codes and subject IDs;
- claim/source/uncertainty/rule counters;
- lifecycle outcome and absence of final promotion for fail/indeterminate; and
- preservation of candidate and report artifacts for review.

The implementation may add more fixtures as regressions are found, but a
fixture should protect a contract or confirmed failure rather than merely
increase coverage.

## False-positive and false-negative controls

The first version deliberately prefers a reviewable indeterminate result over
a confident guess:

- only safe normalization is automatic;
- stable IDs, not fuzzy text similarity, determine correspondence;
- source quality and semantic relevance are not auto-scored;
- order-only changes are ignored;
- supported additions are not regressions;
- intentional removals require `required: false` or a later explicit review
  decision; and
- absent ledgers, absent rule snapshots, unknown rule results, and ambiguous
  claim mapping cannot pass.

This means the contract can miss a semantic change hidden behind a dishonest or
incorrect ledger. That is an intentional boundary: the ledger makes the
attestation inspectable, while the existing QA and human review remain
responsible for checking the prose against the evidence. Adding an LLM judge to
the deterministic core would make the result less reproducible and would cross
the provider-runtime boundary established by ADR-001.

## Alternatives considered

### Raw text or Markdown diff

Rejected. It over-reports harmless rewrites, under-reports evidence-link
changes, and cannot distinguish style from a changed factual claim.

### LLM semantic judge

Rejected for v1. It is provider-dependent, non-deterministic, harder to replay,
and weakens the local-first contract. It may be a later review aid, but its
output cannot replace the deterministic gate.

### Compare only the current QA boolean

Rejected. The existing boolean does not identify which claims, sources,
uncertainty requirements, or domain rules changed.

### Latest-path or last-write baseline

Rejected. A moving path is not an approved baseline and can silently bless
unreviewed drift or concurrent updates.

### Automatic claim merge

Rejected. Stable IDs make collisions visible but do not make semantic
equivalence decidable. Conflict preservation follows ADR-002.

## Implementation handoff

The next implementation slice should:

1. add a small typed normalizer and diff engine, likely in
   `src/rdw/diff_qa.py` or `src/rdw/qa_diff.py`;
2. validate baseline manifests, draft ledgers, normalized records, and report
   schemas without weakening current packet validation;
3. add the fixture and golden suite above;
4. extend the fixture executor to validate and promote a `diff_qa` companion
   artifact while preserving the existing QA artifact;
5. connect `pass`, `fail`, and `indeterminate` to lifecycle transitions and
   batch-log diagnostics; and
6. keep provider adapters, browsing, model judges, and databases outside this
   deterministic core.

The implementation must not silently infer draft claims from Markdown, score
source quality, or turn the current human-readable checklists into automated
rules without stable IDs and structured results.

## Review evidence

The TMCP test-strategy review for this contract completed successfully as
`tmcp-review-plan-5ec3d9c0`. All packet, playbook, rubric, evidence, finding,
and remediation validations passed. The review scored source grounding 3/4,
risk priority 2/4, verification readiness 3/4, and scope control 3/4; its
substance check was 4/4. The principal finding was that the current execution
checks only `qa.pass`, while freeform drafts lack machine claim IDs and domain
checklists lack stable rule IDs. This ADR resolves that gap by making normalized
claims or an explicit claim ledger and rule snapshot prerequisites for an
automatic pass.
