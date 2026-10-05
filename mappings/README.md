# Using the Lifecycle Extension with the Semantic MLOps Engine

The Semantic MLOps Engine maps its database to the AIDOC-AP core with R2RML and publishes the result through Ontop. The engine itself is not changed. This folder offers two ways to bring its metadata to the terms of the Lifecycle Extension:

| | (a) Adapter over the engine's RDF output | (b) R2RML overlay with its own Ontop endpoint |
|---|---|---|
| Needs | the engine's SPARQL endpoint or an RDF export | read-only access to the engine database |
| Folder | `adapter/` | `r2rml/` |
| Recovers | everything the engine already maps, corrected and lifted to module terms | in addition the columns the engine does not map |
| Check | `make adapter-check` | `make overlay-check` |

Both paths are based on the engine at commit b41ea27.

## (a) Adapter over the RDF output

`adapter/lift/*.rq` holds 19 SPARQL CONSTRUCT rules, one per engine pattern, that derive module and core statements from what the engine publishes. For example, a deployment that `prov:used` a model becomes `aidoc-lc:deploys`, and MLflow parameters become ML Schema hyperparameter settings of the experiment and of the run. `adapter/cleanup.ru` (SPARQL Update) removes, from an RDF export, the engine statements that the rules replace, the predicates no vocabulary declares, and the types that RDFS entailment derives from the engine's domain conflicts.

```bash
python3 scripts/adapt_engine_graph.py --input export.ttl --out lifted.ttl
python3 scripts/adapt_engine_graph.py --endpoint http://localhost:8080/sparql --out lifted.ttl
```

With an export, the output is the cleaned engine graph plus the lifted triples. With the endpoint, which is read-only, the output holds only the lifted triples; query it together with the engine graph, in which the engine's own conflicting statements remain.

`make adapter-check` runs the adapter on the materialised pilot graph of the engine (`ontop/input/knowledge_graph.rdf`, about 30,000 triples, data, training and evaluation) together with `adapter/engine_output_sample.ttl`, which reproduces the engine output for the stages the pilot graph lacks (deployment, packaging, versioning, testing, monitoring, decommissioning, change logs, code), and then runs the competency queries over the result:

| Measure | Engine graph | After the adapter |
|---|---|---|
| Nodes typed both prov:Activity and prov:Entity (disjoint in PROV) | 128 | 0 |
| Triples with predicates declared nowhere | 290 | 0 |
| Domain violations of core and module predicates | 108 | 0 |
| Triples with module terms | 0 | 1606 |

15 of the 18 competency queries return rows. The other three have no data in the engine output: augmentation and tokenization are not mapped by the engine, and the engine records no re-evaluation.

What the adapter cannot recover, because the engine's RDF does not contain it: build status, test type and test results; decommissioning reason and actions; packaging dependencies; tokenizer configuration and statistics; augmentation as a stage of its own; whether a metric belongs to an evaluation when the engine logs it with stage "train". Technique names of a cleaning step arrive as one text value (`{a,b}`), because SPARQL 1.1 cannot split strings.

## (b) R2RML overlay with its own Ontop endpoint

`r2rml/aidoc-lc_overlay.ttl` replaces 36 triples maps of the engine mapping (same names), adds 38 and, through `r2rml/removed_triples_maps.txt`, drops 2. Each triples map carries a comment on what it changes and why. Engine mapping plus overlay form this repository's own mapping; the engine keeps its own.

```bash
make overlay-build      # merged mapping and framework ontology into reports/ontop/
cp mappings/r2rml/ontop/lifecycle.properties.example reports/ontop/lifecycle.properties   # add read-only credentials
docker compose -f mappings/r2rml/ontop/docker-compose.yml up -d                             # SPARQL endpoint on port 8081
```

The ontology given to Ontop is core v1.2 plus the module (`make merged`). Ontop uses its OWL 2 QL part; the union domains of the module lie outside that profile and are expected to be ignored, which does not affect the mapped triples.

`make overlay-check` merges the mappings and checks the overlay: tables and qualified columns exist in the engine schema; every column a template, `rr:column` or join uses is produced by the SQL; every class and predicate is declared; every module concept a `CASE` expression produces exists. On the merged mapping it checks domains and ranges, inferring the classes of link-only triples maps from other triples maps with the same subject template. A deliberately broken overlay fails each of these checks. It then repeats the gap analysis on the merged mapping:

| | Engine mapping | Merged with the overlay |
|---|---|---|
| Terms declared nowhere | 5 | 0 |
| Domain conflicts | 28 | 0 |
| Domain and range conflicts with template inference | 29 and 2 | 0 and 0 |
| Columns not mapped | 48 | 23 |
| Columns mapped only with generic predicates | 59 | 48 |

These checks are static. The SQL has not run against PostgreSQL and the merged mapping has not run in Ontop; the first deployment with database access is that test.

Changed IRI templates (overlay only): model versioning records `model-versioning/{run_id}/{model_id}/{deployment_id}`; data profile measurements `data/{run_id}/{data_id}/metric/{stage}/{key}`; weight statistics `.../weights/{layer_name}/step/{step}/{statistic}`; data technique parameters `data/{run_id}/{data_id}/technique/{technique_name}/parameter/{name}`. New resources use `hyperparameters/`, `metrics/`, `dependencies/`, `software-development/`, `data-profiling/`, `data-processing/`, `tokenization/` and `tokenization-stats/` under `https://w3id.org/aidoc-ap/`.

## Limits of the engine data

Neither path can fix what the engine records:

- The pilot computes MSE and R² on the test split but logs them with stage "train"; they are therefore not linked to an evaluation activity.
- `drift_metrics.value` is an integer column; drift scores are usually fractions.
- The `[drift_metrics]` keys in `data_metrics` compare a column with its augmented copy; they are data profile values, not post-market drift.
- `change_logs.changed_by` holds names such as "ml-team", not user IDs; both paths map them to agents of their own.
- The engine records no commit author (S1) and no re-evaluation (O3).
- `model_architecture.model_version` and `model_deployed.model_version` both describe the model version.
- Columns without a target term: parameter counts and the metric list in `model_architecture`, `experiments.experiment_stage`, `runs.source_type`, `model_deployed.model_cateory` (sic), `labeling_procedures.quality_assurance_methods`.
