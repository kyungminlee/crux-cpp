"""
Tests for the crux_cpp Python package:
  summary.py  – tarjan_sccs, build_prompt, summary_update
  topo.py     – tarjan_sccs  (independent copy; same algorithm)
  mock_summarize.py – _mock
  load.py     – read_source_text, load_def_csv, load_csv
  fetch.py    – fetch_function
"""

import csv
import re
import sqlite3

import pytest

import crux_cpp.summary as summary_mod
import crux_cpp.topo as topo_mod
from crux_cpp.fetch import fetch_function
from crux_cpp.load import load_csv, load_def_csv, read_source_text
from crux_cpp.mock_summarize import _mock
from crux_cpp.summary import build_prompt, summary_update, tarjan_sccs


# ── Fixtures ──────────────────────────────────────────────────────────────────

SCHEMA = """\
    CREATE TABLE def (
        usr                  TEXT PRIMARY KEY,
        fully_qualified_name TEXT NOT NULL,
        kind                 TEXT NOT NULL,
        class                TEXT NOT NULL,
        visibility           TEXT NOT NULL
    );
    CREATE TABLE source (
        usr        TEXT PRIMARY KEY REFERENCES def(usr),
        filename   TEXT NOT NULL,
        start_line INTEGER NOT NULL,
        end_line   INTEGER NOT NULL,
        text       TEXT NOT NULL
    );
    CREATE TABLE call (
        caller_usr TEXT NOT NULL REFERENCES def(usr),
        callee_usr TEXT NOT NULL,
        PRIMARY KEY (caller_usr, callee_usr)
    );
    CREATE TABLE class (
        usr        TEXT NOT NULL,
        parent_usr TEXT NOT NULL,
        visibility TEXT NOT NULL,
        PRIMARY KEY (usr, parent_usr)
    );
"""


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    yield conn
    conn.close()


def insert_func(conn, usr, fqn, text="code"):
    conn.execute(
        "INSERT INTO def VALUES (?, ?, 'Function', '', '')", (usr, fqn)
    )
    conn.execute(
        "INSERT INTO source VALUES (?, 'f.cpp', 1, 1, ?)", (usr, text)
    )
    conn.commit()


# ── tarjan_sccs (summary.py) ──────────────────────────────────────────────────

