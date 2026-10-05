# AIDOC-AP Lifecycle Extension: tooling entry points.
PY ?= $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)
MODULE := ontology/aidoc-lc.ttl

.PHONY: setup check check-strict oci-core oci oci-gate cq gap test lint-text merged alignments all release-check fetch-core fetch-engine fetch-engine-excerpt

setup:
	python3 -m venv .venv
	.venv/bin/pip install --quiet --upgrade pip
	.venv/bin/pip install --quiet -r requirements.txt
	@[ -f vendor/aidoc-ap/aidoc-ap.ttl ] || PY="$(CURDIR)/.venv/bin/python" bash scripts/fetch_core.sh
	@[ -f vendor/engine/ontop/input/aidoc-ap_r2rml.ttl ] || echo "note: vendor/engine is missing; run 'make fetch-engine-excerpt' before 'make gap' or Phase 1"
	@echo "venv ready: .venv"

check:
	$(PY) scripts/check_module.py --module $(MODULE)

check-strict:
	$(PY) scripts/check_module.py --module $(MODULE) --strict

reports:
	mkdir -p reports

oci-core: | reports
	$(PY) scripts/oci.py --label "AIDOC-AP core v1.2" --md reports/oci_core.md --json reports/oci_core.json

oci: | reports
	$(PY) scripts/oci.py --module $(MODULE) --label "framework (core + Lifecycle Extension)" --md reports/oci_framework.md --json reports/oci_framework.json

oci-gate: | reports
	$(PY) scripts/oci.py --module $(MODULE) --label "framework (core + Lifecycle Extension)" --md reports/oci_framework.md --json reports/oci_framework.json --min 0.90

cq: | reports
	$(PY) scripts/run_cqs.py

gap:
	$(PY) scripts/r2rml_gap.py --engine vendor/engine --out docs/05_t54_gap_analysis.md

test:
	$(PY) -m pytest -q tests

alignments:
	$(PY) scripts/alignments.py

lint-text:
	$(PY) scripts/style.py $(wildcard docs/*.md deliverable/*.md)

merged: | reports
	$(PY) scripts/merge.py --out reports/framework_merged.ttl

all: check test oci-core oci cq

release-check: check-strict test oci-gate cq

fetch-core:
	bash scripts/fetch_core.sh

fetch-engine:
	bash scripts/fetch_engine.sh

fetch-engine-excerpt:
	ENGINE_EXCERPT=1 bash scripts/fetch_engine.sh
