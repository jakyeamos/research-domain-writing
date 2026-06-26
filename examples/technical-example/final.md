---
output_id: technical-example-feature-explainer
domain: technical
confidence_level: medium
needs_review: false
---

# Idempotency keys

**Problem:** Clients retry on timeouts; without idempotency, retries can double-charge or duplicate side effects.

**Behavior:** Clients send `Idempotency-Key` on mutating requests. The server stores the first result keyed by (account, key) for 24 hours and returns the same response on repeats.

**Failure modes:** Keys expire after 24h — a retry after expiry may execute twice. Keys are not a distributed lock across different endpoints.

**Constraint:** Safe only when the operation is actually idempotent at the business layer; document which endpoints honor keys.
