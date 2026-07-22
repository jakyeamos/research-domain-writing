# ADR-002: File-backed packet lineage and explicit conflict review

- Status: Accepted for the next implementation slice
- Date: 2026-07-15
- Scope: research-packet revisions produced by one or more task runs
- Builds on: [ADR-001](ADR-001-provider-neutral-adapter-contract.md)

## Decision

RDW will keep one accepted packet head at
`knowledge/<domain>/<packet_id>.yaml` and represent all proposed updates as
inspectable, run-local candidate artifacts. The existing packet `id` remains
the stable logical identity. A candidate may replace the accepted head only
through an explicit promotion operation that passes strict packet validation
and verifies that the candidate was based on the current head.

The first lineage implementation will support:

1. append-only candidate and review artifacts;
2. explicit whole-packet replacement when the parent head still matches; and
3. a human-authored merged candidate recorded with multiple parents.

It will not perform an automatic three-way merge, last-write-wins update, or
silent append. A stale candidate is preserved and turned into a conflict
artifact. An unresolved conflict cannot become the accepted packet head or
advance a task to a final state that depends on that head.

This remains a filesystem model. It adds no database, hosted coordinator, or
provider-specific merge logic.

## Why this fits the current system

The current packet already provides the important semantic anchors:

- `id` is the reusable packet handle;
- `key_facts[].id` identifies atomic claims;
- `source_notes[].fact_ids` links evidence to claims; and
- `used_in_outputs` records downstream reuse.

The planner keeps `packet_id` in task contracts and resolves the canonical
knowledge path from it. The fixture executor already stages artifacts inside a
run-local attempt directory, validates hashes and packet strictness, and only
then promotes them into run-local output paths. Atomic writes and append-only
batch events are existing filesystem primitives. Lineage should extend those
boundaries instead of creating a second storage model.

The current researcher prompt still describes direct writes to
`knowledge/<domain>/<id>.yaml`. That is a legacy external-agent instruction;
the implementation slice following this ADR must change the handoff so the
canonical knowledge path is protected by the promotion gate.

## Artifact model

### Logical packet identity

The tuple `(domain, id)` is the logical packet identity. The canonical accepted
head remains at the existing path:

```text
knowledge/<domain>/<id>.yaml
```

The filename and task-contract `packet_id` do not acquire revision suffixes.
This preserves batch files, planner output, prompt bundles, and existing
knowledge lookups.

### Packet revision metadata

A lineaged packet adds an optional `lineage` mapping to the existing packet
YAML. The packet body remains at the top level so the existing validator and
`research_packet` artifact kind continue to work.

```yaml
lineage:
  schema_version: 1
  revision_id: rev-7f5f7d2c9b4e1a00
  parent_revision_ids: [rev-1c8a4b0e5d6f9012]
  content_sha256: sha256:7f5f7d2c9b4e1a00...
  origin_run_id: task-run-20260715-demo-guard
  created_at: "2026-07-15T20:30:00Z"
  created_by: agent
```

Rules:

- `revision_id` is content-addressed from the normalized packet payload with
  the `lineage` mapping excluded. This makes an identical packet revision
  deduplicable without a registry.
- `content_sha256` is the full integrity hash of that normalized payload. The
  exact canonical serialization belongs to the implementation and must be
  shared by validation and promotion.
- A normal update has one parent. A manually merged revision may list two or
  more parents after a human has resolved the conflicts.
- `origin_run_id`, `created_at`, and `created_by` identify provenance of the
  revision, not truth or confidence. They must not be used to raise confidence
  automatically.
- A legacy packet without `lineage` is read as revision zero. The core derives
  a synthetic legacy revision from its content hash in memory and does not
  rewrite every existing packet during migration.

The accepted head is the packet currently present at the canonical path. No
head index or hidden revision database is required.

### Claim identity and provenance

`key_facts[].id` remains the stable claim identity within a packet lineage.
Reuse an existing fact ID only when the semantic claim and its scope remain the
same. If the value, population, time period, or meaning changes materially,
retire the old ID and add a new one; never recycle an ID for a different claim.

`source_notes[].fact_ids` remains the authoritative claim-to-evidence link.
New lineaged packets may add an optional `source_id` to each source note:

```yaml
source_notes:
  - source_id: source-espn-boxscore-2026-06-26
    source: "Official box score"
    source_type: url
    accessed: "2026-06-26"
    note: "The source supports the games-played and TS% claims."
    fact_ids: [fact-001, fact-003]
```

`source_id` identifies the underlying source record, not one access event.
For a URL, DOI, dataset, or named user-provided file it should remain stable
when only the access date or analyst note changes. Legacy source notes without
`source_id` remain valid and are compared by a deterministic legacy fingerprint
until they are explicitly migrated.

Provenance therefore has three inspectable layers:

1. claim identity and text in `key_facts` or domain metric fields;
2. evidence identity and linkage in `source_notes`; and
3. revision/run provenance in `lineage` and the existing attempt receipt.

