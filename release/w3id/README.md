# w3id redirect for the Lifecycle Extension

The redirects of AIDOC-AP live in `ids/aidoc-ap/.htaccess` of the [w3id repository](https://github.com/perma-id/w3id.org). Its last rule forwards every path below `aidoc-ap/` to `https://certain-project.github.io/aidoc-ap/`, so `https://w3id.org/aidoc-ap/lifecycle` currently ends on a missing page of the core site.

`aidoc-ap.htaccess` in this folder is the complete proposed file: the current file of the w3id repository with the rules for `lifecycle` inserted before the default rules. The core's rules are unchanged. The pull request replaces `ids/aidoc-ap/.htaccess` with it; submit it once the documentation site of the extension is online, so that the redirects do not lead to missing pages.

The file was tested in Apache 2.4 with the same modules as w3id (mod_rewrite, mod_headers):

| Request | Location |
|---|---|
| `https://w3id.org/aidoc-ap/lifecycle` | `https://certain-project.github.io/aidoc-ap-lifecycle/` |
| same, `Accept: text/turtle` | `.../aidoc-ap-lifecycle/aidoc-lc.ttl` |
| same, `Accept: application/rdf+xml` or `application/owl+xml` | `.../aidoc-ap-lifecycle/ontology.owl` |
| same, `Accept: application/ld+json` | `.../aidoc-ap-lifecycle/ontology.jsonld` |
| `https://w3id.org/aidoc-ap/lifecycle/1.0` | `.../aidoc-ap-lifecycle/1.0/aidoc-lc.ttl` |
| `https://w3id.org/aidoc-ap/lifecycle/example/...` | `.../aidoc-ap-lifecycle/examples.html` |
| `https://w3id.org/aidoc-ap/` and other core paths | unchanged |

After the merge, check the live redirects with `curl -sI` and the same `Accept` headers.
