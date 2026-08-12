# Domain QA

Audit draft **before** humanizer/blader. Knowledge gate, not style gate.

## Inputs

- Draft Markdown
- Knowledge packet
- Research packet YAML
- Domain `qa-checklist.md`

## Output (YAML + optional revised draft)

Save to `outputs/qa/{output_id}-qa.yaml`

```yaml
pass: boolean
confidence_score: 0.0-1.0
needs_human_review: boolean
issues:
  - id: string
    severity: blocker | major | minor
    category: grounding | jargon | overclaim | missing_caveat | audience | hallucination
    description: string
    suggested_fix: string
revised_draft_path: string | null  # if QA rewrote to fix blockers
blocking_issue_count: number
draft: string # optional for deterministic mature-pack phrase and injury gates
claim_ledger:
  - claim_id: string
    text: string
    fact_ids: [fact-id]
```

When the resolved contract uses draft-mode deterministic diff-QA, also write
the separate contracted sidecar `draft_claim_ledger` with stable `claim_id`,
`text`, `fact_ids`, and `source_ids` for every factual or recipient-specific
claim. Packet-mode full-lane diff-QA compares the candidate to the approved
packet and does not require this sidecar. The ordinary `claim_ledger` above
remains the domain-QA artifact; the draft sidecar is the machine-comparable
representation and must not be replaced by Markdown extraction.

## Checks

1. Extract factual claims from draft → verify each in knowledge/research packet
2. Flag new claims introduced in draft (hallucination) — blocker
3. Jargon vs concept bank definitions
4. Overclaiming vs confidence_level
5. Missing caveats from open_questions / uncertainties
6. Unsupported comparisons
7. Forbidden phrases
8. For mature basketball packets, emit one claim-ledger row for every factual
   or numeric claim and map it to packet `key_facts[].id` values
9. When the draft is supplied to the deterministic gate, reject forbidden
   generic praise and injury/availability claims without packet evidence

## Pass criteria

- `pass: true` only if zero blockers and zero major grounding/jargon issues
- `blocking_issue_count` must equal blocker + major issue count
- A mature basketball claim ledger must contain no unknown or source-unmapped fact IDs
- Style issues alone are minor — defer to humanizer
- Diff-QA is a separate gate after this artifact: run `prompts/diff-qa.md` and
  stop on `fail` or `indeterminate` before humanizer

## Revised draft

If fixing blockers without new facts, save `outputs/drafts/{output_id}-rev1.md` and reference in QA file.
