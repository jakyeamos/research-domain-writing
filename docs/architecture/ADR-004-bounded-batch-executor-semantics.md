# ADR-004: Bounded filesystem-first batch executor semantics

- Status: Accepted for the next implementation slice
- Date: 2026-07-15
- Scope: Scheduling and operator control for a planned batch of independent RDW task runs
- Builds on: [ADR-001](ADR-001-provider-neutral-adapter-contract.md), [ADR-002](ADR-002-packet-lineage-and-conflict-resolution.md), and [ADR-003](ADR-003-evidence-aware-diff-qa-regression-contract.md)

## Decision

RDW will add a bounded, filesystem-first batch executor that composes the
existing one-task adapter and lifecycle contracts. The executor owns batch
scheduling, task leases, retry policy, pause/cancel intent, and batch outcome
projection. It does not own research, drafting, provider credentials, or
canonical content promotion.

The first implementation slice is deliberately serial:

- one executor writer may own a batch at a time;
- one task attempt may run at a time;
- tasks dispatch in the input order recorded by `summary.yaml`;
- the initially supported `max_concurrency` is `1`; and
- a later concurrency slice may raise the limit only after same-packet locking
  and event-replay tests exist.

This is still a batch executor: it runs planned tasks, resumes work after a
pause or interruption, retries explicitly retryable failures within a finite
budget, continues independent tasks after review or failure, and leaves a
durable partial outcome. It is not a general-purpose agent orchestration
platform.

The source of truth remains the batch event stream and task attempt receipts.
`summary.yaml` and task `status.json` remain projections and compatibility
artifacts. Completed task artifacts are never rolled back because another task
fails, is cancelled, or needs review.

## Context and boundaries

The current system has a useful but incomplete shape:

- `plan_batch` creates independent task folders, a `summary.yaml` projection,
  and initial `planned` events;
- `execute_fixture` proves the one-task receipt, hash, artifact, and lifecycle
  boundary;
- `lifecycle.py` owns legal task transitions, summary counts, and append-only
  batch events; and
- [ADR-001](ADR-001-provider-neutral-adapter-contract.md) keeps batch
  scheduling, retry budgets, and cancellation outside the adapter contract.

`prompts/batch-runner.md` currently tells an agent to execute each planned task
in its session but does not define ordering, ownership, retries, pause/cancel
behavior, or partial outcomes. This ADR fills that gap without moving provider
behavior into the deterministic core.

The executor covers ordering, ownership, retries, time and attempt limits,
pause/cancel controls, review gates, partial outcomes, and recovery. It does not
add model APIs, browsing, a hosted queue, a database, distributed locks,
provider-specific cost accounting, automatic packet merges, or all-or-nothing
rollback.

## Artifact ownership

The current batch paths remain stable:

```text
<batch-dir>/
  summary.yaml
  batch-log.jsonl
  executor-lease.json
  tasks/<task_id>/
    task-contract.yaml
    prompt-bundle.md
    status.json
    adapter-runs/<adapter>/<attempt_id>/receipt.json
```

`batch-log.jsonl` is the append-only source of truth for accepted executor
actions and outcomes. New executor events use this versioned shape:

```json
{
  "schema_version": 1,
  "event_id": "evt-3d9d...",
  "sequence": 12,
  "event_type": "task-attempt-started",
  "batch_id": "demo-batch-001",
  "execution_id": "exec-20260715-001",
  "command_id": "cmd-20260715-001",
  "task_id": "batch-demo-guard-summary",
  "attempt_id": "attempt-20260715T210000Z-a1b2c3d4",
  "idempotency_key": "sha256:...",
  "at": "2026-07-15T21:00:00Z",
  "payload": {"requested_stages": ["research", "draft", "qa", "final"]}
}
```

Planner-created lines are legacy version-0 records and remain readable. The
executor does not rewrite them. New events append with `O_APPEND` and fsync
through the existing `append_jsonl` primitive while the batch lease prevents
competing writers.

Every new event has a stable `event_id`, monotonic sequence, event type,
command ID, UTC timestamp, and relevant task/attempt IDs. Secrets, prompts
containing credentials, and provider tokens never enter the event stream. The
reducer ignores a duplicate event ID, so replaying a log cannot duplicate a
projection or side effect.

