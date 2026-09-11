# DOI Readiness

The repository carries citation and Zenodo metadata for a future archived
software release. The metadata describes the current `0.3.0` release target;
it does not claim that the package has been published or that a DOI has been
minted.

## Archive boundary

Include the installable source, domain and prompt assets, curated examples,
validation tests, limitations, and release metadata. Exclude generated
`.rdw-runs/` output, private source packets, and host-specific installed skill
copies unless they are deliberately selected as public examples.

## Gate before minting

Run the release checks in `RELEASE.md`, confirm the matching tag and CI result,
then review the final archive contents. The metadata alone does not authorize
publication or DOI minting.
