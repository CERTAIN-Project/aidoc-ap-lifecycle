#!/usr/bin/env python3
"""Compute the Ontology Coverage Index (OCI, CERTAIN KPI 1.1).

The index is computed over the ontology framework: the vendored AIDOC-AP core plus
any module passed with --module. The reference lifecycle model and the framework
settings come from method/stage_profile.json; the three criteria are the SPARQL
queries in method/queries/ (C1 concept, C2 traceability, C3 description).

  python3 scripts/oci.py                                   # core only
  python3 scripts/oci.py --module ontology/aidoc-lc.ttl    # core + Lifecycle Extension
  python3 scripts/oci.py --module ontology/aidoc-lc.ttl --min 0.90 --md reports/oci.md --json reports/oci.json

Exit code 1 if --min is given and the index is below it or a stage scores zero.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

import pathlib

from common import CORE_TTL, PROFILE, QUERY_DIR, ROOT, load_graph, qname, verify_lock


def rel(path: str) -> str:
    p = pathlib.Path(path).resolve()
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(path)

CRITERIA = ("C1", "C2", "C3")


def fill(template: str, classes, profile) -> str:
    ns_filter = " || ".join(f'STRSTARTS(STR(?property), "{ns}")' for ns in profile["framework_namespaces"])
    return (template
            .replace("{{CLASSES}}", " ".join(f"<{c}>" for c in classes))
            .replace("{{ANCHOR}}", f"<{profile['anchor_activity']}>")
            .replace("{{ARTEFACT_ROOTS}}", " ".join(f"<{r}>" for r in profile["artefact_roots"]))
            .replace("{{NS_FILTER}}", ns_filter))


def evaluate(graph, profile) -> dict:
    q = {name: (QUERY_DIR / f"{name}.rq").read_text()
         for name in ("c1_concept", "c2_traceability", "c3_description")}
    phases = {p["id"]: p["label"] for p in profile["phases"]}
    rows = []
    for st in profile["stages"]:
        classes = st["classes"]
        c1_hits = {str(r["class"]) for r in graph.query(fill(q["c1_concept"], classes, profile))}
        c2_hits = sorted({(qname(r["property"]), qname(r["range"])) for r in graph.query(fill(q["c2_traceability"], classes, profile))})
        c3_hits = sorted({qname(r["property"]) for r in graph.query(fill(q["c3_description"], classes, profile))})
        crit = {"C1": c1_hits == set(classes), "C2": bool(c2_hits), "C3": bool(c3_hits)}
        rows.append({
            "id": st["id"], "phase": phases[st["phase"]], "stage": st["label"],
            "classes": [qname(c) for c in classes],
            **crit,
            "coverage": round(sum(crit.values()) / len(CRITERIA), 4),
            "missing_classes": [qname(c) for c in classes if c not in c1_hits],
            "evidence_c2": [f"{p} -> {r}" for p, r in c2_hits],
            "evidence_c3": c3_hits,
        })
    per_phase = {}
    for label in phases.values():
        vals = [r["coverage"] for r in rows if r["phase"] == label]
        per_phase[label] = round(sum(vals) / len(vals), 4) if vals else None
    oci = round(sum(r["coverage"] for r in rows) / len(rows), 4)
    return {"oci": oci, "per_phase": per_phase, "min_stage": min(r["coverage"] for r in rows),
            "stages_at_zero": [r["id"] for r in rows if r["coverage"] == 0], "stages": rows}


def to_markdown(res: dict, label: str, inputs) -> str:
    tick = lambda b: "yes" if b else "no"
    out = [f"# Ontology Coverage Index: {label}", "",
           f"Computed {date.today().isoformat()} over: " + ", ".join(f"`{i}`" for i in inputs), "",
           f"**OCI = {res['oci']:.3f}** (target 0.90, stages at zero: {', '.join(res['stages_at_zero']) or 'none'})", "",
           "| Phase | Mean coverage |", "|---|---|"]
    out += [f"| {k} | {v:.3f} |" for k, v in res["per_phase"].items()]
    out += ["", "| ID | Stage | Class(es) | C1 | C2 | C3 | Coverage | Evidence C2 | Evidence C3 |",
            "|---|---|---|---|---|---|---|---|---|"]
    for r in res["stages"]:
        out.append(f"| {r['id']} | {r['stage']} | {', '.join(r['classes'])} | {tick(r['C1'])} | {tick(r['C2'])} | "
                   f"{tick(r['C3'])} | {r['coverage']:.2f} | {'; '.join(r['evidence_c2']) or '-'} | "
                   f"{'; '.join(r['evidence_c3']) or '-'} |")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--core", default=str(CORE_TTL), help="core ontology (default: vendored AIDOC-AP)")
    ap.add_argument("--module", action="append", default=[], help="module file(s) to add to the framework")
    ap.add_argument("--profile", default=str(PROFILE))
    ap.add_argument("--label", default=None, help="label for the report heading")
    ap.add_argument("--md", help="write a Markdown report")
    ap.add_argument("--json", help="write a JSON report")
    ap.add_argument("--min", type=float, help="fail if OCI is below this value or a stage scores zero")
    args = ap.parse_args()

    problems = verify_lock()
    if problems and args.core == str(CORE_TTL):
        for p in problems:
            print("ERROR:", p)
        return 1

    profile = json.loads(open(args.profile).read())
    inputs = [rel(p) for p in (args.core, *args.module)]
    res = evaluate(load_graph([args.core, *args.module]), profile)
    label = args.label or ("framework (core + modules)" if args.module else "AIDOC-AP core")

    print(f"OCI [{label}] = {res['oci']:.3f}")
    for k, v in res["per_phase"].items():
        print(f"  {k:<15} {v:.3f}")
    for r in res["stages"]:
        if r["coverage"] < 1:
            missing = [c for c in ("C1", "C2", "C3") if not r[c]]
            print(f"  gap {r['id']:<3} {r['stage']:<48} {r['coverage']:.2f}  missing {', '.join(missing)}")

    if args.md:
        open(args.md, "w").write(to_markdown(res, label, inputs))
    if args.json:
        open(args.json, "w").write(json.dumps({"label": label, "inputs": inputs, **res}, indent=2) + "\n")

    if args.min is not None and (res["oci"] < args.min or res["stages_at_zero"]):
        print(f"FAIL: OCI {res['oci']:.3f} < {args.min} or stages at zero {res['stages_at_zero']}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