`summary.yaml` keeps the existing top-level fields and adds an executor
projection:

```yaml
batch_id: demo-batch-001
status: in_progress
task_count: 3
completed: 1
needs_review: 1
failed: 1
tasks:
  - task_id: batch-demo-guard-summary
    status: final-done
    executor_state: succeeded
  - task_id: batch-album-blurb
    status: qa-failed
    executor_state: needs-review
  - task_id: batch-idempotency
    status: planned
    executor_state: queued
executor:
  schema_version: 1
  state: completed-with-failures
  execution_id: exec-20260715-001
  policy:
    max_concurrency: 1
    max_attempts: 2
    failure_policy: continue
  completed: 1
  failed: 1
  needs_review: 1
  cancelled: 0
  pending: 0
  last_sequence: 17
```

The existing top-level `status` remains a compatibility projection: `planned`
when no task has advanced, `in_progress` while work or unresolved outcomes
remain, and `complete` only when every task is `final-done`. The exact outcome
lives in `executor.state`; a batch may therefore be
`completed-with-failures` while old readers still see `status: in_progress`.

Each task `status.json` keeps its pipeline `status` and gains an optional
executor mapping. Old readers ignore it:

```json
{
  "task_id": "batch-demo-guard-summary",
  "status": "planned",
  "executor": {
    "state": "queued",
    "attempt_count": 0,
    "last_attempt_id": null,
    "next_retry_at": null,
    "lease_id": null,
    "reason": null
  }
}
```

Pipeline status remains governed by `lifecycle.py`. Executor state answers a
different question: whether the scheduler may dispatch the task.

### Batch lease

`executor-lease.json` is a local ownership guard, not a second event source:

```yaml
schema_version: 1
batch_id: demo-batch-001
execution_id: exec-20260715-001
lease_id: lease-20260715-a1b2c3d4
owner_id: host-pid-4812
acquired_at: "2026-07-15T21:00:00Z"
heartbeat_at: "2026-07-15T21:00:20Z"
expires_at: "2026-07-15T21:01:20Z"
```

The executor acquires this file atomically before mutating events or
projections. A live, unexpired lease produces a conflict rather than a second
writer. Reclaiming an expired lease requires explicit operator action and
emits `lease-reclaimed`.

An expired lease is not proof that external work failed. If a reclaimed lease
finds a task `running` with no terminal receipt, the executor emits
`attempt-reconcile-required` and refuses to dispatch a replacement
automatically. This prevents a process crash from becoming a duplicate
request.

## Execution policy

The planner will snapshot an optional `execution` policy into `summary.yaml`.
Command-line overrides may be used when starting an execution, but the
resolved policy is immutable for that execution ID. A resumed execution uses
the same policy.

```yaml
execution:
  max_concurrency: 1
  max_attempts: 2
  retry_backoff_seconds: [5, 30]
  task_timeout_seconds: 900
  batch_timeout_seconds: 3600
  max_tasks: 100
  max_total_attempts: 100
  failure_policy: continue
```

First-slice bounds:

| Policy | Rule |
| --- | --- |
| `max_concurrency` | Must be `1`; values `2..4` are reserved for a later locking slice and values above `4` are invalid. |
| `max_attempts` | Integer `1..3`, including the initial attempt; default `2`. |
| `retry_backoff_seconds` | Finite non-negative schedule; default `[5, 30]`; never an unbounded sleep. |
| `task_timeout_seconds` | Positive finite duration; default `900`. |
| `batch_timeout_seconds` | Positive finite duration; default `3600`; timeout stops new dispatches. |
| `max_tasks` | Default and hard first-slice upper bound `100`. |
| `max_total_attempts` | Finite count; default is the lower of `100` and `task_count * max_attempts`. |
| `failure_policy` | `continue` by default; `stop` prevents new dispatch after the first exhausted/nonretryable failure. Neither policy rolls back. |

The core does not estimate money, tokens, or provider quotas. It enforces task,
attempt, concurrency, and time budgets. An adapter may report safe usage
metadata outside the required receipt contract.