No separate claim table, source database, or inferred provenance graph is
needed for the first implementation.

### Candidate, conflict, and resolution artifacts

The candidate packet uses the existing run-local path and artifact kind:

```text
<run-dir>/outputs/research/<packet_id>.yaml
```

The candidate packet carries its proposed `lineage`. It is not the canonical
knowledge packet merely because it passed strict schema validation.

When promotion sees a stale parent or a content collision, it writes a
reviewable conflict artifact beside the candidate:

```text
<run-dir>/outputs/research/<packet_id>-conflict.yaml
```

The minimum shape is:

```yaml
schema_version: 1
kind: packet_conflict
packet_id: basketball-player-demo-guard-2026
candidate_revision_id: rev-bbbbbbbbbbbbbbbb
candidate_parent_revision_ids: [rev-aaaaaaaaaaaaaaaa]
current_revision_id: rev-cccccccccccccccc
status: unresolved
conflicts:
  - conflict_id: conflict-001
    category: claim_collision
    fact_id: fact-003
    source_id: source-boxscore
    base: "59.2% true shooting"
    candidate: "57.9% true shooting"
    current: "60.1% true shooting"
    resolution: null
    resolved_by: null
    resolved_at: null
```

A human decision is a separate artifact, not an edit to history:

```text
<run-dir>/outputs/research/<packet_id>-resolution.yaml
```

```yaml
schema_version: 1
kind: packet_resolution
packet_id: basketball-player-demo-guard-2026
conflict_artifact: outputs/research/basketball-player-demo-guard-2026-conflict.yaml
base_revision_id: rev-aaaaaaaaaaaaaaaa
current_revision_id: rev-cccccccccccccccc
candidate_revision_id: rev-bbbbbbbbbbbbbbbb
status: resolved
action: keep_current
decisions:
  - conflict_id: conflict-001
    action: keep_current
    note: "The current source is newer and the candidate is rejected."
resolved_by: human
resolved_at: "2026-07-15T21:00:00Z"
notes: "Preserve the candidate for audit; do not overwrite the accepted head."
```

Allowed resolution actions are `accept_candidate`, `keep_current`,
`manual_merge`, and `reject_candidate`. `manual_merge` requires a new packet
candidate whose lineage names all selected parents. The resolution artifact
does not itself become a packet or bypass strict validation.

## Promotion and mergeability rules

1. Load the candidate and canonical head by logical packet identity.
2. Strictly validate the candidate, including fact/source linkage and domain
   extensions.
3. Compare the candidate's parent revision to the current accepted head.
4. If the parent matches, require an explicit promotion decision, atomically
   replace the canonical packet, and preserve the candidate and receipt.
5. If the parent does not match, do not write the canonical packet. Preserve
   the candidate, emit a conflict artifact, and mark the run as needing review.
6. If a human resolves the conflict, require a resolution artifact and a new
   strict-valid candidate before promotion.
7. Never delete a candidate, conflict artifact, or prior accepted packet as a
   side effect of resolution.

The first version intentionally chooses append-only review plus explicit
replacement:

- **Safe fast path:** a candidate based on the current head can be explicitly
  accepted as the next whole-packet revision.
- **Concurrent path:** a stale candidate is retained for review even when its
  changes appear disjoint. A human can rebase or manually combine it into a
  new candidate.
- **No automatic merge:** fact IDs and source IDs make collisions inspectable,
  but they do not make semantic equivalence decidable. RDW must not guess.
- **No last-write-wins:** wall-clock order, adapter order, and run completion
  order are not evidence quality signals.

## Conflict categories

| Category | Meaning | Automatic action |
| --- | --- | --- |
| `stale_parent` | Candidate was based on a revision other than the current head. | Preserve candidate; require review. |
| `claim_collision` | The same fact ID changed between the candidate branch and current head. | Preserve both values; require a decision. |
| `source_collision` | The same source identity changed in a way that affects provenance or linkage. | Preserve both records; require a decision. |
| `identity_collision` | Domain, packet ID, entity, or time scope does not identify the same logical packet. | Reject promotion; create a new packet or corrected candidate. |
| `evidence_regression` | Candidate removes source linkage, weakens an evidence boundary, or drops supported claims without an explicit decision. | Block promotion; require review. |
| `schema_invalid` | Candidate fails packet/schema/domain validation. | Reject promotion; produce validation diagnostics, not a merge. |

`stale_parent` is sufficient to block promotion. The more specific collision
categories make the human review useful and should be emitted when a base
revision is available for comparison.

## Concurrent update examples

### Example 1: conflicting value for the same claim

Two research runs both read head `rev-aaaaaaaaaaaaaaaa` for Demo Guard.

- Run A proposes `fact-003 = 60.1% true shooting` with a newer source and is
  explicitly promoted to `rev-cccccccccccccccc`.
