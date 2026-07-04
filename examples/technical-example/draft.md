---
output_id: technical-example-feature-explainer
domain: technical
entity_name: Idempotency keys
output_type: feature_explainer
draft_version: 1
research_packet_ids:
  - technical-feature-idempotency-keys-demo
---

# Idempotency keys

Idempotency keys protect clients from duplicate side effects when they retry a request. The client sends a stable key with a create, charge, submit, or enqueue operation. If the first request succeeds but the response is lost, the retry can reuse the same key and receive the stored result instead of running the operation again.

The important product detail is scope. Teams should document how long keys are retained, what fields must match on retry, and whether a mismatched payload returns a conflict or the original response. The pattern makes retries safer, but the exact guarantee belongs to the service implementation.
