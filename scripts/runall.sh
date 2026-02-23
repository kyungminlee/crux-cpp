#!/usr/bin/env bash
# Run def, call, and class on every file listed in compile_commands.json,
# then load the results into a SQLite3 database.
#
# Usage:
#   runall.sh -B DIR -S DIR -o DB [-W DIR]
#
#   -B  build directory (contains compile_commands.json)
#   -S  source root directory
#   -o  output SQLite3 database file
#   -W  directory for intermediate CSV files (default: mktemp -d)

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BIN_DIR="$SCRIPT_DIR/../build"
PY_DIR="$SCRIPT_DIR/../pysrc"

usage() {
    echo "usage: $(basename "$0") -B DIR -S DIR -o DB [-W DIR]" >&2
    exit 1
}

BUILD_DIR=""
ROOT_DIR=""
OUTPUT_DB=""
WORK_DIR=""

OPTS=$(getopt 'B:S:o:W:' "$@") || usage
eval set -- "$OPTS"

while [[ $# -gt 0 ]]; do
    case "$1" in
        -B) BUILD_DIR="$2"; shift 2 ;;
        -S) ROOT_DIR="$2";  shift 2 ;;
        -o) OUTPUT_DB="$2"; shift 2 ;;
        -W) WORK_DIR="$2";  shift 2 ;;
        --) shift; break ;;
    esac
done

[[ -n "$BUILD_DIR" ]] || { echo "error: -B is required" >&2; exit 1; }
[[ -n "$ROOT_DIR"  ]] || { echo "error: -S is required" >&2; exit 1; }
[[ -n "$OUTPUT_DB" ]] || { echo "error: -o is required" >&2; exit 1; }

# Resolve to absolute paths.
BUILD_DIR=$(cd "$BUILD_DIR" && pwd)
ROOT_DIR=$(cd "$ROOT_DIR" && pwd)

# Set up work directory; clean up on exit if we created it.
if [[ -z "$WORK_DIR" ]]; then
    WORK_DIR=$(mktemp -d)
    trap 'rm -rf "$WORK_DIR"' EXIT
fi

# Extract source file paths from compile_commands.json.
FILES=()
while IFS= read -r f; do
    FILES+=("$f")
done < <(python3 -c "
import json, sys
for e in json.load(open(sys.argv[1])):
    print(e['file'])
" "$BUILD_DIR/compile_commands.json")

[[ ${#FILES[@]} -gt 0 ]] \
    || { echo "error: no files found in $BUILD_DIR/compile_commands.json" >&2; exit 1; }

# Run extraction tools.
for tool in def call class; do
    "$BIN_DIR/$tool" "${FILES[@]}" \
        --build "$BUILD_DIR" \
        --root  "$ROOT_DIR"  \
        -o      "$WORK_DIR/$tool.csv"
done

# Load all three CSVs into the output database.
python3 "$PY_DIR/load.py" "$OUTPUT_DB" \
    --def   "$WORK_DIR/def.csv"   \
    --call  "$WORK_DIR/call.csv"  \
    --class "$WORK_DIR/class.csv"
