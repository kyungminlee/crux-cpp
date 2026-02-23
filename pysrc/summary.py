"""
Library for summarizing C++ function definitions using an LLM.

Core API
--------
summary_update(conn, summarize, force=False)
    Populate the 'summary' table in an open SQLite connection by calling
    `summarize(prompt) -> str` for each in-root function in topological
    (callee-first) order.

Helpers exported for use in CLI wrappers
----------------------------------------
tarjan_sccs(graph)   -- iterative Tarjan SCC, callee-first order
build_prompt(...)    -- build the LLM prompt for one function
"""

import sqlite3
from collections.abc import Callable


# ── Tarjan SCC (iterative) ────────────────────────────────────────────────────

def tarjan_sccs(graph: dict[str, list[str]]) -> list[list[str]]:
    """Return SCCs in topological order (callee-first) via iterative Tarjan."""
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
                    lowlink[work[-1][0]] = min(lowlink[work[-1][0]], lowlink[v])
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


# ── Prompt builder ────────────────────────────────────────────────────────────

def build_prompt(fqn: str, text: str,
                 callee_summaries: list[tuple[str, str]]) -> str:
    lines = [
        f"Summarize the following C++ function or method `{fqn}`.",
        "",
        "Source code:",
        "```cpp",
        text,
        "```",
    ]
    if callee_summaries:
        lines += ["", "Summaries of functions it calls:"]
        for callee_fqn, summary in callee_summaries:
            lines.append(f"- `{callee_fqn}`: {summary}")
    lines += [
        "",
        "Write a concise one- or two-sentence summary describing what this "
        "function does.",
    ]
    return "\n".join(lines)


# ── Library entry point ───────────────────────────────────────────────────────

def summary_update(
    conn: sqlite3.Connection,
    summarize: Callable[[str], str],
    force: bool = False,
) -> None:
    """Populate the 'summary' table using the provided summarize function.

    Parameters
    ----------
    conn:       Open SQLite connection to an extract-cpp database.
    summarize:  Callable that takes a prompt string and returns a summary.
    force:      If True, re-summarize functions that already have a summary.
    """
    conn.execute("""\
        CREATE TABLE IF NOT EXISTS summary (
            usr     TEXT  PRIMARY KEY  REFERENCES def(usr),
            summary TEXT  NOT NULL
        )""")
    conn.commit()

    # Load all in-root functions: usr → (fully_qualified_name, text).
    rows = conn.execute(
        "SELECT d.usr, d.fully_qualified_name, s.text "
        "FROM def d JOIN source s USING (usr)"
    ).fetchall()
    names: dict[str, str] = {usr: fqn  for usr, fqn, _    in rows}
    texts: dict[str, str] = {usr: text for usr, _,   text in rows}

    # Build call graph restricted to in-root functions.
    graph: dict[str, list[str]] = {usr: [] for usr in names}
    for caller, callee in conn.execute("SELECT caller_usr, callee_usr FROM call"):
        if caller in names and callee in names:
            graph[caller].append(callee)

    sccs  = tarjan_sccs(graph)
    total = sum(len(s) for s in sccs)
    done  = 0

    for scc in sccs:
        scc_set = set(scc)

        for usr in scc:
            done += 1
            fqn  = names[usr]

            if not force:
                if conn.execute(
                    "SELECT 1 FROM summary WHERE usr = ?", (usr,)
                ).fetchone():
                    print(f"[{done}/{total}] skip (already summarized): {fqn}")
                    continue

            # Collect summaries of callees processed in earlier SCCs.
            callee_summaries: list[tuple[str, str]] = []
            for callee_usr in graph[usr]:
                if callee_usr in scc_set:
                    continue  # mutual recursion — no summary yet
                row = conn.execute(
                    "SELECT d.fully_qualified_name, s.summary "
                    "FROM def d JOIN summary s USING (usr) WHERE d.usr = ?",
                    (callee_usr,),
                ).fetchone()
                if row:
                    callee_summaries.append(row)

            prompt = build_prompt(fqn, texts[usr], callee_summaries)
            result = summarize(prompt)

            conn.execute(
                "INSERT OR REPLACE INTO summary (usr, summary) VALUES (?, ?)",
                (usr, result),
            )
            conn.commit()
            print(f"[{done}/{total}] summarized: {fqn}")
