# Examples

Small instance graphs that show the Lifecycle Extension on realistic data. `make cq` loads every `*.ttl` file in this folder together with the AIDOC-AP core and the module and runs the competency queries in cq/ over them. Instance IRIs use the namespace `https://w3id.org/aidoc-ap/lifecycle/example/`.

The graphs are examples, not records. Values that the Semantic MLOps Engine does not record are marked as illustrative in the files.

## energy_pilot_lifecycle.ttl

The lifecycle of an hourly load forecasting model for Germany, from data ingestion to decommissioning. Training values come from the materialised pilot graph of the Semantic MLOps Engine (Open Power System Data time series, XGBoost regressor, Optuna search); packaging, build testing, deployment and decommissioning values from the engine's full lifecycle pilot script.

| Stage | What the example shows | Module terms |
|---|---|---|
| D1 | download of the OPSD time series; the acquisition method stays on the dataset | (core only) |
| D2 | whylogs profile of the cleaned data as quality measurements | producesMeasurement |
| D3 | forward fill and outlier removal by interquartile range | processingTechnique, hasHyperParameterSetting |
| D5 | augmentation of the load column with Gaussian noise | DataAugmentation, processingTechnique, hasHyperParameterSetting |
| D6 | chronological split into training and test data | (core only) |
| M1 | training run with its hyperparameters, loss function and compute resources | producesModel, hasHyperParameterSetting, usesComputationalResource |
| M2 | hold-out evaluation with MSE and R² | evaluates, producesMeasurement, producesTestReport |
| M3 | packaging as an MLflow model with its dependencies | packagesModel, packagingFormat |
| M4 | registration of v1 for production, its archival, registration of v2 | versionsModel, assignsRegistryStage |
| S1, S4 | training code, its developer, its commit and the change records | producesSoftware, versionsSoftware, producesChangeRecord |
| S2 | build and integration test of the packaged model | testsArtifact, buildStatus, testLevel, producesTestReport |
| S3 | deployment with serving endpoint and container | deploys, servingEndpoint, usesComputationalResource |
| O2 | drift of the load distribution after deployment (illustrative) | monitors, producesMeasurement |
| O3 | re-evaluation on a hold-out set, followed by retraining and decommissioning (illustrative) | evaluates, producesMeasurement, with prov:wasInformedBy |
| O4 | decommissioning of v1 with reason and actions | decommissions, decommissioningReason, decommissioningAction |

## text_classifier_tokenization.ttl

Tokenization of the training split of a text classifier. Tokenizer settings are ML Schema hyperparameter settings and the statistics per split are DQV quality measurements, so the module needs no NLP-specific properties. All values are illustrative; the fields follow the tokenizer logging of the Semantic MLOps Engine.

## Querying the examples

```bash
make cq
```

The report in reports/cq.md lists each competency query with the number of rows it returns over these graphs.
