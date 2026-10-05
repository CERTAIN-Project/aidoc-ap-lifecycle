#!/usr/bin/env python3
"""Lift the RDF output of the Semantic MLOps Engine to the terms of the Lifecycle Extension,
without changing the engine.

File mode (an RDF export of the engine, for example ontop/input/knowledge_graph.rdf):
  the cleanup (mappings/adapter/cleanup.ru) removes the statements the lift rules replace, and
  the lift rules (mappings/adapter/lift/*.rq, SPARQL CONSTRUCT) add module and core terms.
  Output: cleaned engine graph plus lifted triples.
Endpoint mode (--endpoint, the engine's read-only SPARQL endpoint): the lift rules run on the
  endpoint; the output holds only the lifted triples, to be used next to the engine graph.

The report compares the graph before and after: nodes typed both prov:Activity and prov:Entity
(disjoint in PROV), triples with predicates declared nowhere, domain violations of core and
module predicates (on the types present in the graph), and triples per lift rule.

  python3 scripts/adapt_engine_graph.py --input vendor/engine/ontop/input/knowledge_graph.rdf
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import urllib.parse
import urllib.request
from collections import Counter

from rdflib import Graph, URIRef
from rdflib.namespace import PROV, RDF, RDFS

from common import CORE_TTL, LC_NS, MODULE_TTL, REPORTS, ROOT, load_graph, qname, reference_graph
from r2rml_gap import STANDARD_NS, _domain_members, _superclasses

ADAPTER = ROOT / "mappings" / "adapter"


def run_construct_remote(endpoint: str, query: str) -> Graph:
    data = urllib.parse.urlencode({"query": query}).encode()
    req = urllib.request.Request(endpoint, data=data, headers={"Accept": "text/turtle"})
    with urllib.request.urlopen(req, timeout=300) as resp:  # noqa: S310 (endpoint given by the user)
        return Graph().parse(data=resp.read().decode("utf-8"), format="turtle")


def metrics(g: Graph, kb: Graph) -> dict:
    activities = set(g.subjects(RDF.type, PROV.Activity))
    both = {x for x in activities if (x, RDF.type, PROV.Entity) in g}
    undeclared = Counter()
    violations = Counter()
    supers = {}
    for s, p, o in g:
        if p == RDF.type or str(p).startswith(STANDARD_NS):
            continue
        if (p, None, None) not in kb:
            undeclared[qname(p)] += 1
            continue
        doms = [d for dn in kb.objects(p, RDFS.domain) for d in _domain_members(kb, dn) if isinstance(d, URIRef)]
        if not doms or not (str(p).startswith(("https://w3id.org/aidoc-ap#", LC_NS))):
            continue
        types = set(g.objects(s, RDF.type))
        if not types:
            continue
        sup = set()
        for t in types:
            if t not in supers:
                supers[t] = _superclasses(kb, t)
            sup |= supers[t]
        if not set(doms) & sup:
            violations[qname(p)] += 1
    module_triples = sum(1 for s, p, o in g if str(p).startswith(LC_NS) or (p == RDF.type and str(o).startswith(LC_NS)))
    return {"triples": len(g), "activity_and_entity": len(both), "undeclared": undeclared,
            "domain_violations": violations, "module_triples": module_triples}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", nargs="*", default=[], help="RDF export(s) of the engine (file mode)")
    ap.add_argument("--endpoint", help="SPARQL endpoint of the engine (endpoint mode)")
    ap.add_argument("--out", default=str(REPORTS / "engine_lifted.ttl"))
    ap.add_argument("--report", default=str(REPORTS / "adapter_report.md"))
    args = ap.parse_args()
    if bool(args.input) == bool(args.endpoint):
        print("ERROR: give either --input file(s) or --endpoint")
        return 1

    rules = sorted((ADAPTER / "lift").glob("*.rq"))
    lifted, per_rule = Graph(), {}
    if args.endpoint:
        for r in rules:
            res = run_construct_remote(args.endpoint, r.read_text(encoding="utf-8"))
            per_rule[r.stem] = len(res)
            lifted += res
        out = lifted
        before = None
    else:
        g = Graph()
        for f in args.input:
            g.parse(f)
        kb = load_graph([CORE_TTL, MODULE_TTL]) + reference_graph()
        before = metrics(g, kb)
        for r in rules:
            res = g.query(r.read_text(encoding="utf-8")).graph
            per_rule[r.stem] = len(res)
            lifted += res
        cleaned = Graph()
        cleaned += g
        cleaned.update((ADAPTER / "cleanup.ru").read_text(encoding="utf-8"))
        removed = len(g) - len(cleaned)
        out = cleaned + lifted
        after = metrics(out, kb)

    for prefix, ns in [("aidoc", "https://w3id.org/aidoc-ap#"), ("aidoc-lc", LC_NS), ("prov", str(PROV)),
                       ("dqv", "http://www.w3.org/ns/dqv#"), ("mls", "http://www.w3.org/ns/mls#")]:
        out.bind(prefix, ns)
    REPORTS.mkdir(exist_ok=True)
    out.serialize(destination=args.out, format="turtle")

    lines = ["# Adapter report", "",
             f"Input: {', '.join(pathlib.Path(f).name for f in args.input) or args.endpoint}. "
             f"Output: {pathlib.Path(args.out).name}.", "",
             "| Lift rule | Triples |", "|---|---|", *[f"| {k} | {v} |" for k, v in per_rule.items()], ""]
    if before is not None:
        lines += ["| Measure | Engine graph | After cleanup and lifting |", "|---|---|---|",
                  f"| Triples | {before['triples']} | {after['triples']} (removed {removed}, lifted {len(lifted)}) |",
                  f"| Nodes typed prov:Activity and prov:Entity | {before['activity_and_entity']} | {after['activity_and_entity']} |",
                  f"| Triples with predicates declared nowhere | {sum(before['undeclared'].values())} | {sum(after['undeclared'].values())} |",
                  f"| Domain violations of core and module predicates | {sum(before['domain_violations'].values())} | {sum(after['domain_violations'].values())} |",
                  f"| Triples with module terms | {before['module_triples']} | {after['module_triples']} |", ""]
        for label, key in [("Undeclared predicates after", "undeclared"), ("Domain violations after", "domain_violations")]:
            if after[key]:
                lines += [f"{label}: " + ", ".join(f"{k} ({v})" for k, v in after[key].most_common()), ""]
        lines += ["The engine graph is materialised with RDFS entailment, so its domain conflicts appear as extra "
                  "types (for example data split activities typed aidoc:Dataset) rather than as domain violations; "
                  "the activity-and-entity count shows them.", ""]
    open(args.report, "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
