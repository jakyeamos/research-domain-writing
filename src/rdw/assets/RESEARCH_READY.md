# Research Readiness

Research Domain Writing has citation and archive metadata for a future
software-methods release. The citable artifact should archive source code,
domain packs, prompt templates, packet validators, curated examples,
limitations docs, and the release metadata. It should not archive
user-specific generated writing runs or private source packets unless they are
deliberately attached to the release.

## Validation

Use the commands in `RELEASE.md`, including the locked dependency, quality,
package-parity, test, build, and wheel-smoke checks. These are local and
non-network validation steps.

## DOI Gate

Author ORCID is recorded in `CITATION.cff` and `.zenodo.json`. Before minting a
DOI, confirm the version-matched release tag, CI result, and archived artifact
boundary match the release notes.
