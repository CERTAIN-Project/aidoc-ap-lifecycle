# Engine mapping proposal (Phase 5)

`aidoc-lc_r2rml_proposal.ttl` will hold R2RML triples maps (or changes to existing ones) that connect the Semantic MLOps Engine tables to the new module terms. Base: vendor/engine/ontop/input/aidoc-ap_r2rml.ttl at commit b41ea27.

This is a proposal to be agreed with the T5.4 partners according to their roles. Do not change the engine repository from here.

Include, besides the new terms, the fixes that need no new term (see the gap analysis, `make gap`):

- columns the core can already represent (for example annotator_details and annotation_tools to aidoc:annotatorType and aidoc:annotationTool)
- terms used by the mappings but declared nowhere (mls:hasObjective, mls:hasOptimizer, mls:hasModelParameter, prov:wasUsedBy, aidoc:VisualDocumentation)
- rows typed as activity and artefact at once, to be split into two IRIs
- the Ontop configuration, which loads core v1.0 and should load v1.2 plus the module

Check the proposal with `make gap` after pointing the gap script at a copy of the mappings that includes the proposal.
