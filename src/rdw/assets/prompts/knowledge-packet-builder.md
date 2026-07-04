# Knowledge Packet Builder

Assemble **task-specific** context for one writing job — not the whole domain bank.

## Inputs

- User writing request
- Router output
- Research packet YAML
- Selected concept files (slugs from `concepts_that_apply` + planner)
- Selected jargon files
- `config/style-profile.yaml` (voice constraints only)
- Domain `writing-templates.md` section for `output_type`
- Target audience

## Output (Markdown)

```markdown
# Knowledge Packet — {task_id}

## Task
- output_type:
- audience:
- domain:

## Non-negotiables
- Claims allowed:
- Claims forbidden (must_not_claim):
- Uncertainty phrases required:

## Facts (from research)
...

## Metrics
...

## Concepts (compressed)
...

## Jargon guardrails
...

## Template structure
(outline from writing-templates)

## Style (voice only)
(from style-profile — tone, avoid phrases)

## Open questions
(do not answer in copy — surface as caveats)
```

## Rules

- Compress concepts to 2–4 lines each — link slug for full file
- Exclude facts not in research packet
- Cap total length: aim ≤ 1200 words unless deep tier
- If packet confidence is low, prepend **Thin evidence warning**
