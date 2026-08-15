# Deterministic Diff-QA Gate

Compare the current structured artifact with an explicitly approved local
baseline before the humanizer/blader. This is a semantic regression gate, not
a prose-style review and not permission for an external action.

## Inputs

- The task contract's `diff_qa_mode`, `diff_qa_baseline_path`, and `diff_qa_path`
- An approved `diff_baseline` manifest and its unchanged artifact bytes
- The candidate packet, or the draft plus an explicit `draft_claim_ledger`
  sidecar when the contract uses `draft` mode

## Run

```bash
rdw diff-qa <baseline-manifest> <candidate> \
  --root <task-or-repository-root> \
  [--candidate-ledger <ledger>] \
  --output <task-run>/outputs/qa/<output_id>-diff.yaml
```

Packet mode compares stable fact, metric, source, uncertainty, and rule
representations. Draft mode compares the claim ledger only; it never extracts
claims from Markdown. A missing or malformed draft ledger is
`status: indeterminate` with `DQA-009`, requires human review, and cannot pass.

The baseline manifest must be structurally valid, `approved: true`,
`qa_status: pass`, hash-matched, identity-matched, and approved by a human.
Never replace a baseline silently or treat a prior `final-done` status as
baseline approval.

## Outcomes

- `pass`: eligible to advance to `qa-passed`; minor-only findings set
  `needs_human_review: true`.
- `fail`: preserve the candidate and report, mark `qa-failed`, and name the
  `DQA-*` codes in the reason.
- `indeterminate`: preserve the evidence, stop before humanizer, and require a
  human or a corrected structured representation.

The report is deterministic and local. Do not call a provider, network
service, email system, upload surface, or submission flow. A passing report
still ends at mandatory human review; it does not authorize send, submit,
publish, or upload.
