#!/usr/bin/env python3
"""Build the extra pages of the module documentation, next to the Widoco reference.

examples.html: one section per lifecycle stage with the competency questions of that stage,
  the SPARQL query, its result over the example graphs and the example data behind the result.
coverage.html: the Ontology Coverage Index of the core and of core plus module, per stage.

Input: examples/*.ttl, examples/README.md (stage descriptions), cq/*.rq, method/stage_profile.json,
reports/oci_core.json and reports/oci_framework.json (run `make oci-core oci` first).

  python3 scripts/build_docs_pages.py --out site-extra
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import shutil
import sys

from rdflib import Graph, URIRef

from common import CORE_TTL, CQ_DIR, EXAMPLES_DIR, LC_NS, MODULE_TTL, PROFILE, REPORTS, ROOT, load_graph

EX_NS = "https://w3id.org/aidoc-ap/lifecycle/example/"
PREFIXES = {
    "aidoc": "https://w3id.org/aidoc-ap#", "aidoc-lc": LC_NS, "ex": EX_NS, "prov": "http://www.w3.org/ns/prov#",
    "dqv": "http://www.w3.org/ns/dqv#", "mls": "http://www.w3.org/ns/mls#", "dcterms": "http://purl.org/dc/terms/",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#", "xsd": "http://www.w3.org/2001/XMLSchema#",
    "dpv-aiact": "https://w3id.org/dpv/legal/eu/aiact#", "skos": "http://www.w3.org/2004/02/skos/core#",
}
STAGE_ORDER = ["D1", "D2", "D3", "D4", "D5", "D6", "M1", "M2", "M3", "M4", "S1", "S2", "S3", "S4", "O1", "O2", "O3", "O4"]


def short(v) -> str:
    if v is None:
        return ""
    s = str(v)
    for p, ns in PREFIXES.items():
        if isinstance(v, URIRef) and s.startswith(ns):
            return f"{p}:{s[len(ns):]}"
    return s


def header(text: str) -> dict:
    out = {}
    for key in ("CQ", "Stage", "Terms"):
        m = re.search(rf"^#\s*{key}:\s*(.+)$", text, re.M)
        out[key] = m.group(1).strip() if m else ""
    return out


def stage_notes() -> dict:
    """Stage -> description, from the table in examples/README.md."""
    notes = {}
    for line in (EXAMPLES_DIR / "README.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*([DMSO]\d(?:,\s*[DMSO]\d)*)\s*\|\s*([^|]+)\|", line)
        if m:
            for st in re.split(r",\s*", m.group(1)):
                notes[st] = m.group(2).strip()
    return notes


def turtle_of(data: Graph, nodes: list) -> str:
    sub = Graph()
    for p, ns in PREFIXES.items():
        sub.bind(p, ns)
    for n in nodes:
        for t in data.triples((n, None, None)):
            sub.add(t)
    text = sub.serialize(format="turtle")
    return "\n".join(l for l in text.splitlines() if not l.startswith("@prefix")).strip()


def page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="assets/lifecycle.css">
</head>
<body>
<header><nav><a href="index.html">AIDOC-AP Lifecycle Extension</a> · <a href="examples.html">Worked examples</a> · <a href="coverage.html">Coverage</a></nav></header>
<main>
{body}
</main>
<footer>AIDOC-AP Lifecycle Extension · CERTAIN project (Horizon Europe, grant agreement 101189650) · CC BY 4.0</footer>
</body>
</html>
"""


