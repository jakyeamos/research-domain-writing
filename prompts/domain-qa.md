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
```

## Checks

1. Extract factual claims from draft → verify each in knowledge/research packet
2. Flag new claims introduced in draft (hallucination) — blocker
3. Jargon vs concept bank definitions
4. Overclaiming vs confidence_level
5. Missing caveats from open_questions / uncertainties
6. Unsupported comparisons
7. Forbidden phrases

## Pass criteria

- `pass: true` only if zero blockers and zero major grounding/jargon issues
- Style issues alone are minor — defer to humanizer

## Revised draft

If fixing blockers without new facts, save `outputs/drafts/{output_id}-rev1.md` and reference in QA file.
