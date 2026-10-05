# Engine mapping proposal

Proposed changes to the R2RML mapping of the Semantic MLOps Engine, so that the metadata the engine captures reaches the terms of the Lifecycle Extension and the core v1.2. Base: `ontop/input/aidoc-ap_r2rml.ttl` of the engine at commit b41ea27 (69 triples maps).

Status: proposal, to be agreed with the T5.4 partners according to their roles. Nothing in the engine repository is changed from here.

## Files

| File | Content |
|---|---|
| `aidoc-lc_r2rml_proposal.ttl` | 36 triples maps that replace engine triples maps of the same name, and 37 new triples maps; each with a comment on what changes and why |
| `removed_triples_maps.txt` | 2 engine triples maps to remove |

## Applying the proposal

1. In `ontop/input/aidoc-ap_r2rml.ttl`, replace each triples map that has the same name as one in the proposal, add the new ones and delete the two removed ones. `make mapping-check` does this and writes the result to `reports/aidoc-ap_r2rml_merged.ttl`.
2. Give Ontop the framework instead of core v1.0: `make merged` writes core v1.2 plus the module, without imports, to `reports/framework_merged.ttl`; it replaces `ontop/input/aidoc-ap.ttl`. Ontop uses the OWL 2 QL part of the ontology; the union domains of the module lie outside that profile and are expected to be ignored by Ontop, which does not affect the mapped triples.

## Changes by stage

| Stage | Engine tables | Module and core terms now used |
|---|---|---|
| D1 | data | aidoc:producesDataset, aidoc:hasSourceDataset (web sources), aidoc:dataCollectionMethod on the dataset |
| D2 | data_metrics | new profiling activity per dataset and stage; measurements with producesMeasurement, dqv:isMeasurementOf, dqv:value |
| D3, D5 | data_techniques, data_hyperparameters | processingTechnique (technique names are arrays: unnest); DataProcessing and DataAugmentation activities; hasHyperParameterSetting |
| D5 | tokenizer_config, tokenization_stats | Tokenization; tokenizer settings as hyperparameter settings; statistics as measurements |
| D6 | data | aidoc:usesTrainingData, aidoc:usesValidationData, aidoc:usesTestData |
| M1 | experiments, model_architecture, model_hyperparameters, checkpoints | producesModel; hasHyperParameterSetting, with loss function and optimizer as settings |
| M2 | model_metrics, last_model_metrics, weight_distribution | evaluates; producesMeasurement; metric rows as measurements; weight mean and std mapped |
| M3 | model_packaging | packagesModel; packagingFormat; dependencies with aidoc:dependsOn |
| M4 | model_deployed | versionsModel; assignsRegistryStage; aidoc:version on the model |
| S1, S4 | runs_code, runs, change_logs | producesSoftware, versionsSoftware, producesChangeRecord; aidoc:hasChangeLog, aidoc:endDate |
| S2 | build_and_integration_testing | testsArtifact, buildStatus, testLevel, producesTestReport |
| S3 | model_deployed, runtime_environment | deploys, servingEndpoint, usesComputationalResource |
| O2 | drift_metrics | monitors; drift values as measurements of the deployed model |
| O4 | decomissioning | decommissions, decommissioningReason, decommissioningAction |
| cross-cutting | resources, data_resources | usesComputationalResource; aidoc:providesComputationalResource in its declared direction |
| other | labeling_procedures, experiments, visual_documentation, id_mapping | aidoc:annotatorType, aidoc:annotationTool; aidoc:TechnicalDocumentation (v1.2 name); removal of activity-as-entity statements |

Removed: `PostMarketPerformanceEvaluationActivityTriplesMap`, which typed runtime environment rows as re-evaluation activities, and `DataTechniquesTriplesMap`, which put technique names on the dataset.

## Checks

`make mapping-check` runs two scripts:

- `scripts/mapping_proposal.py` merges the mappings and checks the proposal: tables and qualified columns exist in `data_api/app/models.py`; every column a template, `rr:column` or join uses is produced by the SQL; every class and predicate is declared; every module concept a `CASE` expression can produce exists. On the merged mapping it checks domains and ranges, inferring the classes of link-only triples maps from other triples maps with the same subject template. A deliberately broken proposal fails each of these checks.
- `scripts/r2rml_gap.py --mapping` repeats the gap analysis on the merged mapping and writes `reports/gap_after_proposal.md`.

| | Engine mapping | With proposal |
|---|---|---|
| Terms declared nowhere | 5 | 0 |
| Domain conflicts (gap analysis) | 28 | 0 |
| Domain and range conflicts with template inference | 29 and 2 | 0 and 0 |
| Columns not mapped | 48 | 23 |
| Columns mapped only with generic predicates | 59 | 48 |

The checks are static. The SQL has not yet been run against a PostgreSQL instance of the engine schema, and the merged mapping has not been run in Ontop; doing so is the next verification step.

## IRI changes

Most IRI templates stay as in the engine. These change, because the old IRIs merged distinct records:

| Resource | New template |
|---|---|
| model versioning record | `model-versioning/{run_id}/{model_id}/{deployment_id}` (one per deployment row) |
| data profile measurement | `data/{run_id}/{data_id}/metric/{stage}/{key}` (stage added) |
| weight statistic | `models/{run_id}/{model_id}/weights/{layer_name}/step/{step}/{statistic}` |
| data technique parameter | `data/{run_id}/{data_id}/technique/{technique_name}/parameter/{name}` |

New resources use the templates `hyperparameters/{name}`, `metrics/{key}`, `dependencies/{name}`, `software-development/{commit}`, `data-profiling/...`, `data-processing/...`, `tokenization/...` and `tokenization-stats/...` under `https://w3id.org/aidoc-ap/`.

## Points for the engine (no mapping change can fix them)

- The pilot computes MSE and R² on the test split but logs them with stage "train"; logged with "test", they become measurements of the evaluation activity.
- `drift_metrics.value` is an integer column; drift scores are usually fractions.
- The `[drift_metrics]` keys in `data_metrics` compare a column with its augmented copy; they are data profile values, not post-market drift, and stay with the profiling activity.
- `change_logs.changed_by` holds names such as "ml-team", not user IDs; the proposal maps them to agents of their own.
- The engine records no commit author (S1) and no re-evaluation (O3).
- `model_architecture.model_version` and `model_deployed.model_version` are both mapped to aidoc:version of the model; one of them should be authoritative.
- Columns without a target term: parameter counts and the metric list in `model_architecture`, `experiments.experiment_stage`, `runs.source_type`, `model_deployed.model_cateory` (sic), `labeling_procedures.quality_assurance_methods`.
- The codecarbon values in `resources` and `data_resources` (energy, emissions, duration) are measurements of a run rather than computational resources; they keep the current mapping.
