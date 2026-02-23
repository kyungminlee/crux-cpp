#!/usr/bin/env python3
"""Print functions from the call graph in topological order.

Output is a JSON array of arrays.  Each inner array is a strongly connected
component (SCC); functions in a mutual-recursion cycle share one array.
The outer array is ordered so that callees appear before their callers
(leaf / deepest functions first, entry points last).

Only functions present in the 'def' table are included; calls to external
functions (e.g. stdlib) are ignored.
"""

import argparse
import json
import sqlite3
import sys
from collections import defaultdict


def tarjan_sccs(graph: dict[str, list[str]]) -> list[list[str]]:
    """Return SCCs in topological order (callee-first) via iterative Tarjan.

    Each SCC is a list of node keys.  The algorithm is iterative to avoid
    hitting Python's recursion limit on deep call graphs.
    """
    index_counter = [0]
    stack: list[str] = []
    on_stack: set[str] = set()
    index: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    sccs: list[list[str]] = []

    for root in graph:
        if root in index:
            continue

        index[root] = lowlink[root] = index_counter[0]
        index_counter[0] += 1
        stack.append(root)
        on_stack.add(root)
        # Each frame: (node, iterator over its neighbours)
        work = [(root, iter(graph[root]))]

        while work:
            v, neighbours = work[-1]
            try:
                w = next(neighbours)
                if w not in index:
                    index[w] = lowlink[w] = index_counter[0]
                    index_counter[0] += 1
                    stack.append(w)
                    on_stack.add(w)
                    work.append((w, iter(graph[w])))
                elif w in on_stack:
                    lowlink[v] = min(lowlink[v], index[w])
            except StopIteration:
                work.pop()
                if work:
                    parent = work[-1][0]
                    lowlink[parent] = min(lowlink[parent], lowlink[v])
                if lowlink[v] == index[v]:
                    scc: list[str] = []
                    while True:
                        w = stack.pop()
                        on_stack.discard(w)
                        scc.append(w)
                        if w == v:
                            break
                    sccs.append(scc)

    return sccs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print call-graph functions in topological order.")
    parser.add_argument("database", help="SQLite3 database file")
    args = parser.parse_args()

    conn = sqlite3.connect(args.database)

    # Load fully_qualified_name keyed by USR.
    names: dict[str, str] = dict(
        conn.execute("SELECT usr, fully_qualified_name FROM def"))

    # Build directed graph (caller -> callee), restricted to in-root functions.
    graph: dict[str, list[str]] = {usr: [] for usr in names}
    for caller, callee in conn.execute("SELECT caller_usr, callee_usr FROM call"):
        if caller in names and callee in names:
            graph[caller].append(callee)

    conn.close()

    sccs = tarjan_sccs(graph)

    # Replace USRs with human-readable names.
    # result = [[names[u] for u in scc] for scc in sccs]
    result = sccs

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
