#!/usr/bin/env python3
"""
Mock summarizer CLI for testing without a real LLM.

Usage:
    mock_summarize.py <database> [--force]

Produces summaries of the form:
    "{fully_qualified_name} is a great function and has size of {size}"
where size is the number of characters in the source text.
"""

import argparse
import re
import sqlite3
import sys

from summary import summary_update


def _mock(prompt: str) -> str:
    # First line: "Summarize the following C++ function or method `{fqn}`."
    first_line = prompt.split("\n")[0]
    m = re.search(r"`([^`]+)`", first_line)
    fqn = m.group(1) if m else "unknown"

    # Source text is between the ```cpp and ``` fences.
    m = re.search(r"```cpp\n(.*?)\n```", prompt, re.DOTALL)
    size = len(m.group(1)) if m else 0

    return f"{fqn} is a great function and has size of {size}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize C++ functions using a mock LLM (for testing).")
    parser.add_argument("database", help="SQLite3 database file")
    parser.add_argument("--force", action="store_true",
                        help="Re-summarize even if a summary already exists")
    args = parser.parse_args()

    conn = sqlite3.connect(args.database)
    conn.execute("PRAGMA journal_mode=WAL")
    summary_update(conn, _mock, force=args.force)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