- Run B proposes `fact-003 = 57.9% true shooting` from the old head and finishes
  afterward.
- Run B's parent no longer matches. The core keeps B's candidate, writes
  `stale_parent` and `claim_collision` records, and leaves the canonical packet
  at `rev-cccccccccccccccc`.
- A human can keep A, reject B, or author a new packet revision that explains
  why both values apply to different samples or time periods. No value is
  silently selected by completion time.

### Example 2: disjoint additions from the same head

Two runs both read `rev-aaaaaaaaaaaaaaaa`.

- Run A adds `fact-005` about playoff efficiency with `source-playoffs` and is
  promoted first.
- Run B adds `fact-006` about on/off performance with `source-onoff`.
- Even though the fact IDs do not overlap, B is stale relative to the current
  head. V1 records `stale_parent` instead of assuming that the additions are
  semantically independent.
- A reviewer may create a new candidate containing the current head plus both
  facts, with `parent_revision_ids` containing A and B, then validate and
  explicitly promote that candidate. The review and the resulting two-parent
  revision preserve how the merge was decided.

## Safety rules for unresolved conflicts

- `status: unresolved` is review-required and must propagate to task/output
  metadata as `needs_review: true`.
- An unresolved candidate cannot replace the canonical packet or support a
  final artifact that claims to use the accepted head.
- Existing accepted packets remain readable and usable for tasks that do not
  opt into the candidate.
- Candidate, conflict, receipt, and resolution artifacts remain inspectable for
  audit and retry; retries create new attempt directories.
- A conflict resolver may not raise `confidence_level`, remove source links,
  or discard uncertainty without recording the human decision and evidence.
- Malformed or identity-mismatched artifacts are rejected as validation errors,
  not coerced into merge inputs.

## Compatibility and migration impact

### Existing packet validation

No existing packet needs to be rewritten for the first implementation.
`validate_packet` already checks required fields, strict fact IDs, source-note
linkage, dates, confidence, and domain extensions. The exported packet schema
allows additional properties. `lineage` and `source_id` can therefore be
introduced as optional fields without invalidating legacy packets.

The next implementation should add opt-in validation for lineaged packets:

- required `revision_id`, `parent_revision_ids`, `content_sha256`, and origin
  metadata when `lineage` is present;
- unique fact IDs and source IDs within a packet;
- valid references from source notes to fact IDs; and
- deterministic content-hash verification.

Legacy packets should be read through the synthetic content-hash revision and
only gain persisted lineage when a candidate is explicitly accepted.

### Task, batch, and output paths

- `packet_id` remains the logical reference in batch YAML and task contracts.
- `local_knowledge_paths` continues to point to the canonical packet path.
- Existing `research_packet` receipt artifacts and run-local output paths stay
  unchanged; lineage is carried inside the packet and review artifacts.
- Batch planning does not need to understand revisions. A future executor must
  block canonical promotion and batch completion when a packet conflict is
  unresolved.
- The direct-write researcher prompt must be migrated to stage candidates in a
  run directory. Until then, the prompt remains a documented legacy behavior,
  not an authority that can bypass the deterministic promotion gate.

Rollback is a git/file restoration plus retention of run-local candidate and
review artifacts. No database migration or destructive packet rewrite is
required.

## Alternatives considered

### Automatic three-way merge by fact and source ID

Rejected for v1. Matching identifiers can detect likely collisions, but they
cannot decide whether changed scope, sample, wording, confidence, or source
quality preserves the same meaning. An opaque merge would violate grounding
before fluency.

### Last-write-wins replacement

Rejected. It silently loses evidence and makes run completion order a hidden
quality rule.

### Hidden database or hosted revision service

Rejected. It would break the local-first, inspectable artifact model before the
repository has demonstrated a scale problem that requires it.

### Duplicate packet IDs per revision

Rejected. Revision suffixes would break existing task contracts, batch files,
knowledge lookup, and downstream output references. Revision metadata belongs
inside the packet and review artifacts while the logical ID remains stable.

## Implementation and verification handoff

The next implementation slice should add a small lineage module and focused
fixtures, not a general synchronization framework. It must prove:

- legacy packet reads derive a stable synthetic head without rewriting files;
- matching-head candidate promotion creates one new revision and preserves the
  prior candidate/receipt;
- stale candidates create conflict artifacts and never overwrite the head;
- both overlapping and disjoint concurrent updates remain reviewable;
- resolution artifacts cannot bypass strict packet validation;
- unresolved conflicts propagate `needs_review` and block final promotion; and
- task/batch packet IDs and current output paths remain compatible.

The TMCP architecture review plan `tmcp-review-plan-5333ad59` completed with
all evidence validations passing. Its scores were source grounding 3/4, risk
priority 2/4, verification readiness 3/4, and scope control 3/4. The review's
primary warning was the stale-parent overwrite risk; its recommended remedy is
the parent-head check, conflict artifact, and promotion block adopted here.
