#!/usr/bin/env python3
"""Set the version of the module consistently in all release files. Publishes nothing.

Updates owl:versionInfo, owl:versionIRI and dcterms:modified in ontology/aidoc-lc.ttl, the
revision, version IRI and dates in documentation/config.properties, and the version in
CITATION.cff and .zenodo.json. With --release it also sets the release date (dcterms:issued,
dateIssued, date-released, publication_date), removes the draft note from the ontology header and
writes the snapshot versions/<version>/aidoc-lc.ttl that the documentation site serves under the
version IRI.

  python3 scripts/set_version.py --version 0.3
  python3 scripts/set_version.py --version 1.0 --release
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys

from common import MODULE_TTL, ROOT

CONFIG = ROOT / "documentation" / "config.properties"
CITATION = ROOT / "CITATION.cff"
ZENODO = ROOT / ".zenodo.json"


def sub(text: str, pattern: str, repl: str, path, count: int = 1) -> str:
    new, n = re.subn(pattern, repl, text, count=count, flags=re.M)
    if n == 0:
        raise SystemExit(f"ERROR: pattern {pattern!r} not found in {path}")
    return new


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", required=True, help="for example 0.3 or 1.0")
    ap.add_argument("--release", action="store_true", help="set the release date and write the version snapshot")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    args = ap.parse_args()
    if not re.fullmatch(r"\d+\.\d+", args.version):
        raise SystemExit("ERROR: version must look like 1.0")
    v, day = args.version, dt.date.fromisoformat(args.date)
    widoco_day = day.strftime("%d %b, %Y")

    t = MODULE_TTL.read_text(encoding="utf-8")
    t = sub(t, r'owl:versionIRI <https://w3id.org/aidoc-ap/lifecycle/[\d.]+>', f"owl:versionIRI <https://w3id.org/aidoc-ap/lifecycle/{v}>", MODULE_TTL)
    t = sub(t, r'owl:versionInfo "[\d.]+"', f'owl:versionInfo "{v}"', MODULE_TTL)
    t = sub(t, r'dcterms:modified "[\d-]+"\^\^xsd:date', f'dcterms:modified "{day}"^^xsd:date', MODULE_TTL)
    if args.release:
        t = re.sub(r'\s*dcterms:issued "[\d-]+"\^\^xsd:date ;', "", t)
        t = sub(t, r'(    dcterms:modified "[\d-]+"\^\^xsd:date ;)', rf'\1\n    dcterms:issued "{day}"^^xsd:date ;', MODULE_TTL)
        t = re.sub(r' ;\n    skos:note "Draft, not released."@en \.', " .", t)
    MODULE_TTL.write_text(t, encoding="utf-8")

    c = CONFIG.read_text(encoding="utf-8")
    c = sub(c, r"^ontologyRevisionNumber=.*$", f"ontologyRevisionNumber={v}", CONFIG)
    c = sub(c, r"^thisVersionURI=.*$", f"thisVersionURI=https://w3id.org/aidoc-ap/lifecycle/{v}", CONFIG)
    c = sub(c, r"^dateModified=.*$", f"dateModified={widoco_day}", CONFIG)
    if args.release:
        c = re.sub(r"^dateIssued=.*\n", "", c, flags=re.M)
        c = sub(c, r"^(dateModified=.*)$", rf"\1\ndateIssued={widoco_day}", CONFIG)
        c = sub(c, r"^status=.*$", "status=Ontology Specification", CONFIG)
    CONFIG.write_text(c, encoding="utf-8")

    cff = CITATION.read_text(encoding="utf-8")
    cff = sub(cff, r'^version: ".*"$', f'version: "{v}"', CITATION)
    if args.release:
        cff = re.sub(r"^date-released: .*\n", "", cff, flags=re.M)
        cff = sub(cff, r'^(version: ".*")$', rf"\1\ndate-released: {day}", CITATION)
    CITATION.write_text(cff, encoding="utf-8")

    z = json.loads(ZENODO.read_text(encoding="utf-8"))
    z["version"] = v
    if args.release:
        z["publication_date"] = day.isoformat()
    ZENODO.write_text(json.dumps(z, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.release:
        snap = ROOT / "versions" / v
        snap.mkdir(parents=True, exist_ok=True)
        shutil.copy(MODULE_TTL, snap / "aidoc-lc.ttl")
    print(f"version {v}{' released ' + str(day) if args.release else ''}: ontology, documentation/config.properties, "
          f"CITATION.cff, .zenodo.json{', versions/' + v + '/aidoc-lc.ttl' if args.release else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