## Ordering and dispatch eligibility

The task order in `summary.yaml` is the stable default order. The first
executor has no implicit dependency graph or priority queue. It selects the
first task that:

1. is not already `final-done`;
2. is not in a terminal executor state (`succeeded`, `failed`, `needs-review`,
   `cancelled`, or `reconcile-required`);
3. has no future `next_retry_at`;
4. is not blocked by pause, cancel, timeout, or `failure_policy: stop`;
5. has not exhausted the attempt budget; and
6. does not violate packet serialization.

Tasks sharing a `packet_id` form a serialization group. They must not run
concurrently because research writebacks or lineage decisions can touch the
same logical packet. The serial first slice enforces this naturally. A later
concurrency slice must add a packet mutex and still obey ADR-002 parent
matching and conflict preservation.

The executor does not infer dependencies from similar prose or entity names.
Explicit task dependencies require a separate batch contract ticket.

## Task execution state machine

Executor state is separate from the existing pipeline status:

```text
queued
  -> leased -> running
      -> succeeded
      -> retry-wait -> leased
      -> needs-review
      -> failed
      -> cancelled
      -> reconcile-required

queued -> cancelled
retry-wait -> paused
paused -> queued
needs-review -> queued       # explicit operator requeue only
failed -> queued             # explicit operator retry only
```

Rules:

- `leased` reserves a task but does not claim an external attempt started.
- `running` is written before adapter dispatch and names the attempt ID.
- `succeeded` is allowed only after receipt, artifact, QA/diff-QA, and existing
  lifecycle validation. Normal success reaches `final-done`.
- `retry-wait` requires an explicitly retryable receipt and remaining budgets.
- `needs-review` covers incomplete work, QA failure, diff-QA indeterminacy,
  lineage conflict, or another human gate. It is not automatically retried.
- `failed` covers nonretryable or exhausted failures; the reason remains.
- `cancelled` requires acknowledged adapter cancellation or a task that had
  not started. A cancel request is not proof that running work stopped.
- `reconcile-required` is a safety stop for an unknown attempt outcome.
- Ordinary resume only handles queued work and eligible retry waits.

Receipt-to-state mapping:

| Adapter receipt | Executor state | Automatic action |
| --- | --- | --- |
| `succeeded` with valid artifacts and gates | `succeeded` | Promote through the existing lifecycle and select the next task. |
| `incomplete` or `needs_review: true` | `needs-review` | Preserve artifacts, continue independent tasks, await review. |
| `rejected` | `failed` or `needs-review` according to receipt policy | Do not retry automatically. |
| Retryable `failed` with budget | `retry-wait` | Persist `next_retry_at`, then create a new attempt. |
| Nonretryable or exhausted `failed` | `failed` | Continue or stop according to policy; never rollback. |
| `cancelled` | `cancelled` | Stop scheduling this task and preserve its receipt. |
| Missing/invalid receipt | `failed` or `reconcile-required` | Never promote or blindly retry unknown work. |

The core validates receipt identity, attempt path, hashes, task identity, and
stage requirements before trusting any adapter outcome, as required by
ADR-001.

## Batch state machine

The exact state is stored under `summary.executor.state` and projected from
events:

```text
idle -> running
running -> pause-requested -> paused
running -> cancel-requested -> cancelled
running -> completed
running -> completed-with-failures
running -> recovery-required
paused -> running
completed-with-failures -> running       # explicit retry/review command
recovery-required -> running             # explicit reconciliation
```

Terminal batch states are `completed`, `completed-with-failures`, and
`cancelled`. Status and read-only resume commands never reopen a terminal
batch.

- `completed`: every task is `final-done` and no task needs review.
- `completed-with-failures`: no ordinary work remains, but a task failed,
  needs review, or was cancelled.
- `paused`: no new task is active and the pause is durable.
- `cancelled`: no new task is dispatched and active adapters acknowledged
  cancellation or entered explicit reconciliation.
- `recovery-required`: the executor cannot safely continue without review.

## Execution sequence

The first implementation follows this sequence:

1. Load and validate the batch, task contracts, projections, event stream, and
   resolved policy.
2. Acquire `executor-lease.json`; a valid competing lease returns a stable
   conflict without writing task or batch artifacts.
