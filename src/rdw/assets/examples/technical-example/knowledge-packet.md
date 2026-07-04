# Knowledge Packet - technical-example-idempotency-explainer

## Task
- output_type: feature_explainer
- audience: backend engineers
- domain: technical

## Non-negotiables
- Claims allowed: retry safety, duplicate side-effect prevention, first-result reuse, scope/retention/conflict caveats
- Claims forbidden: exact retention windows, vendor-specific response codes, universal guarantees
- Uncertainty: implementation details vary

## Facts
- Idempotency keys make retries safe for side-effecting requests.
- The server associates the first result with the key.
- Create, charge, submit, and enqueue flows benefit most.
- Scope, retention, and conflict semantics must be documented.

## Template
1. Define the failure mode.
2. Explain key behavior.
3. Name where it matters.
4. Close with implementation caveats.

## Style
Plain, operational, and precise. Prefer concrete API behavior over analogy.
