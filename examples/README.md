# Examples

Small instance graphs (Turtle) that show the module terms on realistic data. `make cq` loads every `*.ttl` file here together with the core and the module.

Sources for realistic values:

- vendor/engine/ontop/input/knowledge_graph.rdf: materialised graph from the engine (about 30,000 triples; data, training and evaluation stages). Extract small, labelled slices; do not copy the whole graph.
- vendor/engine/test_docker/lifecycle/log_deployment_compliance.py and log_decommission_compliance.py: values for packaging, build and integration testing, deployment and decommissioning (stages that the materialised graph does not contain).
- vendor/engine/test_docker/test_full_lifecycle_pilot.py: a full pilot run.

Conventions: one file per scenario (for example `energy_pilot_lifecycle.ttl`), instance IRIs under `https://w3id.org/aidoc-ap/lifecycle/example/`, and an rdfs:comment on the graph's main resources saying that the data is illustrative.
