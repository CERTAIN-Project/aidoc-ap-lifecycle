# AIDOC-AP Lifecycle Extension (aidoc-lc)

Extension module of the [AIDOC-AP](https://w3id.org/aidoc-ap) application profile, developed in the CERTAIN project (Horizon Europe, grant agreement 101189650, Task 5.3). The module imports the AIDOC-AP core and adds terms for the stages of the AI system lifecycle that the core, which is restricted to the documentation duties of Annex IV of the EU AI Act, does not describe in detail. It does not change any core definition.

Status: in preparation (version 0.1, not released).

| | |
|---|---|
| Namespace | `https://w3id.org/aidoc-ap/lifecycle#` (prefix `aidoc-lc`) |
| Imports | AIDOC-AP core 1.2 |
| Ontology | [ontology/aidoc-lc.ttl](ontology/aidoc-lc.ttl) |
| Coverage measure | Ontology Coverage Index (CERTAIN KPI 1.1): [docs/02_oci_method.md](docs/02_oci_method.md) |
| Licence | CC BY 4.0 (ontology), Apache-2.0 (code) |

## Quick start

```bash
make setup      # Python venv with rdflib and pytest; fetches the pinned core if vendor/aidoc-ap is missing
make all        # module checks, tooling tests, OCI for core and framework, competency queries
```

`make fetch-core` re-fetches the pinned core release and verifies it against vendor/LOCK.json. `make fetch-engine-excerpt` fetches the parts of the Semantic MLOps Engine repository that the gap analysis (`make gap`) and the examples need; `make fetch-engine` fetches the full repository.

## Layout

| Path | Content |
|---|---|
| ontology/ | the module |
| method/ | reference lifecycle model and the SPARQL criteria of the coverage index |
| scripts/ | coverage index, module checker, competency query runner, engine gap analysis, fetch scripts |
| docs/ | definition of the coverage index (KPI 1.1) and grounding of every module term |
| cq/, examples/ | competency queries and example graphs |
| alignments/, mappings/ | alignment proposals, engine mapping proposal |
| vendor/ | pinned core and engine excerpt (not tracked; checksums in vendor/LOCK.json) |

Maintained by Sebastian Neumaier, University of Applied Sciences St. Pölten.
