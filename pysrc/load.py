#!/usr/bin/env python3
"""
Load crux-cpp CSV files into a SQLite3 database.

Usage:
    load.py <database> [--def FILE --root DIR] [--call FILE] [--class FILE]

Existing rows are replaced on primary-key conflict (INSERT OR REPLACE).

Schema notes
------------
def
  - usr is the primary key (Clang USR uniquely identifies a definition).
  - class and visibility are NOT NULL but may be empty for free functions.

source
  - usr is the primary key, references def(usr).
  - text holds the source code extracted from filename at [start_line, end_line].
  - Requires --root to resolve relative filenames.

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
            visibility           TEXT    NOT NULL
        )""",

    "source": """\
        CREATE TABLE IF NOT EXISTS source (
            usr        TEXT     PRIMARY KEY  REFERENCES def(usr),
            filename   TEXT     NOT NULL,
            start_line INTEGER  NOT NULL,
            end_line   INTEGER  NOT NULL,
            text       TEXT     NOT NULL
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

# Columns read from each CSV (def CSV still has all original columns).
CSV_COLUMNS = {
    "def":   ["usr", "fully_qualified_name", "kind", "class",
              "visibility", "filename", "start_line", "end_line"],
    "call":  ["caller_usr", "callee_usr"],
    "class": ["usr", "parent_usr", "visibility"],
}

DEF_COLS    = ["usr", "fully_qualified_name", "kind", "class", "visibility"]
SOURCE_COLS = ["usr", "filename", "start_line", "end_line", "text"]

# ── Helpers ───────────────────────────────────────────────────────────────────

def read_source_text(root: Path, filename: str,
                     start_line: int, end_line: int) -> str:
    lines = (root / filename).read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[start_line - 1 : end_line])


def load_def_csv(conn: sqlite3.Connection, path: Path, root: Path) -> int:
    """Load def CSV into the 'def' and 'source' tables. Returns row count."""
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    def_rows, source_rows = [], []
    for row in rows:
        def_rows.append([row[c] for c in DEF_COLS])
        start = int(row["start_line"])
        end   = int(row["end_line"])
        try:
            text = read_source_text(root, row["filename"], start, end)
        except OSError as exc:
            print(f"warning: {exc}", file=sys.stderr)
            text = ""
        source_rows.append([row["usr"], row["filename"], start, end, text])

    def insert_sql(table, cols):
        col_list     = ", ".join(f'"{c}"' for c in cols)
        placeholders = ", ".join("?" * len(cols))
        return f'INSERT OR REPLACE INTO "{table}" ({col_list}) VALUES ({placeholders})'

    with conn:
        conn.executemany(insert_sql("def",    DEF_COLS),    def_rows)
        conn.executemany(insert_sql("source", SOURCE_COLS), source_rows)
    return len(rows)


def load_csv(conn: sqlite3.Connection, path: Path, table: str) -> int:
    """INSERT OR REPLACE all rows from path into table. Returns row count."""
    cols = CSV_COLUMNS[table]
    col_list     = ", ".join(f'"{c}"' for c in cols)
    placeholders = ", ".join("?" * len(cols))
    sql = (f'INSERT OR REPLACE INTO "{table}" ({col_list}) '
           f'VALUES ({placeholders})')

    with open(path, newline="", encoding="utf-8") as f:
        rows = [[row[c] for c in cols] for row in csv.DictReader(f)]

    with conn:
        conn.executemany(sql, rows)
    return len(rows)

# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load crux-cpp CSV files into a SQLite3 database.")
    parser.add_argument("database", help="SQLite3 database file")
    parser.add_argument("--def",   dest="def_file",   metavar="FILE",
                        type=Path, help="CSV produced by the def tool")
    parser.add_argument("--root",  dest="root",       metavar="DIR",
                        type=Path, help="Source root dir (required with --def)")
    parser.add_argument("--call",  dest="call_file",  metavar="FILE",
                        type=Path, help="CSV produced by the call tool")
    parser.add_argument("--class", dest="class_file", metavar="FILE",
                        type=Path, help="CSV produced by the class tool")
    args = parser.parse_args()

    if not any([args.def_file, args.call_file, args.class_file]):
        parser.error("at least one of --def, --call, --class is required")
    if args.def_file and not args.root:
        parser.error("--root is required when --def is given")

    conn = sqlite3.connect(args.database)
    conn.execute("PRAGMA journal_mode=WAL")
    for ddl in DDL.values():
        conn.execute(ddl)
    conn.commit()

    ok = True

    if args.def_file:
        try:
            count = load_def_csv(conn, args.def_file, args.root)
            print(f"{args.def_file}: {count} rows → 'def' + 'source'")
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            ok = False

    for table, path in [("call", args.call_file), ("class", args.class_file)]:
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