3. Verify/rebuild projections and detect stale or unknown running attempts.
4. Emit `batch-execution-started` or `batch-resumed`.
5. Select the first eligible task, emit `task-leased`, atomically update its
   executor projection, and create a new attempt ID.
6. Dispatch the adapter through the existing one-task request boundary.
7. Validate the receipt and every artifact. Only then promote artifacts or
   advance the task lifecycle.
8. Emit the outcome and update projections. Retryable failures persist
   `next_retry_at`; review and failure outcomes persist their reasons.
9. Continue until the queue drains or pause, cancel, timeout, or stop policy
   prevents new dispatch.
10. Emit the batch outcome, release the lease, and preserve all receipts and
    event history.

An executor crash between dispatch and terminal receipt processing does not
authorize a duplicate retry. The next owner must reconcile the attempt or
explicitly record operator verification before requeueing it.

## Retry and control semantics

Every retry keeps the same logical task and idempotency key but receives a new
attempt ID and directory. Automatic retry is allowed only for a retryable
`rate_limited`, `network`, or `provider` failure with remaining budgets and no
active pause, cancel, timeout, or stop control.

`contract_invalid`, `unsupported`, `auth`, `configuration`,
`artifact_invalid`, `cancelled`, and nonretryable `provider`/`internal`
failures do not receive automatic retries. Review-required and diff-QA
indeterminate outcomes are not transient failures.

The backoff schedule is persisted in the event and task projection. Resuming
after process exit compares UTC time with `next_retry_at`; it does not reset
the budget.

The additive operator surface is:

```text
rdw batch execute <batch-dir> [--resume]
rdw batch pause <batch-dir>
rdw batch cancel <batch-dir>
rdw batch status <batch-dir>
rdw batch resume <batch-dir>       # retain current read-only next-task view
```

`batch pause` stops new leases and new retries. An active attempt finishes its
current adapter boundary, after which the batch becomes `paused`.

`batch execute --resume` uses the same policy, skips final and terminal task
states, and continues queued or eligible retry-wait work. It does not bypass
review or duplicate completed attempts.

`batch cancel` stops new leases and asks an active adapter to cancel when the
adapter declares cooperative cancellation. The executor records `cancelled`
only for an acknowledged cancellation or a task that had not started. An
unacknowledged active runtime leaves the batch in `cancel-requested` or
`recovery-required`; no process kill, artifact deletion, or rollback is
implied. Cancellation is terminal in v1.

## Human review and partial success

Review is task-scoped. The executor treats adapter incompleteness, QA failure,
diff-QA failure or indeterminacy under ADR-003, packet conflicts under ADR-002,
and explicit approval requirements as `needs-review`. It preserves the
artifacts, does not call the humanizer to hide the gate, and continues
independent tasks under `failure_policy: continue`.

The batch projection exposes separate counts for `completed`, `failed`,
`needs_review`, `cancelled`, and `pending`. If tasks A and B complete while C
fails, A and B remain complete. If C later succeeds after explicit repair,
only C receives a new attempt and new lifecycle events.

There is no batch-level transaction or rollback. Provider effects and
filesystem artifacts are not assumed reversible.

## Event vocabulary and idempotency

The implementation uses compact `batch-state` and `task-state` event envelopes
with the following semantic states. Keeping the envelope small preserves the
legacy batch-log fields while making the executor reducer deterministic.

| Event | Meaning |
| --- | --- |
| `batch-state: running` | New execution acquired the lease. |
| `batch-state: paused` | Pause reached a safe boundary. |
| `batch-state: cancel-requested` / `cancelled` | Cancellation intent and safe terminal state. |
| `task-state: leased` / `running` | Task and external attempt ownership. |
| `task-state: succeeded` | Receipt, artifacts, QA gates, and lifecycle passed. |
| `task-state: retry-wait` | Retryable failure received a future retry time. |
| `task-state: needs-review` | Task stopped at an evidence or human gate. |
| `task-state: failed` / `cancelled` | Terminal task outcome. |
| `task-state: reconcile-required` | Unknown attempt outcome blocks automatic retry. |
| `batch-state: completed` / `completed-with-failures` | Queue drained with clean or partial outcome. |
| `batch-state: recovery-required` | Safe execution cannot continue without reconciliation. |

