# Release procedure

The repository prepares releases; publishing is done by the maintainer. The module stays at 0.x until the release at M24 (December 2026), which is version 1.0.

## Before the release

1. `make release-check` passes: module rules with warnings as errors, tooling tests, coverage index of at least 0.90 with no stage at zero, every competency query returns rows over `examples/`.
2. The CI workflow `Module checks` passes on the default branch, including the HermiT consistency check and the engine job (adapter and R2RML overlay).
3. `make docs-pages` builds the worked examples and coverage pages without errors; review them in `reports/site-extra/`.

## Release

1. `make release VERSION=1.0` runs the release checks, then sets the version and release date in `ontology/aidoc-lc.ttl`, `documentation/config.properties`, `CITATION.cff` and `.zenodo.json`, removes the draft note from the ontology header and writes the snapshot `versions/1.0/aidoc-lc.ttl`.
2. Review the diff, commit, tag `v1.0`.
3. Push the commit and the tag.

## Publishing (maintainer)

1. Repository: make `CERTAIN-Project/aidoc-ap-lifecycle` public. GitHub Pages for private repositories depends on the organisation's plan, so the documentation goes online with the public repository.
2. GitHub Pages: Settings, Pages, source "GitHub Actions". The workflow `Build & deploy documentation (Widoco)` then publishes the term reference, the worked examples, the coverage page and the version snapshots.
3. OOPS!: run the workflow `OOPS! pitfall scan` once by hand; it sends the ontology to EasyRDF and OOPS!.
4. Zenodo: enable the GitHub integration for the repository and create the GitHub release `v1.0`; Zenodo archives it with the metadata of `.zenodo.json` and assigns a DOI. Add the DOI to `CITATION.cff` and `README.md` in the next commit.
5. w3id: open a pull request in `perma-id/w3id.org` with the rules in `release/w3id/` and check the redirects listed there after the merge.
