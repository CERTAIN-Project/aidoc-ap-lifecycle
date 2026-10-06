#!/usr/bin/env python3
"""End-to-end test of both engine paths on the same database rows (needs Docker).

1. Creates the engine schema in PostgreSQL 13 from data_api/app/models.py and loads
   mappings/r2rml/e2e/pilot_rows.json.
2. Materialises with Ontop 5.5.0 (a) the engine's own mapping and ontology, as the engine
   publishes it today, and (b) the engine mapping merged with the overlay, with core and module.
3. Runs the adapter on (a), and the competency queries over the adapted (a) and over (b).
With --engine-fix DIR it also materialises the mapping and ontology of an engine checkout with
fixes (DIR/ontop/input), and with --core-cqs DIR it runs the core's competency queries
(*.sparql) over the engine output and over the fixed engine output, as a regression test.
Outputs in reports/e2e/. Containers and the Docker network are removed at the end.

  python3 scripts/engine_e2e.py [--engine-fix DIR] [--core-cqs DIR]
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import shutil
import subprocess
import sys
import time

from common import REPORTS, ROOT

ENGINE = ROOT / "vendor" / "engine"
ROWS = ROOT / "mappings" / "r2rml" / "e2e" / "pilot_rows.json"
OUT = REPORTS / "e2e"
NET, DB, VOL = "lc-e2e", "lc-e2e-db", "lc-e2e-jdbc"
JDBC = "postgresql-42.7.10.jar"
SQL_TYPES = {"String": "text", "Text": "text", "Numeric": "numeric", "Integer": "integer", "BigInteger": "bigint",
             "Float": "double precision", "Boolean": "boolean", "JSON": "json", "DateTime": "timestamp"}


def sh(cmd: list, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, capture_output=True, **kw)


def ident(name: str) -> str:
    return f'"{name}"' if name != name.lower() else name


def schema_sql() -> str:
    """CREATE TABLE statements from the SQLAlchemy models (types only, no keys)."""
    out = []
    for node in ast.parse((ENGINE / "data_api" / "app" / "models.py").read_text()).body:
        if not isinstance(node, ast.ClassDef):
            continue
        table, cols = None, []
        for st in node.body:
            tgt = st.targets[0] if isinstance(st, ast.Assign) else getattr(st, "target", None)
            val = getattr(st, "value", None)
            if isinstance(tgt, ast.Name) and tgt.id == "__tablename__" and isinstance(val, ast.Constant):
                table = val.value
            elif isinstance(tgt, ast.Name) and isinstance(val, ast.Call) and \
                    (getattr(val.func, "id", None) or getattr(val.func, "attr", None)) in ("Column", "mapped_column"):
                typ = "text"
                for a in val.args:
                    name = getattr(a, "id", None) or getattr(getattr(a, "func", None), "id", None) \
                        or getattr(getattr(a, "func", None), "attr", None)
                    if name == "ARRAY":
                        inner = getattr(a.args[0], "id", None) or getattr(getattr(a.args[0], "func", None), "id", "String")
                        typ = SQL_TYPES.get(inner, "text") + "[]"
                        break
                    if name in SQL_TYPES:
                        typ = SQL_TYPES[name]
                        break
                cols.append(f"{ident(tgt.id)} {typ}")
        if table:
            out.append(f"CREATE TABLE {table} ({', '.join(cols)});")
    return "\n".join(out) + "\n"


def literal(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, list):
        return "ARRAY[" + ", ".join(literal(x) for x in v) + "]::text[]"
    return "'" + str(v).replace("'", "''") + "'"


def rows_sql() -> str:
    data = json.loads(ROWS.read_text())
    out = []
    for table, rows in data.items():
        if table.startswith("_"):
            continue
        for r in rows:
            out.append(f"INSERT INTO {table} ({', '.join(ident(c) for c in r)}) VALUES ({', '.join(literal(v) for v in r.values())});")
    return "\n".join(out) + "\n"


def cleanup():
    sh(["docker", "rm", "-f", DB])
    sh(["docker", "network", "rm", NET])


def core_cq_rows(graph_file: pathlib.Path, cq_dir: pathlib.Path) -> dict:
    from rdflib import Graph
    g = Graph().parse(graph_file)
    out = {}
    for f in sorted(cq_dir.glob("*.sparql")):
        try:
            out[f.name.split("-")[0]] = len(list(g.query(f.read_text(encoding="utf-8"))))
        except Exception:  # noqa: BLE001
            out[f.name.split("-")[0]] = -1
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine-fix", help="engine checkout with fixes; its ontop/input is materialised as 'engine-fix'")
    ap.add_argument("--core-cqs", help="directory with the core's competency queries (*.sparql)")
    args = ap.parse_args()
    if sh(["docker", "info"]).returncode != 0:
        print("ERROR: Docker is not running")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "schema.sql").write_text(schema_sql())
    (OUT / "rows.sql").write_text(rows_sql())
    cleanup()
    try:
        sh(["docker", "network", "create", NET])
        r = sh(["docker", "run", "-d", "--name", DB, "--network", NET, "-e", "POSTGRES_PASSWORD=e2e",
                "-e", "POSTGRES_DB=certain_db", "postgres:13"])
        if r.returncode:
            print(r.stderr)
            return 1
        for _ in range(60):
            if sh(["docker", "exec", DB, "pg_isready", "-U", "postgres", "-d", "certain_db"]).returncode == 0:
                break
            time.sleep(1)
        time.sleep(2)
        for f in ("schema.sql", "rows.sql"):
            r = sh(["docker", "exec", "-i", DB, "psql", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", "certain_db", "-q"],
                   input=(OUT / f).read_text())
            if r.returncode:
                print(f"ERROR loading {f}:", r.stderr)
                return 1
        sh(["docker", "volume", "create", VOL])
        r = sh(["docker", "run", "--rm", "-v", f"{VOL}:/jdbc", "--user", "root", "curlimages/curl:latest", "sh", "-c",
                f"[ -f /jdbc/{JDBC} ] || curl -sL -o /jdbc/{JDBC} https://jdbc.postgresql.org/download/{JDBC}"])
        if r.returncode:
            print(r.stderr)
            return 1

        inp = OUT / "ontop"
        inp.mkdir(exist_ok=True)
        (inp / "e2e.properties").write_text(f"jdbc.url=jdbc:postgresql://{DB}:5432/certain_db\njdbc.driver=org.postgresql.Driver\n"
                                            "jdbc.user=postgres\njdbc.password=e2e\n")
        # The engine mapping reads the json column data_signatures.signature directly; PostgreSQL json
        # has no equality operator, so materialisation fails. Test copy only: cast it to text.
        em = (ENGINE / "ontop" / "input" / "aidoc-ap_r2rml.ttl").read_text()
        old = 'rr:logicalTable [ rr:tableName "data_signatures" ] ;'
        assert em.count(old) == 1
        em = em.replace(old, 'rr:logicalTable [ rr:sqlQuery "SELECT run_id, data_id, CAST(signature AS text) AS signature '
                             'FROM data_signatures" ] ;')
        (inp / "engine_mapping.ttl").write_text(em)
        shutil.copy(ENGINE / "ontop" / "input" / "aidoc-ap.ttl", inp / "engine_ontology.ttl")
        shutil.copy(REPORTS / "aidoc-ap_r2rml_merged.ttl", inp / "overlay_mapping.ttl")
        shutil.copy(REPORTS / "framework_merged.ttl", inp / "framework.ttl")
        runs = [("engine", "engine_mapping.ttl", "engine_ontology.ttl"), ("overlay", "overlay_mapping.ttl", "framework.ttl")]
        if args.engine_fix:
            fix_in = pathlib.Path(args.engine_fix) / "ontop" / "input"
            shutil.copy(fix_in / "aidoc-ap_r2rml.ttl", inp / "enginefix_mapping.ttl")
            shutil.copy(fix_in / "aidoc-ap.ttl", inp / "enginefix_ontology.ttl")
            runs.append(("engine-fix", "enginefix_mapping.ttl", "enginefix_ontology.ttl"))
        status = 0
        for label, mapping, onto in runs:
            r = sh(["docker", "run", "--rm", "--network", NET, "-v", f"{inp}:/in", "-v", f"{VOL}:/opt/ontop/jdbc",
                    "ontop/ontop:5.5.0", "/opt/ontop/ontop", "materialize",
                    "--mapping", f"/in/{mapping}", "--ontology", f"/in/{onto}", "--properties", "/in/e2e.properties",
                    "--format", "turtle", "--output", f"/in/{label}_output.ttl"])
            (OUT / f"ontop_{label}.log").write_text(r.stdout + r.stderr)
            print(f"ontop materialize ({label}): exit {r.returncode}")
            if r.returncode:
                print((r.stdout + r.stderr)[-3000:])
                status = 1
        if status:
            return status
    finally:
        cleanup()

    # Path (a): adapter over the engine output; path (b): overlay output. Competency queries over both.
    py = sys.executable
    steps = [
        [py, "scripts/adapt_engine_graph.py", "--input", str(OUT / "ontop" / "engine_output.ttl"),
         "--out", str(OUT / "adapter_output.ttl"), "--report", str(OUT / "adapter_report.md")],
        [py, "scripts/run_cqs.py", "--data", str(OUT / "adapter_output.ttl"), "--md", str(OUT / "cq_adapter.md")],
        [py, "scripts/run_cqs.py", "--data", str(OUT / "ontop" / "overlay_output.ttl"), "--md", str(OUT / "cq_overlay.md")],
    ]
    for cmd in steps:
        r = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
        if r.returncode:
            print(r.stdout + r.stderr)
            return 1
    rows = {}
    for label in ("adapter", "overlay"):
        for line in (OUT / f"cq_{label}.md").read_text().splitlines():
            parts = [c.strip() for c in line.strip("|").split("|")]
            if len(parts) == 4 and parts[0].endswith(".rq"):
                rows.setdefault(parts[0], {"stage": parts[1]})[label] = parts[3]
    lines = ["# End-to-end test of the engine paths", "",
             "Same database rows (mappings/r2rml/e2e/pilot_rows.json) in PostgreSQL 13, materialised with Ontop 5.5.0.", "",
             "| Competency query | Stage | (a) adapter over engine output | (b) R2RML overlay |", "|---|---|---|---|"]
    for f, v in sorted(rows.items()):
        lines.append(f"| {f} | {v['stage']} | {v.get('adapter', '-')} | {v.get('overlay', '-')} |")
    answered = {k: sum(1 for v in rows.values() if v.get(k, "0") not in ("0", "error")) for k in ("adapter", "overlay")}
    lines += ["", f"Answered: adapter {answered['adapter']} of {len(rows)}, overlay {answered['overlay']} of {len(rows)}.", ""]
    if args.engine_fix:
        sys.path.insert(0, str(ROOT / "scripts"))
        from adapt_engine_graph import metrics
        from common import CORE_TTL, MODULE_TTL, load_graph, reference_graph
        from rdflib import Graph
        kb = load_graph([CORE_TTL, MODULE_TTL]) + reference_graph()
        lines += ["## Engine fix branch", "", "| Measure | Engine | Engine with fixes |", "|---|---|---|"]
        m = {k: metrics(Graph().parse(OUT / "ontop" / f"{k}_output.ttl"), kb) for k in ("engine", "engine-fix")}
        for key, label in (("triples", "Triples"), ("activity_and_entity", "Nodes typed prov:Activity and prov:Entity")):
            lines.append(f"| {label} | {m['engine'][key]} | {m['engine-fix'][key]} |")
        for key, label in (("undeclared", "Triples with undeclared predicates"), ("domain_violations", "Domain violations")):
            lines.append(f"| {label} | {sum(m['engine'][key].values())} | {sum(m['engine-fix'][key].values())} |")
        lines.append("")
        if args.core_cqs:
            base = core_cq_rows(OUT / "ontop" / "engine_output.ttl", pathlib.Path(args.core_cqs))
            fix = core_cq_rows(OUT / "ontop" / "engine-fix_output.ttl", pathlib.Path(args.core_cqs))
            ans = lambda d: sum(1 for v in d.values() if v > 0)
            lines += [f"Core competency queries answered (rows > 0): engine {ans(base)} of {len(base)}, "
                      f"engine with fixes {ans(fix)} of {len(fix)}.", ""]
            changed = [f"{k}: {base[k]} -> {fix[k]}" for k in base if (base[k] > 0) != (fix.get(k, 0) > 0) or base[k] < 0 or fix.get(k, 0) < 0]
            lines += ["Queries whose answered status changed: " + (", ".join(changed) if changed else "none"), ""]
    (OUT / "summary.md").write_text("\n".join(lines))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
