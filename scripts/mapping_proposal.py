#!/usr/bin/env python3
"""Merge the engine R2RML mapping with the proposal in mappings/ and check the result.

Merge: a triples map of mappings/aidoc-lc_r2rml_proposal.ttl replaces the engine triples map
with the same name (fragment after '#'); new names are added; the names listed in
mappings/removed_triples_maps.txt are removed. Output: reports/aidoc-ap_r2rml_merged.ttl.

Checks of the proposal (errors, exit code 1):
  - every triples map has a logical table and a subject map; replaced and removed names exist
    in the engine mapping
  - SQL: tables in FROM/JOIN exist in data_api/app/models.py, qualified columns (alias.column)
    exist in their table, and every column used by rr:column, templates and join conditions is
    produced by the logical table
  - every class and predicate is declared in the core, the module or the reference ontologies
  - every module concept that a CASE expression can produce for a template in the module
    namespace is declared in the module
Checks of the merged mapping (reported; errors with --strict):
  - domain conflicts: the declared rdfs:domain of a predicate does not cover the classes of the
    subject; the classes of a subject are those of every triples map with the same subject
    template (link-only triples maps without rr:class are covered this way)
  - range conflicts: an IRI object whose template is the subject template of a typed triples map,
    and whose classes are not below the declared rdfs:range of the predicate

  python3 scripts/mapping_proposal.py
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from collections import defaultdict

from rdflib import BNode, Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from common import CORE_TTL, LC_NS, MODULE_TTL, REPORTS, ROOT, load_graph, qname, reference_graph
from r2rml_gap import PROV_STARTING_POINT, RR, STANDARD_NS, _domain_members, _superclasses, engine_tables

ENGINE = ROOT / "vendor" / "engine"
SQL_KEYWORDS = {"select", "distinct", "from", "join", "left", "right", "inner", "outer", "cross", "lateral", "on",
                "where", "and", "or", "not", "in", "is", "null", "as", "case", "when", "then", "else", "end", "union",
                "all", "group", "by", "order", "having", "values", "like", "distinct", "true", "false", "cast", "text",
                "bigint", "date", "array", "any", "max", "min", "coalesce", "lower", "unnest", "to_timestamp", "md5"}


def name_of(tm) -> str:
    return str(tm).rsplit("#", 1)[-1]


def closure(g: Graph, node) -> set:
    """All triples reachable from a triples map through blank nodes."""
    out, todo, seen = set(), [node], set()
    while todo:
        n = todo.pop()
        if n in seen:
            continue
        seen.add(n)
        for t in g.triples((n, None, None)):
            out.add(t)
            if isinstance(t[2], BNode):
                todo.append(t[2])
    return out


def split_top(s: str, sep: str = ",") -> list:
    items, depth, cur, quote = [], 0, "", False
    for ch in s:
        if ch == "'":
            quote = not quote
        if not quote:
            depth += ch == "("
            depth -= ch == ")"
        if ch == sep and depth == 0 and not quote:
            items.append(cur)
            cur = ""
        else:
            cur += ch
    items.append(cur)
    return items


def output_columns(sql: str) -> set:
    """Names produced by the first top-level SELECT list (aliases, or bare/qualified columns)."""
    m = re.search(r"\bSELECT\s+(?:DISTINCT\s+)?(.*?)\bFROM\b", sql, re.I | re.S)
    if not m:  # SELECT without FROM, for example "SELECT 'drift' AS metric_key"
        m = re.search(r"\bSELECT\s+(?:DISTINCT\s+)?(.*?)(?:\bUNION\b|$)", sql, re.I | re.S)
    out = set()
    for item in split_top(m.group(1)):
        item = item.strip()
        am = re.search(r"\bAS\s+\"?(\w+)\"?\s*$", item, re.I)
        if am:
            out.add(am.group(1))
        elif re.fullmatch(r"(\w+\.)?\"?\w+\"?", item):
            out.add(item.split(".")[-1].strip('"'))
    return out


def sql_tables(sql: str) -> dict:
    """alias -> table for every 'FROM table [alias]' and 'JOIN table [alias]'."""
    out = {}
    for t, a in re.findall(r"\b(?:FROM|JOIN)\s+(\w+)(?:\s+(?!ON\b|WHERE\b|JOIN\b|LEFT\b|CROSS\b|GROUP\b|UNION\b)(\w+))?", sql, re.I):
        if t.lower() in ("lateral",):
            continue
        out[a or t] = t
        out[t] = t
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine-mapping", default=str(ENGINE / "ontop" / "input" / "aidoc-ap_r2rml.ttl"))
    ap.add_argument("--proposal", default=str(ROOT / "mappings" / "aidoc-lc_r2rml_proposal.ttl"))
    ap.add_argument("--removed", default=str(ROOT / "mappings" / "removed_triples_maps.txt"))
    ap.add_argument("--out", default=str(REPORTS / "aidoc-ap_r2rml_merged.ttl"))
    ap.add_argument("--strict", action="store_true", help="domain and range conflicts are errors")
    args = ap.parse_args()

    engine, proposal = Graph().parse(args.engine_mapping), Graph().parse(args.proposal)
    tables = {t: {c for c, _ in cols} for t, cols in engine_tables(ENGINE / "data_api" / "app" / "models.py").items()}
    module = load_graph([MODULE_TTL])
    kb = load_graph([CORE_TTL, MODULE_TTL]) + reference_graph()
    errors, warnings = [], []

    e_tms = {name_of(tm): tm for tm in engine.subjects(RR.subjectMap, None)}
    p_tms = {name_of(tm): tm for tm in proposal.subjects(RR.subjectMap, None)}
    removed = [ln.split("#")[0].strip() for ln in open(args.removed, encoding="utf-8")]
    removed = [r for r in removed if r]
    for r in removed:
        if r not in e_tms:
            errors.append(f"removed triples map {r} does not exist in the engine mapping")

    # ---- merge
    merged = Graph()
    for prefix, ns in list(engine.namespaces()) + list(proposal.namespaces()):
        merged.bind(prefix, ns, override=False)
    for name, tm in e_tms.items():
        if name not in p_tms and name not in removed:
            for t in closure(engine, tm):
                merged.add(t)
    for tm in p_tms.values():
        for t in closure(proposal, tm):
            merged.add(t)
    # join conditions point to the proposal's IRIs; rewrite references to engine IRIs by name
    m_tms = {name_of(tm): tm for tm in merged.subjects(RR.subjectMap, None)}
    for s, p, o in list(merged.triples((None, RR.parentTriplesMap, None))):
        if name_of(o) in m_tms and o != m_tms[name_of(o)]:
            merged.remove((s, p, o))
            merged.add((s, p, m_tms[name_of(o)]))

    # ---- per triples map checks on the proposal
    def logical(g, tm):
        lt = g.value(tm, RR.logicalTable)
        return (str(g.value(lt, RR.tableName) or "").strip('"') or None), (str(g.value(lt, RR.sqlQuery) or "") or None)

    def outputs(g, tm):
        tname, sql = logical(g, tm)
        if tname:
            return tables.get(tname, set())
        return output_columns(sql)

    def used_columns(g, tm):
        cols = set()
        maps = [g.value(tm, RR.subjectMap)] + [om for pom in g.objects(tm, RR.predicateObjectMap) for om in g.objects(pom, RR.objectMap)]
        for mp in maps:
            if g.value(mp, RR.column):
                cols.add(str(g.value(mp, RR.column)).strip('"'))
            if g.value(mp, RR.template):
                cols |= set(re.findall(r"\{\"?(\w+)\"?\}", str(g.value(mp, RR.template))))
            for jc in g.objects(mp, RR.joinCondition):
                cols.add(str(g.value(jc, RR.child)))
        return cols

    replaced = sorted(n for n in p_tms if n in e_tms)
    added = sorted(n for n in p_tms if n not in e_tms)
    for name, tm in sorted(p_tms.items()):
        sm = proposal.value(tm, RR.subjectMap)
        tname, sql = logical(proposal, tm)
        if sm is None or (tname is None and sql is None):
            errors.append(f"{name}: needs rr:logicalTable and rr:subjectMap")
            continue
        if tname and tname not in tables:
            errors.append(f"{name}: table {tname} does not exist")
        if sql:
            aliases = sql_tables(sql)
            for alias, t in aliases.items():
                if t not in tables and t.lower() not in SQL_KEYWORDS:
                    errors.append(f"{name}: table {t} does not exist")
            for alias, col in re.findall(r"\b([A-Za-z_]\w*)\.\"?(\w+)\"?", sql):
                if alias in aliases and aliases[alias] in tables and col not in tables[aliases[alias]]:
                    errors.append(f"{name}: column {alias}.{col} does not exist in {aliases[alias]}")
        out = outputs(proposal, tm)
        for col in sorted(used_columns(proposal, tm) - out):
            errors.append(f"{name}: column {col} is used but not produced by the logical table (produced: {sorted(out)})")
        for pom in proposal.objects(tm, RR.predicateObjectMap):
            for om in proposal.objects(pom, RR.objectMap):
                ptm = proposal.value(om, RR.parentTriplesMap)
                if ptm is not None:
                    parent_out = outputs(merged, m_tms.get(name_of(ptm), ptm))
                    for jc in proposal.objects(om, RR.joinCondition):
                        if str(proposal.value(jc, RR.parent)) not in parent_out:
                            errors.append(f"{name}: join parent column {proposal.value(jc, RR.parent)} not produced by {name_of(ptm)}")
                tpl = proposal.value(om, RR.template)
                if tpl and str(tpl).startswith(LC_NS) and sql:
                    col = re.findall(r"\{(\w+)\}", str(tpl))[0]
                    m = re.search(r"CASE(?:(?!\bEND\b).)*?END\s+AS\s+" + col + r"\b", sql, re.S | re.I)
                    for concept in re.findall(r"THEN\s+'(\w+)'", m.group(0) if m else ""):
                        if (URIRef(LC_NS + concept), None, None) not in module:
                            errors.append(f"{name}: concept aidoc-lc:{concept} is not declared in the module")
        terms = set(proposal.objects(sm, RR["class"])) | {p for pom in proposal.objects(tm, RR.predicateObjectMap)
                                                         for p in proposal.objects(pom, RR.predicate)}
        for t in terms:
            if not str(t).startswith(STANDARD_NS) and (t, None, None) not in kb:
                errors.append(f"{name}: {qname(t)} is declared nowhere")

    # ---- domain and range conflicts on the merged mapping
    norm = lambda tpl: re.sub(r"\{[^}]*\}", "{}", str(tpl))
    classes_by_tpl = defaultdict(set)
    for tm in m_tms.values():
        sm = merged.value(tm, RR.subjectMap)
        if merged.value(sm, RR.template):
            classes_by_tpl[norm(merged.value(sm, RR.template))] |= {c for c in merged.objects(sm, RR["class"]) if isinstance(c, URIRef)}
    supers = {}

    def all_supers(classes):
        out = set()
        for c in classes:
            if c not in supers:
                supers[c] = _superclasses(kb, c)
            out |= supers[c]
        return out

    conflicts = []
    for name, tm in sorted(m_tms.items()):
        sm = merged.value(tm, RR.subjectMap)
        tpl = merged.value(sm, RR.template)
        s_classes = set(merged.objects(sm, RR["class"])) | (classes_by_tpl.get(norm(tpl), set()) if tpl else set())
        s_supers = all_supers(s_classes)
        for pom in merged.objects(tm, RR.predicateObjectMap):
            for p in merged.objects(pom, RR.predicate):
                doms = [d for dn in kb.objects(p, RDFS.domain) for d in _domain_members(kb, dn) if isinstance(d, URIRef)]
                if s_classes and doms and not PROV_STARTING_POINT <= set(doms) and not set(doms) & s_supers:
                    conflicts.append(f"domain: {name} {qname(p)} (domain {', '.join(qname(d) for d in doms)}; subject {', '.join(sorted(qname(c) for c in s_classes))})")
                rngs = [r for rn in kb.objects(p, RDFS.range) for r in _domain_members(kb, rn)
                        if isinstance(r, URIRef) and r not in (RDFS.Resource, OWL.Thing)]
                for om in merged.objects(pom, RR.objectMap):
                    otpl = merged.value(om, RR.template)
                    o_classes = classes_by_tpl.get(norm(otpl), set()) if otpl else set()
                    if rngs and o_classes and not PROV_STARTING_POINT <= set(rngs) and not set(rngs) & all_supers(o_classes):
                        conflicts.append(f"range: {name} {qname(p)} (range {', '.join(qname(r) for r in rngs)}; object {', '.join(sorted(qname(c) for c in o_classes))})")

    REPORTS.mkdir(exist_ok=True)
    merged.serialize(destination=args.out, format="turtle")
    print(f"proposal: {len(replaced)} replaced, {len(added)} added, {len(removed)} removed triples maps; "
          f"merged mapping: {len(m_tms)} triples maps -> {args.out}")
    for c in sorted(set(conflicts)):
        (errors if args.strict else warnings).append(c)
    for w in warnings:
        print("WARN: ", w)
    for e in errors:
        print("ERROR:", e)
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
