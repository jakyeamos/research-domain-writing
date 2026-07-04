# Researcher

Gather and structure knowledge — **not** polished copy.

## Research responsibility (agent)

**You perform research** per planner gaps and `config/research-sources.yaml` — browser, APIs, files, user paste, etc. This skill has no built-in fetch layer; your job is to gather, then structure.

- Record every fact in `source_notes` with what you actually used
- Do not claim sources you did not consult
- Do not write polished copy here — facts and interpretation blocks only

## Inputs

- Research planner output
- Domain research packet template
- `config/research-sources.yaml` for domain
- User-provided materials (stats, links, notes, files)

## Outputs

1. **Updated research packet** (YAML) → `knowledge/<domain>/<id>.yaml`
2. **Missing information log** (YAML) → `outputs/research/<id>-missing.yaml`
3. **Suggested concept/jargon slugs** to load or create

## Rules

- **Facts** go in `key_facts` / `relevant_metrics` with `source_notes` linkage
- **Interpretation** only in `interpretation_notes`
- Use `unknown` for missing extension fields
- Never fabricate statistics, quotes, dates, or chart positions
- Update existing packet by `id` when refreshing; bump `last_updated`
- `confidence_level`: high | medium | low — per domain confidence_rules
- Do not write final prose except short atomic fact strings

## Packet save format

Save as YAML mirroring `domains/_template/research-packet-template.yaml` + domain extensions.

## Source notes item

```yaml
- source: "Official source or user-provided dataset"
  accessed: "2026-06-26"
  note: "TS% 59.2 on 27.8 USG%, 62-game synthetic sample"
  fact_ids: [fact-003, fact-004]
```

## After research

Append packet id to planner's reuse list; suggest concepts to add to bank when a pattern repeats.
