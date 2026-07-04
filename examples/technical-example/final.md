---
output_id: technical-example-feature-explainer
domain: technical
entity_name: Idempotency keys
output_type: feature_explainer
confidence_level: medium
needs_review: false
research_packet_ids_used:
  - technical-feature-idempotency-keys-demo
---

# Idempotency keys

**Problem:** Clients retry on timeouts; without idempotency, retries can double-charge or duplicate side effects.

**Behavior:** Clients send an idempotency key on mutating requests. The server stores the first result associated with that key and can return a consistent response on repeats instead of running the operation again.

**Failure modes:** The exact retention window, scope, and mismatched-payload behavior depend on the implementation. A retry outside the documented guarantee may still execute again.

**Constraint:** Document which endpoints honor keys, how long keys are retained, and whether conflicts return the original response or an error.
