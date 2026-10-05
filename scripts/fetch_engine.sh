#!/usr/bin/env bash
# Fetch the Semantic MLOps Engine (T5.4) at a pinned commit into vendor/engine (read-only reference, not tracked).
#   scripts/fetch_engine.sh                      full repository at the pinned commit (about 360 MB, mostly pilot test data)
#   ENGINE_EXCERPT=1 scripts/fetch_engine.sh     excerpt only (about 9 MB): schema, R2RML mappings, materialised
#                                                pilot graph, logging library, lifecycle test scripts (paths below)
#   ENGINE_REF=main scripts/fetch_engine.sh      latest main (then re-run `make gap` and compare)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/vendor/engine"
REPO="https://github.com/CERTAIN-Project/Semantic_MLOps_engine.git"
REF="${ENGINE_REF:-b41ea271be92107fbd0375b8705db42a2681fcfe}"
EXCERPT_PATHS=(
  /README.md /LICENSE /LICENSE-CC-BY.TXT /pyproject.toml /requirements.txt /init_databases.sql
  /docker-compose.yml /Dockerfile
  /ontop/ /data_api/ /certain_library/ /tests/ /docs_api/
  /test_docker/__init__.py /test_docker/lifecycle/ /test_docker/model_retriever/
  /test_docker/test_full_lifecycle_pilot.py /test_docker/test_complete_workflow.py
  /test_docker/test_library_mlflow.py /test_docker/test_finance_pitol.py
)
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

git -C "$TMP" init --quiet engine
git -C "$TMP/engine" remote add origin "$REPO"
if [ "${ENGINE_EXCERPT:-0}" = "1" ]; then
  # partial clone: only the blobs of the excerpt paths are downloaded
  git -C "$TMP/engine" fetch --quiet --depth 1 --filter=blob:none origin "$REF"
  git -C "$TMP/engine" sparse-checkout set --no-cone "${EXCERPT_PATHS[@]}"
else
  git -C "$TMP/engine" fetch --quiet --depth 1 origin "$REF"
fi
git -C "$TMP/engine" -c advice.detachedHead=false checkout --quiet FETCH_HEAD
COMMIT="$(git -C "$TMP/engine" rev-parse HEAD)"
rm -rf "$TMP/engine/.git"

[ -d "$DEST" ] && chmod -R u+w "$DEST" && rm -rf "$DEST"
mkdir -p "$DEST"
cp -R "$TMP/engine/." "$DEST/"
echo "$COMMIT" > "$DEST/ENGINE_REF"
if [ "${ENGINE_EXCERPT:-0}" = "1" ]; then
  {
    echo "# Excerpt of the Semantic MLOps Engine"
    echo
    echo "Commit ${COMMIT}, fetched with \`make fetch-engine-excerpt\`."
    echo "Contains only these paths of https://github.com/CERTAIN-Project/Semantic_MLOps_engine:"
    echo
    for p in "${EXCERPT_PATHS[@]}"; do echo "- \`${p#/}\`"; done
    echo
    echo "Not included: test_docker/finance_pilot/ (pilot test data, about 355 MB). Run \`make fetch-engine\` for the full repository."
  } > "$DEST/EXCERPT.md"
fi
echo "engine at ${COMMIT:0:12} in vendor/engine$([ "${ENGINE_EXCERPT:-0}" = "1" ] && echo ' (excerpt)' || true)"
