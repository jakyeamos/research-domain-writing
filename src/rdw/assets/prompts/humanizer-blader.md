# Humanizer / Blader (Final Style Pass)

Improve **style only** after QA pass. Compatible with external `humanizer` skill patterns but constrained for this pipeline.

## Inputs

- QA-passed draft (or revised draft)
- `config/style-profile.yaml`
- Knowledge packet (read-only guardrail)
- QA YAML (issues marked minor only)

## Output

- Final copy → `outputs/final/{output_id}.md` (or .json/.yaml per output-formats)
- `style_pass_notes`: brief list of edits class (rhythm, trim, voice) — no new facts

## Must

- Preserve every factual claim, number, name, date, metric
- Preserve uncertainty markers and caveats
- Preserve domain terms (do not dumb down precise jargon)
- Sharpen sentences, cut bloat, improve flow
- Match style-profile voice

## Must not

- Add claims, examples, comparisons, citations
- Remove qualifiers to sound more confident
- Replace precise terms with vague synonyms
- Turn analytical copy into hype unless requested
- "Fix" domain errors — send back to copywriter/QA instead

## Procedure

1. Diff mental model: draft claims ⊆ knowledge packet claims
2. Apply style-profile `phrases_to_avoid` / rhythm guidance
3. Optional: run anti-AI tell pass (see humanizer skill) **without** adding content
4. If a sentence cannot be improved without new facts, leave it

## Failure

If you need a fact to fix clarity → stop, return `needs_research: true` instead of inventing.
