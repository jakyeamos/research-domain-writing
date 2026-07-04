# Domain Router

Infer the full task contract from natural language. **The user does not need to pass `domain=`, `entity=`, etc.** — only when they want to override.

## Inputs

- User writing request (raw) — may be a single sentence
- Optional explicit overrides (`domain=`, `entity=`, `output-type=`, `audience=`, `depth=`, `packet-id=`)
- `config/domains.yaml`
- `config/router-inference.yaml`
- List of available packs under `domains/`
- Optional: project paths, files, or URLs the user mentions (load for entity context)

## Outputs (YAML)

```yaml
# Original user text (always)
task: string

# Inferred or overridden — report all of these to the user before pipeline continues
domain: string
pack_exists: boolean
entity_type: string
entity_name: string
topic: string
output_type: string
audience: string
research_needed: boolean
research_depth: light | standard | deep

# Transparency
inference:
  mode: inferred | explicit | mixed
  confidence: high | medium | low
  fields_inferred: []
  fields_explicit: []
  rationale: string   # one short paragraph

local_knowledge_paths: []
qa_checklist_path: string
writing_template: string
style_profile_path: config/style-profile.yaml
warnings: []
```

## Inference procedure (required)

1. **Start from** `config/router-inference.yaml` defaults.
2. **Parse user text** for domain signals (jargon, surface names like "LIS leaderboard", product names).
3. **Apply** `domain_inference` keyword lists → pick domain with most signals; if tie, prefer basketball only when sports/stat cues present.
4. **Apply** `output_type_inference` and `entity_inference` patterns (e.g. "leaderboard" → `ranking_explanation`, entity `LIS leaderboard` if named).
5. **Apply** `audience_inference` match lists.
6. **Apply** `depth_inference`: deep triggers win; light triggers win; else `standard`.
7. **Explicit overrides** from `key=value` or user saying "domain is X" → replace inferred field; set `mode: mixed`.
8. **Entity naming**: preserve user’s proper nouns (LIS, product names) verbatim in `entity_name`.
9. **Topic**: short phrase for what the writing must accomplish (e.g. "improve leaderboard UI copy").
10. **Do not invent domain facts** — only route metadata. Unknown domain → `general` + warning.

## Worked example

**User:** "I want you to improve the copy on my LIS leaderboard."

```yaml
task: Improve copy on the LIS leaderboard (headers, row blurbs, methodology as needed).
domain: basketball
entity_type: ranking
entity_name: LIS leaderboard
topic: Leaderboard UI and ranking copy grounded in what LIS measures
output_type: ranking_explanation
audience: fantasy and analytics users who know basic stats
research_depth: standard
research_needed: true
inference:
  mode: inferred
  confidence: medium-high
  fields_inferred: [domain, entity_type, entity_name, output_type, audience, research_depth]
  rationale: LIS + leaderboard implies basketball analytics ranking surface; not a single-player task unless user narrows.
```

## After routing

- **Show the inferred contract** to the user in a compact table; proceed unless they object.
- Continue pipeline without requiring them to re-type parameters.

## Rules

- Prefer reusing `knowledge/<domain>/*.yaml` when packet id matches entity (e.g. `basketball-lis-leaderboard` if exists).
- Flag `warnings` when `inference.confidence` is low.
- Never block the run solely because parameters were omitted.
