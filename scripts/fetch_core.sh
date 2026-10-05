#!/usr/bin/env bash
# Fetch the pinned AIDOC-AP core release into vendor/aidoc-ap and verify it against vendor/LOCK.json.
#   scripts/fetch_core.sh                 fetch the tag recorded in LOCK.json and verify checksums
#   UPDATE_LOCK=1 AIDOC_CORE_TAG=v1.3 scripts/fetch_core.sh
#                                         switch to another core release (needs approval by the T5.3 lead)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/vendor/aidoc-ap"
REPO="https://github.com/certain-project/aidoc-ap.git"
PY="${PY:-python3}"
if [ -z "${AIDOC_CORE_TAG:-}" ] && [ -f "$ROOT/vendor/LOCK.json" ]; then
  AIDOC_CORE_TAG="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["tag"])' "$ROOT/vendor/LOCK.json")"
fi
TAG="${AIDOC_CORE_TAG:-v1.2}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

git -c advice.detachedHead=false clone --quiet --depth 1 --branch "$TAG" "$REPO" "$TMP/core"
COMMIT="$(git -C "$TMP/core" rev-parse HEAD)"
[ -d "$DEST" ] && chmod -R u+w "$DEST" && rm -rf "$DEST"
mkdir -p "$DEST/reference_ontologies"
cp "$TMP/core/aidoc-ap.ttl" "$TMP/core/annex_4.ttl" "$TMP/core/LICENSE-CC-BY.txt" "$DEST/"
cp "$TMP/core/reference_ontologies/"*.ttl "$DEST/reference_ontologies/"
chmod -R a-w "$DEST"

cd "$ROOT/scripts"
if [ "${UPDATE_LOCK:-0}" = "1" ] || [ ! -f "$ROOT/vendor/LOCK.json" ]; then
  "$PY" lock.py write --tag "$TAG" --commit "$COMMIT"
fi
"$PY" lock.py verify
