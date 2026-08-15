# Lightweight Research Card

Use this prompt only when the task contract has `execution_lane: lightweight`.
It is a bounded evidence pass for short, low-stakes writing. It is not a
shortcut for legal, medical, financial, disputed, high-consequence, or deeply
comparative work.

## Inputs

- The resolved task contract
- User-provided material and local files that are in scope
- A matching reusable packet, if one exists
- A small number of authoritative public sources when the contract's
  `research_depth` is `light`

## Output

Write only the run-local card at the contract's `research_card_path`:

```yaml
schema_version: rdw-research-card/v1
task_id: string
domain: string
topic: string
audience: string
recipient_context: string
supported_claims:
  - id: claim-1
    text: string
    source: string
    source_type: user_material | url | packet | other
    confidence: high | medium | low
    evidence_kind: optional string
unknowns: []
must_not_claim: []
candidate_evidence: []
sources:
  - id: source-1
    source: string
    source_type: user_material | url | packet | other
    accessed: optional ISO date
    supports: [claim-1]
```

The card is an evidence boundary, not polished copy. Every supported claim
must point to a source label, and every source must identify the claims it
supports. Use `unknowns` and `must_not_claim` instead of filling gaps.

## Research budget

1. Resolve the entity, recipient context, and task scope.
2. Gather only the facts needed for the requested short artifact.
3. Prefer a matching packet or user-provided evidence; otherwise use the
   smallest useful set of authoritative sources.
4. Keep the card to the few claims the draft can actually use. Do not create a
   concept bank, broad background section, or durable domain packet.

For `research_depth: minimal`, use an existing packet or explicitly supplied
evidence only. Do not perform new research. If the evidence is insufficient,
stop and escalate to the full lane.

## Privacy and source boundaries

- Keep the card inside the run directory; never write it to
  `knowledge/<domain>/`.
- If a private source is in scope, extract only the minimum evidence needed and
  replace names, addresses, thread IDs, employers, exact subjects, and unique
  phrases with neutral placeholders.
- Never copy a private email body, headers, contact details, or identifying
  language into a fixture, prompt bundle, artifact request, receipt, log, or
  external service.
- A source label such as `private-user-material` is sufficient; the source body
  is not evidence that belongs in the card.

## Escalate instead of compressing

Stop and request the full lane when the task is high-stakes, the identity is
ambiguous, the evidence conflicts, more than three material claim categories
are needed, the user asks for a comparison or recommendation, or any claim
would require inference beyond the source. A thin card with a warning is safer
than a confident-looking draft.

Do not write polished copy in this stage.
