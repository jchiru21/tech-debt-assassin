# Architecture

This document describes how TechDebtAssassin works under the hood -- the interaction between the Streamlit frontend, Python backend, Claude Opus 4.6, and the Model Context Protocol server.

---

## System Overview

```
                         ┌──────────────────────────────┐
                         │      User Entry Points        │
                         │                                │
                         │  CLI (main.py)                 │
                         │  Streamlit Dashboard (app.py)  │
                         │  MCP Server (mcp_server.py)    │
                         └──────────┬───────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    v               v               v
             ┌──────────┐   ┌──────────┐   ┌──────────────┐
             │ Scanner   │   │Generator │   │  Verifier    │
             │           │   │          │   │              │
             │ AST parse │   │ Claude   │   │ mypy         │
             │ file tree │   │ Opus 4.6 │   │ pytest       │
             │ context   │   │ patches  │   │ py_compile   │
             └──────────┘   └──────────┘   └──────────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    │
                                    v
                            Source files on disk
```

All three entry points (CLI, Dashboard, MCP) share the same backend modules. The pipeline is always: **Scan -> Fix -> Verify**.

---

## Core Modules

### Scanner (`src/scanner.py`)

The scanner has two responsibilities:

**1. Function discovery** -- Parses every `.py` file using Python's `ast` module. For each `FunctionDef` and `AsyncFunctionDef` node, it checks:
- Does each parameter have an annotation?
- Is the annotation a valid type (not a typo like `foat`)?
- Is there a return type annotation?

The result is a list of `FunctionInfo` dataclass objects with the function name, file path, line number, and which hints are missing.

**2. Global project context** -- `build_project_context()` constructs a structured text representation of the entire codebase:

```
============================================================
PROJECT STRUCTURE
============================================================
my-project/
├── models.py
├── services.py
└── utils.py

============================================================
FILE DETAILS
============================================================

--- models.py ---
class User:
    """Represents an application user."""
    def __init__(self, name: str, email: str):
    def to_dict(self) -> dict:

--- services.py ---
def create_user(name, email):
    """Create a new user and persist to database."""
...
```

This context is sent with every LLM call so Claude can see cross-file relationships.

**Token budget strategy:**
- Projects under 100K tokens (~400K chars): full source bodies included
- Larger projects: only class names, function signatures, and docstrings
- Hard cap at 200K tokens with graceful truncation

### Generator (`src/generator.py`)

The generator makes one Claude API call per function that needs fixing. Each call includes:

- **System prompt**: Instructions for generating type hints using Python 3.10+ syntax (`list[str]` not `List[str]`, `str | None` not `Optional[str]`)
- **Project context**: The full output of `build_project_context()`, injected into the system prompt
- **User message**: The function's source code from the file

**Model selection:**
- With project context: **Claude Opus 4.6** -- the strongest model for complex cross-file reasoning
- Without project context: **Claude Sonnet 4.5** -- faster, used for isolated single-file fixes

The response is parsed back through `ast.parse` to extract individual parameter types and return types, then assembled into a `TypeHintPatch` that rewrites the `def` line in the source file.

**Why Opus 4.6 matters here:**

Type inference across files is a reasoning-heavy task. The model must:
1. Read the project context to understand custom types, class hierarchies, and data flow
2. Trace how a function's parameters are used in the body
3. Match parameter types against types defined in other files
4. Produce annotations that are consistent with the rest of the codebase

This requires the deep reasoning capabilities of Opus 4.6. Smaller models tend to fall back to `Any` or produce inconsistent types across files.

### Verifier (`src/verifier.py`)

After patches are applied, the verifier confirms correctness:

- **Syntax check** (`py_compile`): Ensures the patched file still parses
- **Type check** (`mypy --ignore-missing-imports`): Validates that the new annotations are consistent
- **Test execution** (`pytest`): Runs any generated test suites

This closes the loop -- the agent doesn't just generate patches, it validates them.