`event_id` is computed from batch ID, execution ID, command ID, task ID,
attempt ID, and event type. A duplicate command or crash retry therefore maps
to the same logical event. The reducer deduplicates by event ID, while the
single writer assigns sequence numbers.

Attempt receipts remain immutable. A retry never overwrites an earlier receipt,
even with the same idempotency key.

## Minimal implementation slice

The next implementation should remain small and fixture-backed:

1. Add typed policy and executor-state definitions with range validation.
2. Add a serial `execute_batch` use case that composes the existing one-task
   executor and a test fixture mapping for task IDs.
3. Add event encode/reduce helpers with deterministic IDs and replay dedupe.
4. Add atomic task/batch executor projections and the batch lease guard.
5. Add batch execute, pause, and cancel commands while preserving the current
   read-only `batch resume` behavior.
6. Map receipt outcomes to retry, review, failure, and cancellation states
   without changing the existing pipeline status vocabulary.

The fixture implementation must not call a model, browse, use a database, or
require credentials. A real provider runtime remains outside this slice.

## Verification contract

The implementation is complete only when tests and CLI smoke cover:

| Scenario | Required proof |
| --- | --- |
| Ordered success | Three tasks run in input order and produce a completed batch. |
| Same-packet serialization | Tasks sharing a packet never overlap. |
| Continue after failure | A failed/review task does not erase or prevent independent later tasks. |
| Stop policy | No new task starts after an exhausted/nonretryable failure under `stop`. |
| Retry | Retryable failure uses the same idempotency key and a new attempt directory. |
| Retry exhaustion | No attempt exceeds `max_attempts`. |
| Review gate | QA failure or diff-QA indeterminacy preserves evidence and stops only that task. |
| Pause/resume | Pause stops new leases; resume skips final tasks and avoids duplicate events. |
| Cancel | Cancellation is honest, cooperative, and never rolls back completed artifacts. |
| Event replay | Duplicate event IDs do not change the rebuilt projection. |
| Lease conflict | A second executor cannot mutate a validly leased batch. |
| Unknown attempt | Lost running work becomes `reconcile-required`, not an automatic duplicate retry. |
| Limits | Task, attempt, timeout, and policy bounds are enforced. |
| Compatibility | Existing batch status/resume, lifecycle, package, and wheel checks stay green. |

Golden event sequences compare stable event types, task IDs, attempt numbers,
reasons, and counts while ignoring timestamps, host PIDs, and random suffixes.

## Alternatives considered

### Default parallel fan-out

Rejected for the first slice. It requires proven task locks, safe event
serialization, adapter cancellation, and same-packet conflict handling. Serial
dispatch gives RDW a useful executor and an unambiguous baseline.

### Adapter-owned scheduling

Rejected. Adapters cannot own canonical lifecycle state, cross-task ordering,
review gates, or batch projections without violating ADR-001.

### All-or-nothing batch transaction

Rejected. Provider effects and filesystem outputs may not be reversible;
partial success is more honest and supports audited repair.

### Automatic retries for every failure

Rejected. Contract, auth, evidence, artifact, and review failures are not
transient and may duplicate unsafe work.

### Hosted queue or database now

Deferred until local event and projection semantics are proven. The filesystem
is sufficient for this bounded first executor.

### Mutating the existing `batch resume` command

Rejected. Consumers use it to list pending tasks. Execution must be additive and
explicit; the compatibility read remains read-only.

## Review evidence

The TMCP architecture review completed as `tmcp-review-plan-3f488911`. All
packet, playbook, rubric, evidence, finding, and remediation validations
passed, and the substance check scored 4/4. The review scored source grounding
3/4, risk priority 1/4, verification readiness 2/4, and scope control 2/4.
Its primary blocker was the risk of unbounded concurrency, retries,
cancellation, or rollback corrupting filesystem projections or duplicating
external work. This ADR addresses that blocker with serial-first dispatch,
one-writer leases, finite retry limits, cooperative controls, explicit
reconciliation, and no rollback.
