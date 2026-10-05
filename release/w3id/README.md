# w3id redirect for the Lifecycle Extension

`https://w3id.org/aidoc-ap/lifecycle` currently falls under the rules of the core, which forward every path below `aidoc-ap/` to `https://certain-project.github.io/aidoc-ap/`. Because the module is documented from its own repository, `htaccess-lifecycle.txt` adds rules for `lifecycle` that go before those of the core in `aidoc-ap/.htaccess` of the [w3id repository](https://github.com/perma-id/w3id.org). The change is a pull request to that repository, submitted by the maintainer once the documentation site is public.

After the merge, these requests should give the following locations:

| Request | Expected location |
|---|---|
| `curl -sI https://w3id.org/aidoc-ap/lifecycle` | `https://certain-project.github.io/aidoc-ap-lifecycle/` |
| `curl -sI -H "Accept: text/turtle" https://w3id.org/aidoc-ap/lifecycle` | `.../aidoc-ap-lifecycle/aidoc-lc.ttl` |
| `curl -sI -H "Accept: application/rdf+xml" https://w3id.org/aidoc-ap/lifecycle` | `.../aidoc-ap-lifecycle/ontology.owl` |
| `curl -sI https://w3id.org/aidoc-ap/lifecycle/1.0` | `.../aidoc-ap-lifecycle/1.0/aidoc-lc.ttl` |
| `curl -sI https://w3id.org/aidoc-ap/lifecycle/example/training` | `.../aidoc-ap-lifecycle/examples.html` |
| `curl -sI https://w3id.org/aidoc-ap/` | unchanged: `https://certain-project.github.io/aidoc-ap` |
