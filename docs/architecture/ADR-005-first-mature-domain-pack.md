# ADR-005: First mature domain pack — basketball analytics

**Status:** Accepted as the target contract; implementation remains gated by the acceptance rubric  
**Date:** 2026-07-15  
**Decision:** Make basketball analytics the first production-grade RDW domain pack, scoped initially to evidence-grounded ranking, player, and team-context writing.

## Context

RDW currently has three enabled starter packs: basketball, music, and
technical writing. They demonstrate the same provider-neutral pipeline, but
they do not have equal evidence, QA, or repeatability. The first mature pack
should be the domain where RDW can prove its grounding boundary with the least
ambiguity and the strongest existing product signal.

This decision is based on repository evidence, not a claim about external
market size. The product-fit signal is the repeated LIS leaderboard workflow in
the router, golden contract, README, and modernization history. The current
basketball packet and fixtures are explicitly synthetic and cannot be treated
as production evidence.

## Decision

Basketball analytics becomes the first mature domain pack. The initial pack is
narrower than the word “basketball” suggests:

- leaderboard and ranking explanations;
- player stat interpretation and summaries;
- evidence-backed comparisons;
- role, usage, and team-fit context;
- cautious future projections when the packet contains explicit drivers and
  uncertainty.

The pack explains and writes from supplied evidence. It does not calculate a
ranking, fetch provider data, or silently fill a missing packet. The existing
`example_only: true` marker remains in place until the graduation gates in
this document pass.

## Candidate evaluation

Scores are 1–5, where 5 is strongest. “Product fit” is a repository signal,
not validated market research.

| Criterion | Basketball analytics | Technical/product | Music criticism |
|---|---:|---:|---:|
| Product-fit signal | 5 | 4 | 3 |
| Structured evidence path | 4 | 5 | 2 |
| Domain-specific QA leverage | 5 | 4 | 3 |
| Repeatable task coverage | 5 | 4 | 3 |
| Overclaiming controls | 4 | 4 | 3 |
| End-to-end proof already present | 5 | 3 | 3 |
| **Total** | **28** | **24** | **17** |

Evidence for the basketball score includes:

- `tests/golden/lis-leaderboard/` proves the intended natural-language entry
  point and resolved task contract;
- `domains/basketball/` already contains metric misuse rules, concepts,
  terminology, templates, and a domain checklist;
- `knowledge/basketball/` and `examples/basketball-example/` exercise the
  packet-to-QA path;
- `examples/fixtures/` covers success, review-required, and rejected outcomes;
- `config/router-inference.yaml` treats leaderboard and LIS work as a first-
  class routing case.

Technical writing has the strongest source reproducibility, but its current
pack is a generic feature-explainer demonstration rather than a product
surface with a distinct domain corpus. Music has useful anti-hallucination
rules, but listening evidence, credits, and reception context are harder to
reproduce consistently and the current example is intentionally thin.

## Pack contract

### Required packet invariants

Every production basketball packet must satisfy the generic packet contract in
`domains/_template/research-packet-template.yaml` and additionally provide:

- stable `id`, `entity_type`, `entity_name`, `time_period`, and `last_updated`;
- atomic `key_facts` with a non-empty source mapping;
- `source_notes` with source, access date, notes, and `fact_ids` for every
  externally verifiable fact;
- `confidence_level`, `open_questions`, and `uncertainties`;
- `domain_terms` and `concepts_that_apply` whenever terminology affects the
  copy;
- role, team, usage context, and sample scope before an impact claim.

Metric records must include:

- metric name and value or an explicit `unknown`;
- unit and denominator when applicable;
- season or time period;
- sample scope, such as games, minutes, possessions, or on/off sample;
- what the metric captures and what it does not capture;
- source or `fact_ids` that support the value and definition.

### Ranking extension

Ranking and leaderboard packets must add an `extensions.ranking` object with:

- `ranking_name`;
- `metric_definition`;
- `population` and inclusion/exclusion filters;
- season or update window;
- rank value and tie/missing-value behavior;
- methodology notes and known limitations;
- update timestamp and freshness expectation;
- a list of ranked entities or a source reference to the supplied ranking
  artifact.

The pack may not describe a leaderboard as “better” without naming the
dimension being ranked. It may describe the supplied ordering, but it must not
imply that the ordering is a complete player-value judgment.

### Confidence rules

- **High:** at least two relevant seasons or a clearly documented ranking
  window, stable role/context, and metric definitions cross-checked against
  authoritative sources.
- **Medium:** one complete season or a stable current ranking with documented
  methodology and limitations.
- **Low:** preseason, fewer than 15 games, injury-shortened sample, unclear
  role, unverified tracking data, or unresolved source disagreement.

Low-confidence packets may produce bounded descriptive copy, but projections,
comparisons, and strong ranking claims require human review or must be marked
not writable by the planner.

## Source and research policy

Preferred evidence order:

1. official league or team records and box scores;
2. official or licensed tracking/stat documentation with definitions;
3. reputable analytics sources that publish methodology;
4. secondary commentary only for clearly labeled interpretation or reception.

