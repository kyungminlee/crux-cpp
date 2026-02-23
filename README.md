# crux-cpp

crux-cpp extracts structural information from a C++ codebase — function definitions, call graphs, and class hierarchies — and stores it in a SQLite database that can be queried or fed to an LLM summarizer.

## Requirements

**C++ tools** (extraction binaries):
- CMake ≥ 3.28
- LLVM/Clang ≥ 19 with development libraries

**Python tools** (database + summarization):
- Python ≥ 3.13
- [uv](https://docs.astral.sh/uv/) (or pip)

---

## Building the C++ tools

### macOS (Homebrew LLVM)

```bash
brew install llvm

cmake --preset macos
cmake --build --preset macos
```

### Linux (Ubuntu/Debian with LLVM 19)

```bash
sudo apt-get install llvm-19-dev libclang-19-dev clang-19

cmake --preset linux
cmake --build --preset linux
```

Binaries are written to `build/cppsrc/`: `def`, `call`, and `class`.

### Running C++ tests

```bash
ctest --test-dir build
```

---

## Installing the Python package

### Development (editable)

```bash
uv sync
```

### As a wheel

```bash
uv build                          # produces dist/crux_cpp-*.whl
pip install dist/crux_cpp-*.whl
```

### Running Python tests

```bash
uv run pytest
```

---

## C++ extraction tools

All three tools take the same arguments:

```
TOOL SOURCE1.cpp [SOURCE2.cpp ...] --build BUILD_DIR --root ROOT_DIR [-o OUTPUT.csv]
```

- `--build`: directory containing `compile_commands.json`
- `--root`: only emit rows for source files under this path (excludes system headers)
- `-o`: write output to a file instead of stdout

### `def` — function definitions

Extracts definitions of functions, methods, constructors, destructors, conversion functions, function templates, and their specializations.

Output columns: `usr`, `fully_qualified_name`, `kind`, `class`, `visibility`, `filename`, `start_line`, `end_line`

### `call` — call graph

Extracts caller → callee relationships for all call expressions inside in-root function bodies.

Output columns: `caller_usr`, `callee_usr`

### `class` — class hierarchy

Extracts direct base-class relationships for all class/struct definitions.

Output columns: `usr`, `parent_usr`, `visibility`

---

## Full pipeline: `runall.sh`

`scripts/runall.sh` runs all three extractors over a project and loads the results into a SQLite database.

```bash
scripts/runall.sh -B BUILD_DIR -S SOURCE_ROOT -o OUTPUT.db
```

- `-B`: build directory containing `compile_commands.json`
- `-S`: source root (passed as `--root` to the extractors)
- `-o`: output SQLite database file
- `-W`: (optional) directory for intermediate CSV files; defaults to a temp dir

**Example** — index the bundled test project:

```bash
# 1. Configure the test project to generate compile_commands.json
cmake -B build/tests/simple -S tests/simple \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY

# 2. Run the pipeline
scripts/runall.sh -B build/tests/simple -S tests/simple -o my.db
```

Requires the Python package to be installed (`uv sync` or `pip install`).

---

## Python CLI tools

After installation the following commands are available:

### `crux-load`

Load CSV files produced by the C++ extractors into a SQLite database.

```bash
crux-load my.db --def def.csv --root /path/to/src --call call.csv --class class.csv
```

### `crux-topo`

Print all in-root functions in topological order (callees before callers). Each line is a strongly-connected component (SCC); functions in a mutual-recursion cycle share one SCC.

```bash
crux-topo my.db
```

### `crux-fetch`

Fetch source text and callee list for one or more functions by USR.

```bash
crux-fetch my.db 'c:@F@main#'
```

### `crux-mock-summarize`

Populate the `summary` table using a mock LLM (for testing). Summaries have the form `"{name} is a great function and has size of {N}"`.

```bash
crux-mock-summarize my.db [--force]
```

---

## Database schema

| Table | Key columns | Description |
|---|---|---|
| `def` | `usr` (PK) | Function/method definitions |
| `source` | `usr` (PK) | Source text for each definition |
| `call` | `(caller_usr, callee_usr)` | Call edges |
| `class` | `(usr, parent_usr)` | Inheritance edges |
| `summary` | `usr` (PK) | LLM-generated summaries (populated separately) |
