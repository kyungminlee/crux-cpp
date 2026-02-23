#!/usr/bin/env bash
# Usage: run_test.sh TOOL EXPECTED_FILE BUILD_DIR ROOT_DIR SOURCE_FILE...
set -euo pipefail

TOOL=$1; EXPECTED=$2; BUILD=$3; ROOT=$4
shift 4

diff "$EXPECTED" <("$TOOL" "$@" --build "$BUILD" --root "$ROOT" 2>/dev/null | sort -u)
