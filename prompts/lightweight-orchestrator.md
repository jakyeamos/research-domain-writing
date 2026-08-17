# Lightweight Research-Card Orchestrator

Run this lane only when the task contract says
`execution_lane: lightweight`. It is a compact route for short, lower-stakes
writing where a full reusable knowledge packet would be disproportionate.
The human-review boundary is shared with the full lane and remains mandatory.

## Load order

1. `config/domains.yaml`, `config/router-inference.yaml`,
   `config/style-profile.yaml`, `config/output-formats.yaml`, and
   `config/artifacts.yaml`
2. `prompts/domain-router.md` to confirm the contract
3. `prompts/lightweight-research-card.md`
4. `prompts/lightweight-copywriter.md`
5. `prompts/lightweight-qa.md`
6. `prompts/diff-qa.md`
7. `prompts/humanizer-blader.md`

If the contract is missing `execution_lane`, has `human_approval_required:
false`, or the task is material/high-stakes, stop and re-plan through the full
lane. Do not silently downgrade the work.

## Ordered stages

1. **Confirm scope and privacy boundary.** Show the resolved contract. Keep
   private source content local and redacted; never place email body, headers,
   contact details, or unique phrases in fixtures, logs, prompts, receipts, or
   external services.
2. **Research card.** Follow `lightweight-research-card.md`. Save the
   run-local card at `research_card_path`; do not write a reusable packet under
   `knowledge/`.
3. **Grounded draft.** Follow `lightweight-copywriter.md`. Use only the card's
   supported claims.
4. **Compact QA.** Follow `lightweight-qa.md`. If QA fails, needs research, or
   says `needs_full_lane`, stop before humanizer and re-plan at full depth.
5. **Deterministic diff-QA.** Run `diff-qa.md` in the contract's explicit draft
   mode against the approved baseline.
   If the compact lane cannot provide the structured packet or an explicit
   draft claim ledger, stop with `indeterminate`; do not infer claims from the
   card or Markdown.
6. **Humanizer/blader.** Run `humanizer-blader.md` only after QA and diff-QA
   pass. Treat
   the research card as the read-only evidence guardrail. Style may change;
   claims, names, numbers, caveats, and source meaning may not.
7. **Artifact request and receipt.** For externally consumed writing, create
   the normal `rdw-artifact-request/v1` with evidence and claim bindings and
   run `rdw validate-artifact`. Include
   `constraints.human_approval_required: true` and, where the artifact schema
   permits it, `external_actions: []`. A passing receipt is only
   `approved_for_human_review`.
8. **Stop at review.** Do not send, submit, publish, upload, or invoke an
   external communication service. Report the local artifact paths and the
   receipt status for a human to review.

## Outputs

```text
Run-local research card  -> contract.research_card_path
Draft                    -> outputs/drafts/<output_id>.*
Lightweight QA           -> outputs/qa/<output_id>-lightweight-qa.yaml
Diff-QA                  -> outputs/qa/<output_id>-diff.yaml
Final style pass         -> outputs/final/<output_id>.*
Artifact receipt         -> governed run directory or next to request
```

This lane is intentionally not a claim extractor. If the source boundary or
claim mapping cannot be represented explicitly, use the full lane and retain
the uncertainty for human review.
