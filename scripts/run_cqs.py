#!/usr/bin/env python3
"""Run the competency queries in cq/ over core + module + examples/*.ttl.

Each query file starts with a header:
  # CQ: Which hyperparameter settings did the training activity that produced model M use?
  # Stage: M1
  # Terms: aidoc-lc:hasHyperParameterSetting
A query that does not parse is an error. A query without rows over the example graphs
is reported, so that every term is shown to be usable on realistic data.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

from common import CORE_TTL, CQ_DIR, EXAMPLES_DIR, MODULE_TTL, REPORTS, load_graph


def header(text: str) -> dict:
    out = {}
    for key in ("CQ", "Stage", "Terms"):
        m = re.search(rf"^#\s*{key}:\s*(.+)$", text, re.M)
        out[key] = m.group(1).strip() if m else ""
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--md", default=str(REPORTS / "cq.md"))
    ap.add_argument("--data", nargs="*", help="instance graphs to query instead of examples/*.ttl")
    args = ap.parse_args()

    files = sorted(CQ_DIR.glob("*.rq"))
    examples = [pathlib.Path(d) for d in args.data] if args.data else sorted(EXAMPLES_DIR.glob("*.ttl"))
    g = load_graph([CORE_TTL, MODULE_TTL, *examples])
    errors, lines = 0, ["| File | Stage | CQ | Rows |", "|---|---|---|---|"]
    for f in files:
        text = f.read_text(encoding="utf-8")
        h = header(text)
        if not h["CQ"] or not h["Stage"]:
            print(f"WARN:  {f.name}: header needs '# CQ:' and '# Stage:' lines")
        try:
            n = len(list(g.query(text)))
        except Exception as exc:  # noqa: BLE001
            errors += 1
            print(f"ERROR: {f.name}: {exc}")
            lines.append(f"| {f.name} | {h['Stage']} | {h['CQ']} | error |")
            continue
        if n == 0 and examples:
            print(f"WARN:  {f.name}: no rows over {'the given graphs' if args.data else 'examples/'} (add data or check the query)")
        lines.append(f"| {f.name} | {h['Stage']} | {h['CQ']} | {n} |")
        print(f"{f.name:<40} {h['Stage']:<4} rows={n}")
    REPORTS.mkdir(exist_ok=True)
    open(args.md, "w").write("# Competency queries\n\n" + "\n".join(lines) + "\n")
    print(f"{len(files)} query file(s), {len(examples)} example graph(s), {errors} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
