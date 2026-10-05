"""Regression tests for the measurement and check tooling (run: make test).

These tests protect the method, not the module content: the core baseline must stay
at the published value, the criteria must react to the patterns they are meant to
count, and the module checker must reject axioms about core terms.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from common import CORE_TTL, PROFILE, load_graph, verify_lock  # noqa: E402
from oci import evaluate  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
PROFILE_DATA = json.loads(PROFILE.read_text())


def test_vendored_core_matches_lock():
    assert verify_lock() == []


def test_core_baseline_is_0_574():
    res = evaluate(load_graph([CORE_TTL]), PROFILE_DATA)
    assert res["oci"] == 0.5741
    assert res["stages_at_zero"] == []
    gaps = {r["id"] for r in res["stages"] if r["coverage"] < 1}
    assert gaps == {"D1", "D2", "D5", "M1", "M2", "M3", "M4", "S1", "S2", "S3", "S4", "O2", "O3", "O4"}


def test_fixture_module_reaches_full_coverage_and_union_domains_count():
    res = evaluate(load_graph([CORE_TTL, FIX / "full_module.ttl"]), PROFILE_DATA)
    assert res["oci"] == 1.0
    o2 = next(r for r in res["stages"] if r["id"] == "O2")
    assert any("fxConcernsSystem" in e for e in o2["evidence_c2"])
    assert "aidoc-lc:fxConcernsSystem" in o2["evidence_c3"]


def run_checker(module):
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "check_module.py"), "--module", str(module)],
                          capture_output=True, text=True)


def test_checker_accepts_skeleton():
    r = run_checker(ROOT / "ontology" / "aidoc-lc.ttl")
    assert r.returncode == 0, r.stdout + r.stderr


def test_checker_rejects_rule_violations():
    r = run_checker(FIX / "bad_module.ttl")
    assert r.returncode == 1
    assert "non-module term aidoc:ModelPackaging" in r.stdout
    assert "needs exactly one rdfs:label@en" in r.stdout
    assert "not declared in module, core or reference ontologies" in r.stdout
    assert "property names use lowerCamelCase" in r.stdout