class TestTarjanSccs:
    def test_empty(self):
        assert tarjan_sccs({}) == []

    def test_single_node(self):
        assert tarjan_sccs({"a": []}) == [["a"]]

    def test_self_loop(self):
        sccs = tarjan_sccs({"a": ["a"]})
        assert len(sccs) == 1
        assert sccs[0] == ["a"]

    def test_linear_chain_callee_first(self):
        # a→b→c: leaf c should appear before b, b before a
        graph = {"a": ["b"], "b": ["c"], "c": []}
        sccs = tarjan_sccs(graph)
        assert len(sccs) == 3
        flat = [s[0] for s in sccs]
        assert flat.index("c") < flat.index("b") < flat.index("a")

    def test_simple_cycle_forms_one_scc(self):
        graph = {"a": ["b"], "b": ["a"]}
        sccs = tarjan_sccs(graph)
        assert len(sccs) == 1
        assert set(sccs[0]) == {"a", "b"}

    def test_diamond_dag(self):
        # a→b, a→c, b→d, c→d
        graph = {"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []}
        sccs = tarjan_sccs(graph)
        flat = [s[0] for s in sccs]
        assert flat.index("d") < flat.index("b")
        assert flat.index("d") < flat.index("c")
        assert flat.index("b") < flat.index("a")
        assert flat.index("c") < flat.index("a")

    def test_disconnected_components(self):
        graph = {"a": [], "b": []}
        sccs = tarjan_sccs(graph)
        assert len(sccs) == 2
        assert {s[0] for s in sccs} == {"a", "b"}

    def test_complex_cycle_with_tail(self):
        # cycle: x→y→z→x; tail: w→x (w not in cycle)
        graph = {"w": ["x"], "x": ["y"], "y": ["z"], "z": ["x"]}
        sccs = tarjan_sccs(graph)
        assert len(sccs) == 2
        cycle_scc = next(s for s in sccs if len(s) > 1)
        tail_scc  = next(s for s in sccs if len(s) == 1)
        assert set(cycle_scc) == {"x", "y", "z"}
        assert tail_scc == ["w"]
        # cycle (callee) must appear before its caller w
        assert sccs.index(cycle_scc) < sccs.index(tail_scc)


# ── tarjan_sccs in topo.py is an independent copy; spot-check it ──────────────

class TestTarjanSccsTopo:
    def test_same_behaviour_as_summary(self):
        graph = {"a": ["b"], "b": ["c"], "c": []}
        assert topo_mod.tarjan_sccs(graph) == summary_mod.tarjan_sccs(graph)

    def test_cycle(self):
        graph = {"p": ["q"], "q": ["p"]}
        sccs = topo_mod.tarjan_sccs(graph)
        assert len(sccs) == 1
        assert set(sccs[0]) == {"p", "q"}


# ── build_prompt ──────────────────────────────────────────────────────────────

class TestBuildPrompt:
    def test_first_line_contains_fqn(self):
        prompt = build_prompt("MyNS::foo", "int x;", [])
        first = prompt.split("\n")[0]
        assert "`MyNS::foo`" in first

    def test_source_in_code_fence(self):
        prompt = build_prompt("f", "return 42;", [])
        assert "```cpp\nreturn 42;\n```" in prompt

    def test_no_callee_section_when_empty(self):
        prompt = build_prompt("f", "code", [])
        assert "Summaries of functions it calls:" not in prompt

    def test_callee_section_present(self):
        prompt = build_prompt("f", "code", [("g", "g does stuff")])
        assert "Summaries of functions it calls:" in prompt
        assert "- `g`: g does stuff" in prompt

    def test_multiple_callees(self):
        prompt = build_prompt("f", "code", [("g", "sum1"), ("h", "sum2")])
        assert "- `g`: sum1" in prompt
        assert "- `h`: sum2" in prompt

    def test_fqn_parseable_by_mock(self):
        """_mock must be able to extract the FQN from the prompt first line."""
        fqn = "Outer::Inner::method"
        prompt = build_prompt(fqn, "code", [])
        m = re.search(r"`([^`]+)`", prompt.split("\n")[0])
        assert m is not None and m.group(1) == fqn


# ── _mock ─────────────────────────────────────────────────────────────────────

class TestMock:
    def test_output_format(self):
        prompt = build_prompt("ns::foo", "int x = 1;", [])
        result = _mock(prompt)
        assert result == f"ns::foo is a great function and has size of {len('int x = 1;')}"

    def test_empty_source(self):
        prompt = build_prompt("f", "", [])
        result = _mock(prompt)
        assert result == "f is a great function and has size of 0"

    def test_multiline_source(self):
        src = "int foo() {\n    return 1;\n}"
        prompt = build_prompt("foo", src, [])
        result = _mock(prompt)
        assert result == f"foo is a great function and has size of {len(src)}"

    def test_fqn_with_template(self):
        prompt = build_prompt("Pair<int>::swap", "void swap(){}", [])
        result = _mock(prompt)
        assert result.startswith("Pair<int>::swap is a great function")


# ── summary_update ────────────────────────────────────────────────────────────

class TestSummaryUpdate:
    def test_creates_summary_table(self, db):
        insert_func(db, "u1", "foo")
        summary_update(db, lambda p: "s")
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "summary" in tables

    def test_writes_summary(self, db):
        insert_func(db, "u1", "foo")
        summary_update(db, lambda p: "great function")
        row = db.execute("SELECT summary FROM summary WHERE usr='u1'").fetchone()
        assert row == ("great function",)

    def test_skips_existing(self, db):
        insert_func(db, "u1", "foo")
        summary_update(db, lambda p: "first")
        calls = []
        summary_update(db, lambda p: calls.append(p) or "second")
        assert calls == []
        assert db.execute("SELECT summary FROM summary WHERE usr='u1'").fetchone()[0] == "first"

    def test_force_resummaries(self, db):
        insert_func(db, "u1", "foo")
        summary_update(db, lambda p: "old")
        summary_update(db, lambda p: "new", force=True)
        assert db.execute("SELECT summary FROM summary WHERE usr='u1'").fetchone()[0] == "new"

    def test_callee_before_caller(self, db):
        insert_func(db, "callee", "leaf")
        insert_func(db, "caller", "root")
        db.execute("INSERT INTO call VALUES ('caller', 'callee')")
        db.commit()

        order = []
        def mock(prompt):
            m = re.search(r"`([^`]+)`", prompt.split("\n")[0])
            order.append(m.group(1) if m else "?")
            return "s"

        summary_update(db, mock)
        assert order == ["leaf", "root"]

    def test_mutual_recursion_both_summarized(self, db):
        insert_func(db, "u1", "ping")
        insert_func(db, "u2", "pong")
        db.execute("INSERT INTO call VALUES ('u1', 'u2')")
        db.execute("INSERT INTO call VALUES ('u2', 'u1')")
        db.commit()
        summary_update(db, lambda p: "s")
        count = db.execute("SELECT COUNT(*) FROM summary").fetchone()[0]
        assert count == 2

    def test_callee_summary_included_in_prompt(self, db):
        insert_func(db, "callee", "leaf", "int leaf(){}")
        insert_func(db, "caller", "root", "void root(){}")
        db.execute("INSERT INTO call VALUES ('caller', 'callee')")
        db.commit()

        prompts = {}
        def mock(prompt):
            m = re.search(r"`([^`]+)`", prompt.split("\n")[0])
            fqn = m.group(1) if m else "?"
            prompts[fqn] = prompt
            return f"summary of {fqn}"

        summary_update(db, mock)
        assert "summary of leaf" in prompts["root"]

    def test_external_callee_ignored(self, db):
        insert_func(db, "u1", "foo")
        # callee 'ext' is not in def table — should not crash
        db.execute("INSERT INTO call VALUES ('u1', 'ext_usr')")
        db.commit()
        summary_update(db, lambda p: "s")
        assert db.execute("SELECT COUNT(*) FROM summary").fetchone()[0] == 1


# ── read_source_text ──────────────────────────────────────────────────────────

class TestReadSourceText:
    def test_middle_lines(self, tmp_path):
        (tmp_path / "f.cpp").write_text("a\nb\nc\nd\n")
        assert read_source_text(tmp_path, "f.cpp", 2, 3) == "b\nc"

    def test_single_line(self, tmp_path):
        (tmp_path / "f.cpp").write_text("only\n")
        assert read_source_text(tmp_path, "f.cpp", 1, 1) == "only"

    def test_full_file(self, tmp_path):
        (tmp_path / "f.cpp").write_text("x\ny\n")
        assert read_source_text(tmp_path, "f.cpp", 1, 2) == "x\ny"


# ── load_def_csv ──────────────────────────────────────────────────────────────

class TestLoadDefCsv:
    def _make_db(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(SCHEMA)
        return conn

    def _write_def_csv(self, tmp_path, rows):
        path = tmp_path / "def.csv"
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["usr", "fully_qualified_name", "kind", "class",
                         "visibility", "filename", "start_line", "end_line"])
            w.writerows(rows)
        return path

    def test_inserts_def_and_source(self, tmp_path):
        (tmp_path / "f.cpp").write_text("int foo() {\n    return 1;\n}\n")
        path = self._write_def_csv(tmp_path, [
            ["u1", "foo", "Function", "", "", "f.cpp", "1", "3"]
        ])
        conn = self._make_db()
        count = load_def_csv(conn, path, tmp_path)
        assert count == 1
        assert conn.execute("SELECT fully_qualified_name FROM def WHERE usr='u1'").fetchone() == ("foo",)
        text = conn.execute("SELECT text FROM source WHERE usr='u1'").fetchone()[0]
        assert text == "int foo() {\n    return 1;\n}"

    def test_returns_row_count(self, tmp_path):
        for i in range(3):
            (tmp_path / f"f{i}.cpp").write_text("int f(){}\n")
        path = self._write_def_csv(tmp_path, [
            [f"u{i}", f"f{i}", "Function", "", "", f"f{i}.cpp", "1", "1"]
            for i in range(3)
        ])
        conn = self._make_db()
        assert load_def_csv(conn, path, tmp_path) == 3

    def test_missing_source_file_warns(self, tmp_path, capsys):
        path = self._write_def_csv(tmp_path, [
            ["u1", "foo", "Function", "", "", "missing.cpp", "1", "1"]
        ])
        conn = self._make_db()
        load_def_csv(conn, path, tmp_path)  # should not raise
        assert "warning" in capsys.readouterr().err


# ── load_csv (call / class tables) ───────────────────────────────────────────

class TestLoadCsv:
    def _make_db(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(SCHEMA)
        return conn

    def test_load_call(self, tmp_path):
        path = tmp_path / "call.csv"
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["caller_usr", "callee_usr"])
            w.writerow(["u1", "u2"])
        conn = self._make_db()
        count = load_csv(conn, path, "call")
        assert count == 1
        assert conn.execute("SELECT * FROM call").fetchone() == ("u1", "u2")

    def test_load_class(self, tmp_path):
        path = tmp_path / "class.csv"
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["usr", "parent_usr", "visibility"])
            w.writerow(["child", "parent", "public"])
        conn = self._make_db()
        count = load_csv(conn, path, "class")
        assert count == 1
        assert conn.execute("SELECT * FROM class").fetchone() == ("child", "parent", "public")

    def test_duplicate_rows_replaced(self, tmp_path):
        path = tmp_path / "call.csv"
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["caller_usr", "callee_usr"])
            w.writerow(["u1", "u2"])
            w.writerow(["u1", "u2"])  # duplicate primary key
        conn = self._make_db()
        load_csv(conn, path, "call")
        assert conn.execute("SELECT COUNT(*) FROM call").fetchone()[0] == 1


