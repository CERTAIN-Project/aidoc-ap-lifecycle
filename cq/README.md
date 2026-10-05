# Competency queries

One SPARQL file per question, named `<stage>_<topic>.rq` (for example `M3_package_format.rq`). Each file starts with three header lines that scripts/run_cqs.py reads:

```sparql
# CQ: In which format was model M packaged for deployment, and which dependencies does the package contain?
# Stage: M3
# Terms: aidoc-lc:packagesModel, aidoc-lc:packageFormat

PREFIX aidoc: <https://w3id.org/aidoc-ap#>
PREFIX aidoc-lc: <https://w3id.org/aidoc-ap/lifecycle#>

SELECT ?packaging ?model ?format WHERE {
  ?packaging a aidoc:ModelPackaging ;
             aidoc-lc:packagesModel ?model .
  OPTIONAL { ?packaging aidoc-lc:packageFormat ?format }
}
```

(The terms in this example are placeholders from the candidate list, not decided terms.)

Write the question the way a provider, auditor or ML engineer would ask it. `make cq` runs every query over the core, the module and the graphs in examples/, and reports the number of rows.
