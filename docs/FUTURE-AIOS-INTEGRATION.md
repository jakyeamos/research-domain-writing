# Future AIOS Integration (Not Implemented)

This tool is **standalone** today. When integrating into AIOS or a second-brain layer, consider these mapping points only — do not assume they exist yet.

## Likely integration surfaces

| This tool | AIOS analogue |
|-----------|----------------|
| `knowledge/<domain>/*.yaml` | Context packets / CTS entity stores |
| Concept/jargon banks | `aios/context/domains/` feature packets |
| Research planner | Context compiler task classification |
| QA artifacts | Success criteria evaluator findings |
| `outputs/batch-log.jsonl` | Workflow experiment logs |
| Style profile | Author profile in hooks / PROJECT.md |

## Design constraints to preserve

1. **Separation of knowledge vs style** — do not merge humanizer into research hooks
2. **Packet ids** — stable slugs for reuse across sessions
3. **Confidence + needs_review** — must flow to operator UI
4. **No silent promotion** — research writebacks should stay reviewable (AIOS governance)

## Suggested hook points

- **Session start:** suggest existing packets for entity mentioned in task
- **Pre-write:** block humanizer-only path when domain pack detected
- **Session stop:** propose concept-bank writebacks from new research

## Out of scope for v1

- Built-in fetch/crawl layer inside this package (research stays agent-driven per skill prompts)
- SQLite storage (files are sufficient until scale demands)
- AIOS registry / managed runtime coupling

Optional later: thin source adapters invoked by a batch CLI or AIOS hook — not required for the research model to work.
