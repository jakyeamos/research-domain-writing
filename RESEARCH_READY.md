# Research Readiness

Research Domain Writing is prepared as a DOI-grade software-methods artifact for
research-grounded writing workflows. The citable release should archive source
code, domain packs, prompt templates, packet validators, curated examples,
limitations docs, and validation commands. It should not archive user-specific
generated writing runs unless they are explicitly intended as examples.

## Artifact Map

| Surface | Purpose |
| --- | --- |
| `src/rdw/` | Installable CLI, validators, planning commands, and asset loading. |
| `domains/` and `config/` | Domain registry, research packet templates, QA checklists, style, and source expectations. |
| `knowledge/` | Reusable research packets for examples and validation. |
| `prompts/` | Stage prompts and orchestrators used to build exact prompt bundles. |
| `examples/` | Curated example artifacts across basketball, music, technical, and batch usage. |
| `docs/LIMITATIONS.md` | Explicit v0.1 boundaries and claim limits. |

## Validation

Non-network release validation:

```bash
uv run rdw doctor
uv run rdw validate-batch examples/batch-tasks.yaml
uv run pytest
uv run ruff check src tests
uv run basedpyright src tests
```

## Data Availability

Generated `.rdw-runs/` outputs are local run artifacts unless deliberately
committed as examples. Research packets should include source notes, confidence,
timestamps, and domain-specific extension data before being cited.

## DOI Gate

Before minting a DOI, replace the placeholder ORCID in `CITATION.cff` and
`.zenodo.json` with the real author ORCID.