---

## The Self-Healing Loop

The core differentiator is the closed-loop pipeline. Here's the exact flow when a user clicks "Auto-Fix All Issues" in the Streamlit dashboard:

```
1. User clicks "Auto-Fix"
           │
           v
2. app.py spawns: subprocess.Popen(["python", "main.py", "fix", path])
           │
           v
3. main.py fix command:
   a. build_project_context(path)  → full project context string
   b. scan_codebase(path)          → list of FunctionInfo objects
   c. For each function missing hints:
      i.   infer_type_hints(func, project_context)  → Claude Opus 4.6 API call
      ii.  generate_type_hint_patch(func, hints)     → AST-level source rewrite
      iii. Write patched source to disk
   d. Print progress ("Fixed 'func_name' in file:line")
           │
           v
4. app.py reads stdout line-by-line, updates st.status:
   "Fixing 12/46 — 8 fixed, 4 skipped"
           │
           v
5. On completion:
   a. run_analysis()  → re-scan with force=False
   b. st.rerun()      → dashboard refreshes with new metrics
           │
           v
6. Dashboard shows updated health (e.g., 35% → 100%)
   If 100%: balloons + green "Codebase is Clean!" banner
```

The re-scan in step 5 is critical. It proves the fixes are real by re-parsing the files from disk. If a fix produced invalid syntax or the annotation was rejected, it would still show as missing.

---

## Streamlit Frontend (`app.py`)

The dashboard is organized into sections:

**Session state management:**
- `scan_results`: The `ScanResult` object from the last scan
- `scanned_path`: Which directory was scanned (clears stale results on path change)
- `celebrate`: One-shot flag for balloons animation after a successful fix

**Metrics computation:**
```python
total_funcs = len(res.functions)
missing_funcs = [f for f in res.functions
                 if f.params_missing_hints or not f.has_return_type]
health = int(((total_funcs - len(missing_funcs)) / total_funcs) * 100)
```

Missing functions are computed directly from `FunctionInfo` fields, not from the `functions_missing_hints` property. This ensures accuracy regardless of the `force` flag used during scanning.

**Live progress streaming:**
The auto-fix engine uses `subprocess.Popen` (not `subprocess.run`) to stream `main.py fix` output line-by-line. Environment variables `PYTHONUNBUFFERED=1`, `NO_COLOR=1`, and `TERM=dumb` ensure immediate, clean text output. Each line is parsed for "Fixed", "Skipping", or "Error" keywords to update the progress counter in real time.

---

## MCP Server (`src/mcp_server.py`)

The MCP server exposes the agent as tools that any MCP-compatible client (Cursor, Claude Desktop, Windsurf) can call:

| Tool | Description |
|---|---|
| `scan_project(path)` | Scan a file or directory, return JSON with all functions missing hints |
| `fix_file(path)` | Fix a single file with full project context awareness |

**Project root detection:** When `fix_file` is called on a single file, the server walks up the directory tree to find `pyproject.toml`, `setup.py`, or `.git` to determine the project root. This ensures the global context covers the full project, not just the file being fixed.

**Transport:** stdio (standard input/output), the default for local MCP servers.

---

## Data Flow Summary

```
User input (path)
     │
     ▼
collect_python_files()        # Recursively find .py files
     │
     ▼
parse_function_signatures()   # AST parse each file → FunctionInfo[]
     │
     ▼
build_project_context()       # File tree + source/summaries → string
     │
     ▼
infer_type_hints()            # Claude Opus 4.6 API call per function
     │                         #   system: context + instructions
     ▼                         #   user: function source
generate_type_hint_patch()    # Build patched source via AST rewrite
     │
     ▼
file.write_text(patched)      # Write to disk
     │
     ▼
run_mypy() / run_pytest()     # Verify correctness
```

Every step is deterministic and auditable except the LLM call, which is why the verification step exists -- the agent does not trust its own output.
