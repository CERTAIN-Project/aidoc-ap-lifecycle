#!/usr/bin/env python3
"""Gap analysis: what the Semantic MLOps Engine (T5.4) captures vs. what the R2RML mappings
express in the ontology framework.

For every engine table (data_api/app/models.py) and column, the script reports whether the
column is mapped to an ontology term with specific meaning, mapped only through generic
predicates (rdfs:comment, prov:wasInfluencedBy, dct:format, ...), or not mapped at all.
It also lists terms that the mappings use but that are declared nowhere (core, reference
ontologies, module), and domain conflicts: predicates applied to subjects whose mapped class
is not below the predicate's declared rdfs:domain (RDFS entailment would then give the
subject the domain class as an additional type).

  python3 scripts/r2rml_gap.py --engine vendor/engine --out docs/05_t54_gap_analysis.md
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date

from rdflib import BNode, Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from common import CORE_TTL, MODULE_TTL, ROOT, load_graph, qname, reference_graph

RR = Namespace("http://www.w3.org/ns/r2rml#")
GENERIC = {
    "http://www.w3.org/ns/prov#wasInfluencedBy", "http://www.w3.org/2000/01/rdf-schema#comment",
    "http://www.w3.org/2000/01/rdf-schema#label", "http://purl.org/dc/terms/description",
    "http://purl.org/dc/terms/type", "http://purl.org/dc/terms/format",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#value", "https://schema.org/keywords",
    "https://schema.org/status", "https://schema.org/url",
}
STANDARD_NS = ("http://www.w3.org/1999/02/22-rdf-syntax-ns#", "http://www.w3.org/2000/01/rdf-schema#",
               "http://purl.org/dc/terms/", "https://schema.org/", "http://xmlns.com/foaf/0.1/",
               "http://www.w3.org/2002/07/owl#")
# engine table -> reference lifecycle stage(s) of method/stage_profile.json (orientation only)
STAGE_HINT = {
    "data": "D1, D6", "data_techniques": "D3, D5", "data_hyperparameters": "D5", "data_metrics": "D2",
    "data_signatures": "D2", "data_resources": "D (resources)", "tokenizer_config": "D5", "tokenization_stats": "D5",
    "labeling_procedures": "D4", "experiments": "M1", "runs": "M1", "runs_tags": "M1", "experiments_tags": "M1",
    "model_architecture": "M1", "model_hyperparameters": "M1", "checkpoints": "M1, M4", "resources": "M1 (resources)",
    "model_metrics": "M2", "last_model_metrics": "M2", "weight_distribution": "M2", "examples": "M2",
    "model_packaging": "M3", "model_deployed": "S3, M4", "runtime_environment": "S3, O3", "runs_code": "S1, S4",
    "change_logs": "S4", "build_and_integration_testing": "S2", "monitor_logs": "O1", "runs_logs": "O1",
    "drift_metrics": "O2", "decomissioning": "O4", "id_mapping": "(keys)",
    "risks": "legal module", "human_oversight_mechanisms": "documentation", "transparency_measures": "documentation",
    "explainable_ai_features": "documentation", "interfaces": "documentation", "standards": "documentation",
    "declaration_of_conformity": "documentation", "visual_documentation": "documentation", "ai_actors": "documentation",
}


def engine_tables(models_py: pathlib.Path) -> dict:
    tables = {}
    for node in ast.parse(models_py.read_text()).body:
        if not isinstance(node, ast.ClassDef):
            continue
        name, cols = None, []
        for st in node.body:
            tgt = st.targets[0] if isinstance(st, ast.Assign) else getattr(st, "target", None)
            val = getattr(st, "value", None)
            if isinstance(tgt, ast.Name) and tgt.id == "__tablename__" and isinstance(val, ast.Constant):
                name = val.value
            elif isinstance(tgt, ast.Name) and isinstance(val, ast.Call):
                fn = getattr(val.func, "id", None) or getattr(val.func, "attr", None)
                if fn in ("Column", "mapped_column"):
                    fk = any(isinstance(a, ast.Call) and (getattr(a.func, "id", None) or getattr(a.func, "attr", None)) == "ForeignKey"
                             for a in val.args)
                    cols.append((tgt.id, fk))
        if name:
            tables[name] = cols
    return tables


def _split_top(s: str, sep: str = ",") -> list:
    items, depth, cur = [], 0, ""
    for ch in s:
        depth += ch == "("
        depth -= ch == ")"
        if ch == sep and depth == 0:
            items.append(cur)
            cur = ""
        else:
            cur += ch
    items.append(cur)
    return items


def _lateral_values(sql: str) -> dict:
    """For 'CROSS JOIN LATERAL (VALUES ('k', t.col), ...) AS s(key, value)': value -> identifiers."""
    out = {}
    for body, cols in re.findall(r"LATERAL\s*\(\s*VALUES\s*(.*?)\)\s*AS\s*\w+\s*\(([^)]*)\)", sql, re.I | re.S):
        names = [c.strip() for c in cols.split(",")]
        for tup in re.findall(r"\(((?:[^()]|\([^()]*\))*)\)", body):
            for name, expr in zip(names, _split_top(tup)):
                out.setdefault(name, set()).update(re.findall(r"\b[A-Za-z_]\w*\.\"?(\w+)\"?", expr))
    return out


def select_aliases(sql: str) -> dict:
    """Map each output column of the query to the identifiers used in its expression, over all
    top-level UNION branches. Columns produced by a LATERAL VALUES list are traced to the
    columns used in the list."""
    lateral = _lateral_values(sql)
    out = {}
    for branch in re.split(r"\bUNION(?:\s+ALL)?\b", sql, flags=re.I):
        m = re.search(r"\bSELECT\b(.*?)\bFROM\b", branch, re.I | re.S)
        if not m:
            continue
        for item in _split_top(m.group(1)):
            item = item.strip()
            am = re.search(r"\bAS\s+\"?(\w+)\"?\s*$", item, re.I)
            if am:
                expr = item[: am.start()]
                out.setdefault(am.group(1), set()).update(re.findall(r"\b([A-Za-z_]\w*)\b", expr))
            else:
                qm = re.fullmatch(r"(?:\w+\.)?\"?(\w+)\"?", item)
                if qm and qm.group(1) in lateral:
                    out.setdefault(qm.group(1), set()).update(lateral[qm.group(1)])
    return out


def mapping_usage(r2rml: Graph, tables: dict):
    used = defaultdict(lambda: defaultdict(set))  # table -> column -> predicates
    classes = defaultdict(set)
    terms = set()
    for tm in set(r2rml.subjects(RR.logicalTable, None)):
        lt = r2rml.value(tm, RR.logicalTable)
        tname, sql = r2rml.value(lt, RR.tableName), r2rml.value(lt, RR.sqlQuery)
        tabs, alias = set(), {}
        if tname:
            tabs.add(str(tname).strip('"'))
        if sql:
            sql = str(sql)
            tabs |= {t.strip('"') for t in re.findall(r'(?:FROM|JOIN)\s+"?(\w+)"?', sql, re.I)}
            alias = select_aliases(sql)
        tabs = {t for t in tabs if t in tables}
        sm = r2rml.value(tm, RR.subjectMap)
        for c in r2rml.objects(sm, RR["class"]):
            terms.add(c)
            for t in tabs:
                classes[t].add(qname(c))
        for pom in r2rml.objects(tm, RR.predicateObjectMap):
            preds = list(r2rml.objects(pom, RR.predicate))
            terms |= set(preds)
            for om in r2rml.objects(pom, RR.objectMap):
                cols = set()
                if r2rml.value(om, RR.column):
                    cols.add(str(r2rml.value(om, RR.column)).strip('"'))
                if r2rml.value(om, RR.template):
                    cols |= set(re.findall(r"\{\"?(\w+)\"?\}", str(r2rml.value(om, RR.template))))
                for col in cols:
                    for t in tabs:
                        names = {c for c, _ in tables[t]}
                        sources = {col} if col in names else alias.get(col, set()) & names
                        for src in sources:
                            used[t][src] |= {str(p) for p in preds}
    return used, classes, terms


def _domain_members(g: Graph, node) -> list:
    """Expand an owl:unionOf domain into its member classes."""
    if isinstance(node, BNode):
        lst = g.value(node, OWL.unionOf)
        if lst is not None:
            out = []
            while lst is not None and lst != RDF.nil:
                first = g.value(lst, RDF.first)
                if first is not None:
                    out.append(first)
                lst = g.value(lst, RDF.rest)
            return out
    return [node]


def _superclasses(g: Graph, cls: URIRef) -> set:
    seen, todo = {cls}, [cls]
    while todo:
        for s in g.objects(todo.pop(), RDFS.subClassOf):
            if isinstance(s, URIRef) and s not in seen:
                seen.add(s)
                todo.append(s)
    return seen


PROV_STARTING_POINT = {URIRef("http://www.w3.org/ns/prov#" + c) for c in ("Activity", "Agent", "Entity")}


def domain_conflicts(r2rml: Graph, kb: Graph) -> list:
    """Predicates whose declared rdfs:domain (in core, module or reference ontologies) does not
    cover any rr:class of the subject map. Triples maps without rr:class are not checked, nor are
    generic PROV-O relations whose domain is the union of prov:Activity, prov:Agent and prov:Entity."""
    rows = set()
    for tm in set(r2rml.subjects(RR.subjectMap, None)):
        sm = r2rml.value(tm, RR.subjectMap)
        classes = [c for c in r2rml.objects(sm, RR["class"]) if isinstance(c, URIRef)]
        if not classes:
            continue
        supers = set().union(*(_superclasses(kb, c) for c in classes))
        for pom in r2rml.objects(tm, RR.predicateObjectMap):
            for p in r2rml.objects(pom, RR.predicate):
                doms = [m for d in kb.objects(p, RDFS.domain) for m in _domain_members(kb, d) if isinstance(m, URIRef)]
                if PROV_STARTING_POINT <= set(doms):
                    continue
                if doms and not set(doms) & supers:
                    rows.add((str(tm).rsplit("#", 1)[-1], qname(p), ", ".join(sorted(qname(d) for d in doms)),
                              ", ".join(sorted(qname(c) for c in classes))))
    return sorted(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", default=str(ROOT / "vendor" / "engine"))
    ap.add_argument("--module", default=str(MODULE_TTL))
    ap.add_argument("--mapping", default=None, help="R2RML file to analyse (default: the engine's ontop/input/aidoc-ap_r2rml.ttl)")
    ap.add_argument("--out", default=None, help="Markdown output (default: stdout)")
    args = ap.parse_args()
    eng = pathlib.Path(args.engine)
    models = eng / "data_api" / "app" / "models.py"
    r2rml_path = pathlib.Path(args.mapping) if args.mapping else eng / "ontop" / "input" / "aidoc-ap_r2rml.ttl"
    mapping_label = r2rml_path.name if args.mapping else "ontop/input/aidoc-ap_r2rml.ttl"
    if not models.exists() or not r2rml_path.exists():
        print(f"ERROR: engine files not found under {eng}; run scripts/fetch_engine.sh")
        return 1
    ref = (eng / "ENGINE_REF").read_text().strip() if (eng / "ENGINE_REF").exists() else \
        subprocess.run(["git", "-C", str(eng), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()

    tables = engine_tables(models)
    r2rml = Graph().parse(str(r2rml_path))
    used, classes, terms = mapping_usage(r2rml, tables)
    framework = load_graph([CORE_TTL] + ([args.module] if pathlib.Path(args.module).exists() else []))
    refs = reference_graph()
    undefined = sorted(qname(t) for t in terms if isinstance(t, URIRef) and not str(t).startswith(STANDARD_NS)
                       and (t, None, None) not in framework and (t, None, None) not in refs)
    conflicts = domain_conflicts(r2rml, framework + refs)

    counts = defaultdict(int)
    rows = []
    for t, cols in tables.items():
        for col, fk in cols:
            if fk or col.endswith("_id") or col in ("run_id", "experiment_id"):
                status = "key"
            elif col not in used.get(t, {}):
                status = "unmapped"
            elif used[t][col] <= GENERIC:
                status = "generic only"
            else:
                status = "mapped"
            counts[status] += 1
            if status in ("unmapped", "generic only"):
                preds = ", ".join(sorted(qname(p) for p in used.get(t, {}).get(col, set()))) or "-"
                rows.append((STAGE_HINT.get(t, "?"), t, col, status, preds))

    out = [
        "# T5.4 gap analysis: Semantic MLOps Engine vs. ontology framework", "",
        f"Generated {date.today().isoformat()} by `scripts/r2rml_gap.py` from the engine at `{ref[:12]}` "
        f"(`data_api/app/models.py`, `{mapping_label}`). Re-run with `make gap`.", "",
        f"Columns: {counts['mapped']} mapped with specific terms, {counts['generic only']} mapped only through "
        f"generic predicates, {counts['unmapped']} not mapped, {counts['key']} keys.", "",
        "Generic predicates: " + ", ".join(sorted(qname(p) for p in GENERIC)) + ".", "",
        "## Terms used by the mappings but declared nowhere (core v1.2, reference ontologies, module)", "",
        *[f"- `{u}`" for u in undefined], "",
        "## Domain conflicts", "",
        "Predicates applied to subjects whose mapped class (rr:class) is not below the predicate's declared "
        "rdfs:domain in the core, the module or the reference ontologies. Under RDFS entailment the subject "
        "also becomes an instance of the domain class (for example, a data acquisition activity is inferred "
        "to be an aidoc:Dataset). Triples maps without rr:class are not checked, nor are generic PROV-O relations "
        "such as prov:wasInfluencedBy, whose domain covers every PROV class. Each row is either a mapping "
        "fix (map the value onto the resource the property is defined for) or evidence that a stage-level "
        "property is missing; decide per row in Phase 1 and record the outcome in Phase 5.", "",
        "| Triples map | Predicate | Declared domain | Mapped class(es) |", "|---|---|---|---|",
        *[f"| {tm} | {p} | {d} | {c} |" for tm, p, d, c in conflicts], "",
        "## Columns without a specific mapping, by lifecycle stage", "",
        "| Stage | Table | Column | Status | Current predicates |", "|---|---|---|---|---|",
        *[f"| {s} | {t} | {c} | {st} | {p} |" for s, t, c, st, p in sorted(rows)], "",
        "## Classes assigned per table", "",
        "| Table | Stage | Classes |", "|---|---|---|",
        *[f"| {t} | {STAGE_HINT.get(t, '?')} | {', '.join(sorted(classes.get(t, []))) or '-'} |" for t in tables], "",
    ]
    text = "\n".join(out)
    if args.out:
        open(args.out, "w").write(text)
        print(f"wrote {args.out}: {counts['unmapped']} unmapped, {counts['generic only']} generic-only, "
              f"{len(undefined)} undefined terms, {len(conflicts)} domain conflicts")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
