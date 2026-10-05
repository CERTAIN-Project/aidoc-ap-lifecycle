# KPI 1.1: Ontology Coverage Index (OCI)

The method is fixed. Its machine-readable form is method/stage_profile.json and the queries in method/queries/; scripts/oci.py evaluates them. Changes need the approval of the T5.3 lead.

## Definition

The OCI measures the extent to which the ontology framework represents the stages of the AI system lifecycle. It is computed over the classes and properties of the framework (AIDOC-AP core plus extension modules), without instance data and without LLM judgement. For each stage of a reference lifecycle model three criteria are tested; the coverage of a stage is the share of criteria it satisfies, and the OCI is the mean over all stages.

Target: OCI ≥ 0.90 and no stage with coverage 0.

## Reference lifecycle model (18 stages)

The stages come from sources outside AIDOC-AP, so that the index does not measure the ontology against itself.

| ID | Phase | Stage | Core class(es) | Sources |
|---|---|---|---|---|
| D1 | Data pipeline | Data ingestion | aidoc:DataAcquisitionActivity | ml-ops.org end-to-end workflow: "Data Ingestion" |
| D2 | Data pipeline | Exploration and validation | aidoc:ExplorationAndValidation | ml-ops.org: "Exploration and Validation" |
| D3 | Data pipeline | Data wrangling (cleaning) | aidoc:DataWrangling, aidoc:DataCleaningProcedure | ml-ops.org: "Data Wrangling (Cleaning)" |
| D4 | Data pipeline | Data labelling | aidoc:LabelingProcedure | ml-ops.org: "Data Labeling" |
| D5 | Data pipeline | Data preparation (transformation, feature engineering) | aidoc:DataProcessing | CRISP-ML(Q): "Data Preparation" |
| D6 | Data pipeline | Data splitting | aidoc:DataTraining, aidoc:DataValidation, aidoc:DataTesting | ml-ops.org: "Data Splitting" |
| M1 | ML pipeline | Model training and engineering | aidoc:ModelEngineering | ml-ops.org: "Model Training"; ISO/IEC 22989 development |
| M2 | ML pipeline | Model evaluation and testing | aidoc:ModelEvaluation | ml-ops.org: "Model Evaluation", "Model Testing"; ISO/IEC 22989 verification and validation |
| M3 | ML pipeline | Model packaging | aidoc:ModelPackaging | ml-ops.org: "Model Packaging" |
| M4 | ML pipeline | Model versioning | aidoc:ModelVersioning | ml-ops.org three levels: versioning of model specifications; AI Act Annex IV 1(c) |
| S1 | Code pipeline | Software development | aidoc:SoftwareDevelopment | ISO/IEC 22989 design and development; ml-ops.org code level |
| S2 | Code pipeline | Build and integration testing | aidoc:BuildAndIntegrationTesting | ISO/IEC 22989 verification; ml-ops.org code level [verify wording] |
| S3 | Code pipeline | Deployment and model serving | aidoc:Deployment | ml-ops.org: "Model Serving"; ISO/IEC 22989 deployment |
| S4 | Code pipeline | Software versioning and change management | aidoc:SoftwareVersioning | AI Act Annex IV 1(c) and 6; ISO/IEC 22989 update |
| O1 | Operation | Performance monitoring and logging | aidoc:DataMonitoringAndLogging | ml-ops.org: "Model Performance Monitoring", "Model Performance Logging"; ISO/IEC 22989 operation and monitoring; AI Act Art. 12 |
| O2 | Operation | Post-market monitoring | aidoc:PostMarketMonitoringActivity | AI Act Art. 72 |
| O3 | Operation | Re-evaluation | aidoc:PostMarketPerformanceEvaluationActivity | ISO/IEC 22989 re-evaluation |
| O4 | Operation | Retirement and decommissioning | aidoc:Decommissioning | ISO/IEC 22989 retirement (decommissioning) |

Sources. ml-ops.org: L. Visengeriyeva, A. Kammer, I. Bär, A. Kniesz, M. Plöd, "End-to-end Machine Learning Workflow" and "Three Levels of ML Software", https://ml-ops.org (stage names checked on 2 October 2026). ISO/IEC 22989:2022 stages are cited through DPV-AI, which models them as dpv-ai:InceptionStage ... dpv-ai:RetirementStage with dct:source "ISO/IEC 22989:2022" (vendored, already aligned with AIDOC-AP). CRISP-ML(Q): Studer et al., Machine Learning and Knowledge Extraction 3(2), 2021 [verify citation]. AI Act: Regulation (EU) 2024/1689.

Not included as stages: ISO/IEC 22989 inception and design, which Annex IV records on the system and on model engineering; continuous validation, which is part of O1 and O3; data augmentation, which is part of data preparation (D5).

## Criteria

All three criteria only count terms defined in a framework namespace (`https://w3id.org/aidoc-ap#`, `https://w3id.org/aidoc-ap/lifecycle#`). owl:unionOf domains and ranges are expanded.

- **C1 Concept.** Every class listed for the stage exists and is a (transitive) subclass of aidoc:AIActivity, which the core declares a subclass of prov:Activity. Query: method/queries/c1_concept.rq.
- **C2 Traceability.** An object property has as domain the stage class or one of its superclasses strictly below aidoc:AIActivity (the pipeline class), and as range a class that is an aidoc:AIArtifact or a prov:Entity. Query: method/queries/c2_traceability.rq.
- **C3 Description.** At least one object or datatype property has the stage class itself as domain. Query: method/queries/c3_description.rq.

What does not count: the PROV-O relations every activity inherits (prov:used, prov:generated, prov:wasAssociatedWith); properties on aidoc:AIActivity itself, such as aidoc:affects; SKOS mappings (they carry no domain or range); properties of reference vocabularies that the module does not specialise.

Coverage of a stage = (number of satisfied criteria) / 3. OCI = mean over the 18 stages. Per-phase means are reported as well.

## Baseline: AIDOC-AP core v1.2 (reproduce with `make oci-core`)

OCI = **0.574**. Data pipeline 0.833, ML pipeline 0.417, code pipeline 0.417, operation 0.500.

| ID | C1 | C2 | C3 | Coverage | Missing |
|---|---|---|---|---|---|
| D1 | yes | yes | no | 0.67 | C3 |
| D2 | yes | yes | no | 0.67 | C3 |
| D3 | yes | yes | yes | 1.00 | |
| D4 | yes | yes | yes | 1.00 | |
| D5 | yes | yes | no | 0.67 | C3 |
| D6 | yes | yes | yes | 1.00 | |
| M1 | yes | no | no | 0.33 | C2, C3 |
| M2 | yes | no | yes | 0.67 | C2 |
| M3 | yes | no | no | 0.33 | C2, C3 |
| M4 | yes | no | no | 0.33 | C2, C3 |
| S1 | yes | no | yes | 0.67 | C2 |
| S2 | yes | no | no | 0.33 | C2, C3 |
| S3 | yes | no | no | 0.33 | C2, C3 |
| S4 | yes | no | no | 0.33 | C2, C3 |
| O1 | yes | yes | yes | 1.00 | |
| O2 | yes | no | no | 0.33 | C2, C3 |
| O3 | yes | no | no | 0.33 | C2, C3 |
| O4 | yes | no | no | 0.33 | C2, C3 |

23 of 54 criteria are open: 11 × C2 (M1 to M4, S1 to S4, O2 to O4) and 12 × C3 (D1, D2, D5, M1, M3, M4, S2 to S4, O2 to O4). The target needs at least 49 of 54 satisfied criteria, so at most 5 may stay open.
