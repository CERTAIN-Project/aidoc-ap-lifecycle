"""Shared paths, namespaces and loaders for the AIDOC-AP Lifecycle Extension tooling."""
from __future__ import annotations

import hashlib
import json
import pathlib

from rdflib import Graph

ROOT = pathlib.Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "aidoc-ap"
LOCK = ROOT / "vendor" / "LOCK.json"
CORE_TTL = VENDOR / "aidoc-ap.ttl"
REF_DIR = VENDOR / "reference_ontologies"
MODULE_TTL = ROOT / "ontology" / "aidoc-lc.ttl"
PROFILE = ROOT / "method" / "stage_profile.json"
QUERY_DIR = ROOT / "method" / "queries"
CQ_DIR = ROOT / "cq"
EXAMPLES_DIR = ROOT / "examples"
GROUNDING_CSV = ROOT / "docs" / "grounding.csv"
REPORTS = ROOT / "reports"

CORE_NS = "https://w3id.org/aidoc-ap#"
CORE_ONTOLOGY_IRIS = {"https://w3id.org/aidoc-ap#", "https://w3id.org/aidoc-ap"}
LC_NS = "https://w3id.org/aidoc-ap/lifecycle#"
LC_PREFIX = "aidoc-lc"
LC_ONTOLOGY_IRIS = {"https://w3id.org/aidoc-ap/lifecycle#", "https://w3id.org/aidoc-ap/lifecycle"}

PREFIXES = {
    "aidoc": CORE_NS,
    LC_PREFIX: LC_NS,
    "prov": "http://www.w3.org/ns/prov#",
    "mls": "http://www.w3.org/ns/mls#",
    "dcat": "http://www.w3.org/ns/dcat#",
    "dqv": "http://www.w3.org/ns/dqv#",
    "dct": "http://purl.org/dc/terms/",
    "dpv": "https://w3id.org/dpv#",
    "dpv-ai": "https://w3id.org/dpv/ai#",
    "dpv-tech": "https://w3id.org/dpv/tech#",
    "dpv-aiact": "https://w3id.org/dpv/legal/eu/aiact#",
    "airo": "https://w3id.org/airo#",
    "vair": "https://w3id.org/vair#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "schema": "https://schema.org/",
}


def qname(iri: str) -> str:
    """Shorten an IRI with the known prefixes (longest namespace first)."""
    s = str(iri)
    for prefix, ns in sorted(PREFIXES.items(), key=lambda kv: -len(kv[1])):
        if s.startswith(ns):
            return f"{prefix}:{s[len(ns):]}"
    return f"<{s}>"


def load_graph(paths) -> Graph:
    g = Graph()
    for p in paths:
        g.parse(str(p), format="turtle")
    return g


def reference_graph() -> Graph:
    return load_graph(sorted(REF_DIR.glob("*.ttl")))


def vendor_digest() -> dict:
    # Hidden files (for example .DS_Store written by macOS Finder) are not part of the vendored core.
    return {
        str(p.relative_to(VENDOR)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(VENDOR.rglob("*"))
        if p.is_file() and not any(part.startswith(".") for part in p.relative_to(VENDOR).parts)
    }


def verify_lock() -> list[str]:
    """Return a list of problems; empty if vendor/ matches vendor/LOCK.json."""
    if not LOCK.exists():
        return ["vendor/LOCK.json is missing; run scripts/fetch_core.sh"]
    if not VENDOR.exists():
        return ["vendor/aidoc-ap/ is missing; run scripts/fetch_core.sh"]
    expected = json.loads(LOCK.read_text())["files"]
    actual = vendor_digest()
    problems = []
    for name, digest in expected.items():
        if name not in actual:
            problems.append(f"vendored core file missing: {name}")
        elif actual[name] != digest:
            problems.append(f"vendored core file changed: {name} (the core must not be modified)")
    for name in actual:
        if name not in expected:
            problems.append(f"unexpected file in vendor/aidoc-ap: {name}")
    return problems