# ── fetch_function ────────────────────────────────────────────────────────────

@pytest.fixture
def populated_db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    conn.execute("INSERT INTO def VALUES ('u1', 'foo', 'Function', '', '')")
    conn.execute("INSERT INTO source VALUES ('u1', 'f.cpp', 1, 1, 'int foo(){}')")
    conn.execute("INSERT INTO def VALUES ('u2', 'bar', 'Function', '', '')")
    conn.execute("INSERT INTO source VALUES ('u2', 'f.cpp', 2, 2, 'int bar(){}')")
    conn.execute("INSERT INTO call VALUES ('u1', 'u2')")
    conn.commit()
    yield conn
    conn.close()


class TestFetchFunction:
    def test_returns_correct_fields(self, populated_db):
        result = fetch_function(populated_db, "u1")
        assert result == {
            "usr": "u1",
            "fully_qualified_name": "foo",
            "text": "int foo(){}",
            "call": ["u2"],
        }

    def test_returns_none_for_missing_usr(self, populated_db):
        assert fetch_function(populated_db, "nonexistent") is None

    def test_no_callees(self, populated_db):
        result = fetch_function(populated_db, "u2")
        assert result["call"] == []

    def test_multiple_callees(self, populated_db):
        populated_db.execute("INSERT INTO def VALUES ('u3', 'baz', 'Function', '', '')")
        populated_db.execute("INSERT INTO source VALUES ('u3', 'f.cpp', 3, 3, 'void baz(){}')")
        populated_db.execute("INSERT INTO call VALUES ('u1', 'u3')")
        populated_db.commit()
        result = fetch_function(populated_db, "u1")
        assert set(result["call"]) == {"u2", "u3"}
