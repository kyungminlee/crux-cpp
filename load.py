#!/usr/bin/env python3
"""
Load extract-cpp CSV files into a SQLite3 database.

Usage:
    load.py <database> <csv_file>...

Each CSV file is identified by its header row; the table name matches the
CLI tool that produced it (def, call, class).  Existing rows are replaced
on primary-key conflict (INSERT OR REPLACE).

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

# Header rows produced by each tool (used to auto-detect the table).
EXPECTED_HEADERS = {
    "def":   ["usr", "fully_qualified_name", "kind", "class",
              "visibility", "filename", "start_line", "end_line"],
    "call":  ["caller_usr", "callee_usr"],
    "class": ["usr", "parent_usr", "visibility"],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def detect_table(path: Path) -> str:
    """Return the table name by matching the CSV header to a known schema."""
    with open(path, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f), None)
    if header is None:
        raise ValueError(f"{path}: empty file")
    for table, expected in EXPECTED_HEADERS.items():
        if header == expected:
            return table
    raise ValueError(
        f"{path}: unrecognized header {header!r}\n"
        f"Expected one of: {list(EXPECTED_HEADERS.values())}"
    )


def load_csv(conn: sqlite3.Connection, path: Path, table: str) -> int:
    """INSERT OR REPLACE all rows from path into table. Returns row count."""
    cols = EXPECTED_HEADERS[table]
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
    if len(sys.argv) < 3:
        print(f"usage: {Path(sys.argv[0]).name} <database> <csv_file>...",
              file=sys.stderr)
        return 1

    db_path = sys.argv[1]
    csv_paths = [Path(p) for p in sys.argv[2:]]

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")

    for ddl in DDL.values():
        conn.execute(ddl)
    conn.commit()

    ok = True
    for csv_path in csv_paths:
        try:
            table = detect_table(csv_path)
            count = load_csv(conn, csv_path, table)
            print(f"{csv_path}: {count} rows → '{table}'")
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            ok = False

    conn.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
