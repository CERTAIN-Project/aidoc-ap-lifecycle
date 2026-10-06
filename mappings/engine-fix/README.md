# Minimal fixes for the engine mapping

Five small fixes for errors in the R2RML mapping of the Semantic MLOps Engine (`ontop/input/`), as a patch series against engine commit b41ea27 (the current `main`). They concern the engine's own mapping to the AIDOC-AP core: no change needs a database migration, and none depends on the Lifecycle Extension. Each patch is one commit and can be taken on its own.

| Patch | Error | Fix |
|---|---|---|
| 0001 | `data_signatures.signature` is a PostgreSQL `json` column, which has no equality operator; queries that need DISTINCT over `aidoc:dataCharacteristic`, and materialisation, fail | cast the column to text |
| 0002 | Ontop loads AIDOC-AP 1.0; the mapping uses `aidoc:VisualDocumentation`, renamed in 1.2 | load core 1.2 (byte-identical to the release, SHA-256 468be0cc…); map the class `aidoc:TechnicalDocumentation` |
| 0003 | `prov:wasUsedBy` does not exist in PROV-O; `aidoc:requiresHardware` is stated from the resource, outside its domain | the run and the deployment `prov:used` their resources; the hardware component `aidoc:providesComputationalResource` the resource |
| 0004 | activities and entities mixed up: a run `prov:generated` a deployment (an activity); prediction examples `prov:wasGeneratedBy` a model (an entity); the change log is typed `prov:Activity`; change records and lifecycle phases carry activity times and associations | drop the deployment link; examples `prov:wasDerivedFrom` the model; change log only `aidoc:ChangeLog`; change records `prov:wasAttributedTo` their author and `aidoc:endDate`; no times on lifecycle phases |
| 0005 | core properties outside their declared domain: `aidoc:version` on activities, `aidoc:dataCollectionMethod` and `aidoc:dataScope` on activities and examples, `aidoc:hasAIActivity` on the AI system, `aidoc:hasLifecycleStage` with the MLflow experiment state | versions on the model and the run's code; collection method on the dataset; split activities with `aidoc:usesTrainingData`, `aidoc:usesValidationData`, `aidoc:usesTestData`; activities held by the lifecycle phase; experiment state stays on the lifecycle phase (`schema:name`) |

## Verification

`scripts/engine_e2e.py --engine-fix <engine checkout> --core-cqs <core competency queries>` loads the same rows (`mappings/r2rml/e2e/pilot_rows.json`) into PostgreSQL 13, materialises the unchanged and the fixed mapping with Ontop 5.5.0, and runs the 50 competency queries of the AIDOC-AP core (`sparql_competency_questions/` of the core repository, v1.2) over both outputs:

| Measure | Engine | With the fixes |
|---|---|---|
| Core competency queries answered | 29 of 50 | 31 of 50 (none lost; CQ11.2 and CQ14.2 added) |
| Resources typed both prov:Activity and prov:Entity | 10 | 2 |
| Triples with predicates no vocabulary declares | 3 | 1 |
| Domain violations of core predicates | 1 | 0 |
| Gap analysis: undeclared terms, domain conflicts | 5, 28 | 3, 11 |

The unchanged mapping cannot be materialised at all because of the json column; the "Engine" column uses it with patch 0001 applied in the test copy only.

## Not fixed here

These need terms or modelling that the core does not have, or changes outside the mapping; the Lifecycle Extension and its adapter and overlay (`mappings/`) address the first group:

- metric rows are typed as metrics but carry the values of measurements (`dqv:computedOn`, `aidoc:dataScope`); the registry stage of a deployment (`current_stage`) is stated as `aidoc:hasLifecycleStage`; technique names of cleaning steps are stated as `aidoc:dataCollectionMethod`; loss function, optimizer and parameter count use `mls:hasObjective`, `mls:hasOptimizer` and `mls:hasModelParameter`, which ML Schema does not define;
- `drift_metrics.value` is an integer column and `model_deployed.model_cateory` is misspelt (schema migrations);
- metrics computed on the test split are stored with the stage "train" (data API).

## Applying the patches

In a checkout of the engine repository:

```bash
git checkout -b fix/aidoc-ap-mapping origin/main
git am /path/to/aidoc-ap-lifecycle/mappings/engine-fix/*.patch
```

The patches are submitted to the engine as pull request [CERTAIN-Project/Semantic_MLOps_engine#2](https://github.com/CERTAIN-Project/Semantic_MLOps_engine/pull/2) (branch `ontop-fix`), under review.

Compatibility with the overlay of `mappings/r2rml/`: the triples maps added by the patches have the same names as the corresponding triples maps of the overlay, which replaces them. Only `RunCodeVersionTriplesMap` has no counterpart; it states the same version as the overlay's `RunSourceCodeTriplesMap`.
