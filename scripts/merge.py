#!/usr/bin/env python3
"""Merge the vendored core and the module into one Turtle file without owl:imports,
for reasoners and documentation tools that should not resolve imports over the network.

  python3 scripts/merge.py --out reports/framework_merged.ttl
"""
import argparse
import sys

from rdflib import OWL

from common import CORE_TTL, MODULE_TTL, PREFIXES, load_graph


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--module", default=str(MODULE_TTL))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    g = load_graph([CORE_TTL, args.module])
    g.remove((None, OWL.imports, None))
    for prefix, ns in PREFIXES.items():
        g.bind(prefix, ns, override=True)
    g.serialize(destination=args.out, format="turtle")
    print(f"wrote {args.out} ({len(g)} triples)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
