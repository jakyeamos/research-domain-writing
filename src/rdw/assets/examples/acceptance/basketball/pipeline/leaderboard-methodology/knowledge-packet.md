# Knowledge Packet — basketball-acceptance-ranking-methodology

## Task
- output_type: ranking_explanation
- audience: analytics-literate basketball readers
- domain: basketball

## Non-negotiables
- Claims allowed: the supplied NBA.com comparison definition, named player rows, paired usage-rate and true-shooting changes, and the documented comparison boundary.
- Claims forbidden: total player value, defensive impact, role-adjusted impact, playoff impact, or rows not present in the research packet.
- Uncertainty phrases required: descriptive surface, does not establish, requires role and lineup context.

## Facts (from research)
- NBA.com defines the surface around changes in usage rate and true-shooting percentage between seasons.
- Dillon Brooks is listed with a 9.6 percentage-point usage-rate increase and a 2.7 percentage-point true-shooting increase.
- Jaylen Brown is listed with a 6.4 percentage-point usage-rate increase and a 3.4 percentage-point true-shooting increase.
- Shaedon Sharpe is listed with a 6.6 percentage-point usage-rate increase and a 1.6 percentage-point true-shooting decrease.

## Metrics
- Usage-rate change describes the change in the share of team possessions a player ends while on court; it misses defensive value, role difficulty, lineup context, and whether the extra possessions were efficient.
- True-shooting percentage change includes two-point, three-point, and free-throw scoring; it misses shot difficulty, defensive assignment, playmaking value, and lineup effects.
- The source comparison uses its documented season window and minutes filter; preserve that boundary rather than treating the rows as universal rankings.

## Concepts (compressed)
- **usage-illusion:** a larger possession share needs an efficiency read before it can support a stronger offensive conclusion; link `usage-illusion`.
- **sample-size:** the source filter defines who enters the comparison, but the surface still does not answer every role or context question; link `sample-size`.

## Jargon guardrails
- Define usage-rate change as a percentage-point change in possessions ended while on court.
- Call TS% change a paired efficiency change, not a complete offensive or player-value score.
- Preserve “percentage points” and the source comparison window.

## Template structure
1. State what the surface measures.
2. Explain how to read the paired changes.
3. Give the named rows as examples.
4. Add sample and role caveats.
5. State the explicit non-claim.

## Style
Direct and analytical. Prefer “the surface shows” to promotional labels. Avoid generic praise and unsupported impact language.

## Open questions
- Does the source comparison control for team, lineup, or opponent context?
- How do these changes translate to defensive and playoff impact?
