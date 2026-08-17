# Lightweight QA

Audit the draft against the lightweight research card before any style pass.
This is a grounding gate, not a fluency review.

## Required checks

- Every factual or recipient-specific claim maps to a `supported_claims` item.
- Every mapped claim has a source and confidence; unknowns are not presented as
  facts.
- No new names, metrics, dates, comparisons, achievements, or recipient facts
  appear in the draft.
- The channel, audience, length, CTA, and artifact-profile requirements hold.
- Generic filler, unsupported enthusiasm, and blocked phrases are absent.
- Private-source content remains redacted and local.
- `human_approval_required` is true; no action is authorized by this check.

## Output

Write a YAML QA artifact with this shape:

```yaml
schema_version: rdw-lightweight-qa/v1
pass: true
needs_full_lane: false
needs_research: false
verified_claim_ids: [claim-1]
issues: []
human_review_required: true
```

Use `pass: false` for any blocker or uncertainty. Set `needs_full_lane: true`
when the task has outgrown the card's research budget. Do not let the
humanizer repair a failed grounding check; return to the card or re-plan at
full depth.
