#!/usr/bin/env python3
"""
Load extract-cpp CSV files into a SQLite3 database.

Usage:
    load.py <database> [--def FILE] [--call FILE] [--class FILE]

Existing rows are replaced on primary-key conflict (INSERT OR REPLACE).

Schema notes
------------
def
  - usr is the primary key (Clang USR uniquely identifies a definition).
  - class and visibility are NOT NULL but may be empty for free functions.

call
  - (caller_usr, callee_usr) is the primary key.
  - caller_usr references def(usr): callers are always in-root.
  - callee_usr has no foreign key: callees may be outside the root
    (e.g. std library functions).

class
  - (usr, parent_usr) is the primary key.
  - Class USRs are distinct from function USRs, so no reference to def.
"""

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

# ── Schema ────────────────────────────────────────────────────────────────────

DDL = {
    "def": """\
        CREATE TABLE IF NOT EXISTS def (
            usr                  TEXT    PRIMARY KEY,
            fully_qualified_name TEXT    NOT NULL,
            kind                 TEXT    NOT NULL,
            class                TEXT    NOT NULL,
            visibility           TEXT    NOT NULL,
            filename             TEXT    NOT NULL,
            start_line           INTEGER NOT NULL,
            end_line             INTEGER NOT NULL
        )""",

    "call": """\
        CREATE TABLE IF NOT EXISTS call (
            caller_usr  TEXT  NOT NULL  REFERENCES def(usr),
            callee_usr  TEXT  NOT NULL,
            PRIMARY KEY (caller_usr, callee_usr)
        )""",

    "class": """\
        CREATE TABLE IF NOT EXISTS class (
            usr         TEXT  NOT NULL,
            parent_usr  TEXT  NOT NULL,
            visibility  TEXT  NOT NULL,
            PRIMARY KEY (usr, parent_usr)
        )""",
}

COLUMNS = {
    "def":   ["usr", "fully_qualified_name", "kind", "class",
              "visibility", "filename", "start_line", "end_line"],
    "call":  ["caller_usr", "callee_usr"],
    "class": ["usr", "parent_usr", "visibility"],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_csv(conn: sqlite3.Connection, path: Path, table: str) -> int:
    """INSERT OR REPLACE all rows from path into table. Returns row count."""
    cols = COLUMNS[table]
    placeholders = ", ".join("?" * len(cols))
    # Quote column names to handle reserved-word clashes (e.g. "class").
    col_list = ", ".join(f'"{c}"' for c in cols)
    sql = (f'INSERT OR REPLACE INTO "{table}" ({col_list}) '
           f'VALUES ({placeholders})')

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [[row[c] for c in cols] for row in reader]

    with conn:
        conn.executemany(sql, rows)
    return len(rows)

# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load extract-cpp CSV files into a SQLite3 database.")
    parser.add_argument("database", help="SQLite3 database file")
    parser.add_argument("--def",   dest="def_file",   metavar="FILE",
                        type=Path, help="CSV produced by the def tool")
    parser.add_argument("--call",  dest="call_file",  metavar="FILE",
                        type=Path, help="CSV produced by the call tool")
    parser.add_argument("--class", dest="class_file", metavar="FILE",
                        type=Path, help="CSV produced by the class tool")
    args = parser.parse_args()

    files = {
        "def":   args.def_file,
        "call":  args.call_file,
        "class": args.class_file,
    }
    if not any(files.values()):
        parser.error("at least one of --def, --call, --class is required")

    conn = sqlite3.connect(args.database)
    conn.execute("PRAGMA journal_mode=WAL")

    for ddl in DDL.values():
        conn.execute(ddl)
    conn.commit()

    ok = True
    for table, path in files.items():
        if path is None:
            continue
        try:
            count = load_csv(conn, path, table)
            print(f"{path}: {count} rows → '{table}'")
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            ok = False

    conn.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