def examples_page() -> str:
    files = sorted(EXAMPLES_DIR.glob("*.ttl"))
    data = Graph()
    for f in files:
        data.parse(f)
    g = load_graph([CORE_TTL, MODULE_TTL, *files])
    profile = {s["id"]: s for s in json.loads(PROFILE.read_text())["stages"]}
    notes = stage_notes()
    by_stage = {}
    for f in sorted(CQ_DIR.glob("*.rq")):
        text = f.read_text(encoding="utf-8")
        by_stage.setdefault(header(text)["Stage"], []).append((f, text))

    parts = ["<h1>Worked examples</h1>",
             "<p class=\"lead\">How the module describes each stage of the AI system lifecycle, shown on two example "
             "graphs: the lifecycle of an energy load forecasting model of the CERTAIN energy pilot, from data "
             "ingestion to decommissioning, and the tokenization step of a text classifier. Each stage lists "
             "competency questions as they would be asked by a provider, an auditor or an ML engineer, the SPARQL "
             "query, its answer over the examples, and the example data behind the answer. Values marked as "
             "illustrative in the example files are not recorded by the Semantic MLOps Engine.</p>",
             "<p>Example graphs: " + ", ".join(f'<a href="examples/{f.name}">{f.name}</a>' for f in files) + ".</p>",
             "<nav class=\"toc\">" + " ".join(f'<a href="#{s}">{s}</a>' for s in STAGE_ORDER if s in by_stage) + "</nav>"]
    for st in STAGE_ORDER:
        if st not in by_stage:
            continue
        prof = profile[st]
        parts.append(f'<section id="{st}"><h2>{st} {html.escape(prof["label"])}</h2>')
        if st in notes:
            parts.append(f"<p class=\"hint\">{html.escape(notes[st][:1].upper() + notes[st][1:])}.</p>")
        for f, text in by_stage[st]:
            h = header(text)
            res = g.query(text)
            cols = [str(v) for v in res.vars]
            rows = list(res)
            parts.append(f"<article><h3>{html.escape(h['CQ'])}</h3>")
            parts.append("<p class=\"terms\">Module terms: " + ", ".join(f"<code>{html.escape(t.strip())}</code>"
                                                                   for t in h["Terms"].split(",") if t.strip()) + "</p>")
            table = ["<table><thead><tr>" + "".join(f"<th>{html.escape(c)}</th>" for c in cols) + "</tr></thead><tbody>"]
            for r in rows[:12]:
                table.append("<tr>" + "".join(f"<td>{html.escape(short(v))}</td>" for v in r) + "</tr>")
            table.append("</tbody></table>")
            if len(rows) > 12:
                table.append(f"<p class=\"hint\">{len(rows) - 12} further rows.</p>")
            parts.append("".join(table))
            nodes = []
            for r in rows[:3]:
                for v in r:
                    if isinstance(v, URIRef) and str(v).startswith(EX_NS) and v not in nodes \
                            and any(str(p).startswith(LC_NS) for p in data.predicates(v, None)):
                        nodes.append(v)
            if nodes:
                parts.append("<details><summary>Example data</summary><pre>" + html.escape(turtle_of(data, nodes[:2])) + "</pre></details>")
            query = "\n".join(l for l in text.splitlines() if not l.startswith("#")).strip()
            parts.append(f"<details><summary>SPARQL query ({f.name})</summary><pre>" + html.escape(query) + "</pre></details></article>")
        parts.append("</section>")
    return page("Worked examples · AIDOC-AP Lifecycle Extension", "\n".join(parts))


def coverage_page() -> str:
    core = json.loads((REPORTS / "oci_core.json").read_text())
    fw = json.loads((REPORTS / "oci_framework.json").read_text())
    core_by = {s["id"]: s for s in core["stages"]}
    yes = lambda b: "✓" if b else "–"
    rows = []
    for s in fw["stages"]:
        c = core_by[s["id"]]
        rows.append(f"<tr><td>{s['id']}</td><td>{html.escape(s['stage'])}</td>"
                    f"<td>{yes(c['C1'])} {yes(c['C2'])} {yes(c['C3'])}</td><td>{c['coverage']:.2f}</td>"
                    f"<td>{yes(s['C1'])} {yes(s['C2'])} {yes(s['C3'])}</td><td>{s['coverage']:.2f}</td></tr>")
    phases = "".join(f"<tr><td>{html.escape(k)}</td><td>{core['per_phase'][k]:.3f}</td><td>{v:.3f}</td></tr>"
                     for k, v in fw["per_phase"].items())
    body = f"""<h1>Lifecycle coverage</h1>
<p class="lead">The Ontology Coverage Index (CERTAIN KPI 1.1) measures how far the ontology framework represents the
stages of the AI system lifecycle. Each of 18 reference stages is tested against three criteria: C1, an activity class
for the stage exists; C2, a property links the stage to a typed artefact; C3, a property is defined on the stage class
itself. The coverage of a stage is the share of criteria it meets, and the index is the mean over all stages. The
criteria are SPARQL queries over the ontology files; the method is described in
<a href="https://github.com/CERTAIN-Project/aidoc-ap-lifecycle/blob/main/docs/02_oci_method.md">docs/02_oci_method.md</a>.</p>
<p class="kpi">AIDOC-AP core v1.2: <b>{core['oci']:.3f}</b> · core and Lifecycle Extension: <b>{fw['oci']:.3f}</b></p>
<table><thead><tr><th>Phase</th><th>Core</th><th>Core and extension</th></tr></thead><tbody>{phases}</tbody></table>
<table><thead><tr><th>ID</th><th>Stage</th><th>Core C1 C2 C3</th><th>Core</th><th>With extension C1 C2 C3</th><th>With extension</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p class="hint">Data ingestion (D1) keeps C3 open: the core already records how data was obtained, on the dataset
(aidoc:dataCollectionMethod), and the extension does not repeat it on the activity.</p>"""
    return page("Coverage · AIDOC-AP Lifecycle Extension", body)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(REPORTS / "site-extra"))
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    (out / "assets").mkdir(parents=True, exist_ok=True)
    (out / "examples").mkdir(exist_ok=True)
    (out / "examples.html").write_text(examples_page(), encoding="utf-8")
    (out / "coverage.html").write_text(coverage_page(), encoding="utf-8")
    shutil.copy(ROOT / "documentation" / "assets" / "lifecycle.css", out / "assets" / "lifecycle.css")
    for f in EXAMPLES_DIR.glob("*.ttl"):
        shutil.copy(f, out / "examples" / f.name)
    print(f"wrote {out}/examples.html, {out}/coverage.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