Research must record access date and sample scope. Volatile facts such as
current ranks, roster status, or injury context need a freshness expectation
and must not be reused indefinitely as if they were durable facts. A source
does not support a claim merely because it appears in the same packet; the
claim must map to a fact, metric, or interpretation note.

## Writing surface

The first mature release supports these output types already represented or
anticipated by `domains/basketball/writing-templates.md`:

- `ranking_explanation`;
- `player_summary`;
- `stat_interpretation`;
- `why_stat_likes_player`;
- `why_stat_skeptical`;
- `role_context`;
- `comparison_blurb`;
- `team_fit_notes`.

The copywriter must preserve the template order: define the metric or ranking,
establish role and sample, state the evidence-backed read, then name the
limitation or uncertainty. The humanizer may improve rhythm and clarity only;
it may not add a stat, comparison, causal explanation, injury claim, or
projection driver.

## Acceptance rubric

The pack is ready to leave `example_only` status only when every gate below is
met.

| Gate | Pass rule | Required evidence |
|---|---|---|
| Identity and provenance | Every packet has stable identity, period, freshness, confidence, and source notes. | Validated production packets and source map |
| Metric semantics | Every metric has definition, value/unit, sample, capture/miss limits, and source mapping. | Packet fixtures and validator output |
| Role/context | Impact claims name role, team/lineup context, and relevant sample before interpretation. | Positive and misuse fixtures |
| Claim traceability | 100% of factual and numeric claims in accepted drafts map to packet facts, metrics, or labeled interpretation notes. | QA claim ledger or equivalent report |
| Ranking honesty | Every ranking explanation names the dimension, population, period, and known limitations; no total-value implication without evidence. | LIS/ranking positive fixture |
| Uncertainty | Projections, small samples, injuries, and unresolved source conflicts are labeled or blocked. | Negative fixtures and QA output |
| Terminology | Concept and jargon usage matches the pack; forbidden generic phrases are absent or explicitly justified. | QA checklist and terminology fixtures |
| QA outcome | Zero blocker or major grounding, jargon, hallucination, or overclaim issues. Minor style issues may remain for humanizer. | `outputs/qa/*-qa.yaml` |
| Regression safety | All acceptance fixtures pass through the same deterministic validation and fixture execution path. | Focused tests plus full repository gates |
| Maintainability | Pack docs, prompts, packet templates, and examples agree on names and paths. | Package parity and documentation review |

## Acceptance fixture matrix

The first acceptance set should contain at least these cases. The existing
synthetic Demo Guard fixture remains an integration fixture, not proof of real
domain readiness.

### Positive cases

1. **Leaderboard methodology:** explain what a supplied LIS-style ranking
   measures, its population and period, and how to read the ordering.
2. **Player stat interpretation:** connect usage and efficiency to a stated
   role while naming what the metrics miss.
3. **Comparison:** compare two players on named dimensions with matched sample
   and role context, including an explicit non-claim.
4. **Team fit:** describe scheme or lineup fit only from supplied role,
   spacing, matchup, or on/off evidence.
5. **Bounded projection:** state ceiling/floor drivers and uncertainty from a
   packet with an explicit confidence level; do not present the projection as
   a fact.

### Negative cases

1. A ranking explanation with no metric definition or population must fail.
2. A single-number player ranking with no role or sample must fail.
3. An invented tracking value or exact assist rate must fail as a hallucination.
4. A playoff leap based on fewer than 10 games must require a caveat or fail.
5. An injury or availability projection without packet evidence must fail.
6. “High basketball IQ,” “generational,” or equivalent generic praise without
   observable behavior or evidence must fail.
7. A real-player packet containing only synthetic/demo provenance must be
   blocked from production promotion.

## Graduation sequence

1. Extend the basketball packet contract and validator for ranking metadata and
   metric sample/definition requirements.
2. Replace synthetic-only acceptance data with source-grounded packets that
   cover one ranking surface, two player contexts, and one team-fit context.
3. Add the positive and negative fixtures above to the deterministic QA and
   claim-traceability tests.
4. Run the full RDW pipeline for each positive case: research packet,
   knowledge packet, draft, QA, and humanizer handoff.
5. Update the domain pack docs, prompt mirrors, package assets, and examples;
   then run package parity, wheel, and full test gates.
6. Change `example_only` to `false` only after all gates pass and a human
   reviews the source freshness and overclaim boundaries.

## Non-goals

- live provider SDKs, browsing, or autonomous research in the deterministic
  core;
- calculating LIS or any other ranking inside the writing pack;
- betting, medical, financial, or injury advice;
- automatic packet merges or last-write-wins updates;
- a general scouting database or complete basketball knowledge graph;
- declaring market demand from repository examples alone.

## Decision provenance

This decision was grounded in:

- `config/domains.yaml` and `config/router-inference.yaml`;
- `domains/basketball/`, `domains/music/`, and `domains/technical/`;
- `tests/golden/lis-leaderboard/`;
- `examples/*-example/` and `examples/fixtures/`;
- `knowledge/basketball/demo-guard-2026-demo.yaml`;
- `prompts/domain-qa.md`, `prompts/research-planner.md`, and
  `prompts/knowledge-packet-builder.md`.
