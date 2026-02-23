#!/usr/bin/env python3
"""
Fetch function details from the extract-cpp database.

Usage:
    fetch.py <database> --root DIR <USR> [USR ...]

For each USR, prints a JSON array of objects with:
  usr, fully_qualified_name, text (source code), call (list of callee USRs)
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def fetch_function(conn: sqlite3.Connection, root: Path, usr: str) -> dict | None:
    row = conn.execute(
        "SELECT fully_qualified_name, filename, start_line, end_line "
        "FROM def WHERE usr = ?",
        (usr,),
    ).fetchone()
    if row is None:
        return None

    fqn, filename, start_line, end_line = row

    source_file = root / filename
    try:
        lines = source_file.read_text(encoding="utf-8").splitlines()
        text = "\n".join(lines[start_line - 1 : end_line])
    except OSError as exc:
        text = f"<error reading {source_file}: {exc}>"

    callees = [
        r[0]
        for r in conn.execute(
            "SELECT callee_usr FROM call WHERE caller_usr = ?", (usr,)
        )
    ]

    return {
        "usr": usr,
        "fully_qualified_name": fqn,
        "text": text,
        "call": callees,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch function details from the extract-cpp database.")
    parser.add_argument("database", help="SQLite3 database file")
    parser.add_argument("--root", required=True, metavar="DIR", type=Path,
                        help="Source root directory (used to resolve filenames)")
    parser.add_argument("usrs", nargs="+", metavar="USR",
                        help="Unified Symbol References to look up")
    args = parser.parse_args()

    conn = sqlite3.connect(args.database)

    results = []
    ok = True
    for usr in args.usrs:
        item = fetch_function(conn, args.root, usr)
        if item is None:
            print(f"warning: USR not found: {usr}", file=sys.stderr)
            ok = False
        else:
            results.append(item)

    conn.close()

    print(json.dumps(results, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
