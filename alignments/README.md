# Alignment proposals (Phase 4)

`proposed.ttl` will hold SKOS mapping proposals (skos:exactMatch, closeMatch, broadMatch, narrowMatch, relatedMatch) from module terms to terms in the reference vocabularies, one mapping per line with a short rationale as a comment.

These are proposals. The core's published alignments were curated by three domain experts (majority vote and adjudication) and are published in the core repository under docs/resources/*-alignments.ttl with the mapping reification used there. New mappings follow the same curation before publication.

Candidate targets already known: dpv-ai lifecycle stages (dpv-ai:DeploymentStage, dpv-ai:ReevaluationStage, dpv-ai:RetirementStage, dpv-ai:DecommissionStage), dcat:packageFormat, mls:HyperParameterSetting, dpv-tech:hasOperatingEnvironment, dpv-aiact:TestReport, dpv-aiact:PostMarketMonitoringPlan.

Mappings whose subject is a core term (for example core stage classes to DPV-AI stages) do not belong into ontology/aidoc-lc.ttl, which describes only its own terms. They can be proposed here as a separate mapping file for the core's alignment process.
