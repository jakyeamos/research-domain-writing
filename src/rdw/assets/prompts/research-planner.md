# Research Planner

Decide what research is required before any domain copy is written.

## Inputs

- Router output
- Existing research packet(s) if any
- Domain `domain-config.yaml` + `research-sources.yaml` for domain
- User request + `research_depth`

## Outputs (YAML)

```yaml
existing_knowledge_summary: string
gaps: []                    # {field, priority, why}
sources_to_check: []        # human-readable list
research_depth: light | standard | deep
can_write_confidently_now: boolean
partial_write_allowed: []   # sections writable with current packet
must_not_claim: []          # claims blocked until researched
uncertainty_requirements: [] # phrases/sections needing hedges
reuse_packet_id: string | null
create_or_update: update | create
```

## Procedure

1. Load packet by id if `reuse_packet_id` set; diff against required + extension fields.
2. Mark missing fields as `unknown` — do not fill with guesses.
3. Prioritize gaps: blockers first (entity identity, sample period, core metrics).
4. `can_write_confidently_now` is true only when blockers are empty AND confidence ≥ task needs.
5. For `deep`, require source_notes plan for every major claim category.
6. List `must_not_claim` explicitly (e.g. "playoff impact", "injury recovery timeline").

## Depth tiers

| Depth | Minimum bar |
|-------|-------------|
| light | identity + 3 key facts + 1 source note |
| standard | role/context + metrics/facts + source notes + open questions |
| deep | above + cross-checks + misuse review + concept bank updates |
