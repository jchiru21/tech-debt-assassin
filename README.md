# TechDebtAssassin

[![CI](https://github.com/jchiru21/tech-debt-assassin/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/jchiru21/tech-debt-assassin/actions/workflows/ci.yml)

> **Built with Claude Opus 4.6** | Hackathon Track: *Eliminating Busywork*

An **autonomous AI agent** that scans an entire Python codebase, identifies missing type hints, patches them with cross-file accuracy, and verifies the results -- without a single user prompt per function.

---

## Problem Statement

> *"Eliminating Busywork -- Build agents that handle tedious tasks so developers can focus on creative problem-solving."*

Adding type hints to a legacy Python codebase is one of the most dreaded maintenance tasks in software engineering. It's mechanical, error-prone, and scales linearly with project size. A 100-file project can have hundreds of untyped functions, and each one requires the developer to:

1. Read the function body to understand the data flow
2. Trace imports and class definitions across files for custom types
3. Write the annotations, run mypy, fix mistakes, repeat

This is the exact kind of busywork that should be automated. TechDebtAssassin does all three steps autonomously -- for every function in a project -- in a single command.

---

## Project Vision: Agent, Not Assistant

TechDebtAssassin is not a chatbot that waits for you to ask. It is a **goal-driven autonomous agent** with a closed-loop pipeline:

```
 Point at a directory
        |
        v
  +-----------+      +------------------+      +------------+
  |   SCAN    | ---> |   FIX (Claude    | ---> |   VERIFY   |
  | AST parse |      |   Opus 4.6 +    |      |   mypy +   |
  | all files |      |   global ctx)    |      |   pytest   |
  +-----------+      +------------------+      +------------+
        ^                                            |
        |____________________________________________|
                     re-scan to confirm
```

You give it a folder. It scans every `.py` file, builds a global project context, calls Claude Opus 4.6 to infer type hints with cross-file awareness, patches the source files, and re-scans to confirm the fixes. The developer is not in the loop.

### TechDebtAssassin vs. Coding Assistants

| Capability | VS Code Copilot / Cursor | TechDebtAssassin |
|---|---|---|
| **User input** | You prompt for every change | Give it a folder and walk away |
| **Scope** | Current file + open tabs | Entire project via global context |
| **Context** | ~8K-32K tokens of local code | Up to 200K tokens of project-wide structure, signatures, and source |
| **Specialization** | General-purpose code completion | Hyper-focused on technical debt elimination |
| **Verification** | Developer checks manually | Built-in Scan -> Fix -> Verify loop |
| **Integration** | Editor plugin | CLI, Streamlit dashboard, MCP server |
| **Opus 4.6 usage** | N/A | Every type inference call uses Opus 4.6 with full project context |

---

## Architecture

```
tech-debt-assassin/
├── app.py                 # Streamlit dashboard – visual scan, metrics, one-click auto-fix
├── main.py                # Typer CLI – commands: scan, fix, gen-tests, verify, serve
├── src/
│   ├── scanner.py         # File discovery + AST parsing + global project context builder
│   ├── generator.py       # Type-hint patches + pytest suites via Claude Opus 4.6
│   ├── mcp_server.py      # MCP server exposing scan_project and fix_file tools
│   └── verifier.py        # Runs mypy and pytest for automated verification
├── tests/
│   ├── test_scanner.py    # Unit tests for scanner module
│   ├── test_generator.py  # Unit tests for generator module
│   ├── test_verifier.py   # Unit tests for verifier module
│   └── generated/         # Auto-generated test files from gen-tests
├── demo/                  # Sample Python files for live demo
│   ├── api_helpers.py
│   ├── data_processor.py
│   ├── math_helpers.py
│   ├── string_utils.py
│   └── validators.py
├── messy_code.py          # Example file with missing type hints
├── messy_inventory.py     # Example inventory module for demo
├── pyproject.toml         # Project metadata and dependencies
└── .github/workflows/
    └── ci.yml             # GitHub Actions CI (ruff lint + pytest)
```

### Pipeline Detail

1. **Scanner** (`src/scanner.py`) -- Recursively collects `.py` files, parses them with Python's `ast` module, and identifies every function missing type annotations. Also builds a **global project context**: file tree, class definitions, function signatures, and docstrings -- fed to every LLM call for cross-file accuracy.

2. **Generator** (`src/generator.py`) -- Calls the Anthropic API to produce:
   - **Type-hint patches** -- inferred annotations applied directly to source files. Uses **Claude Opus 4.6** with the full project context so it knows that `User` in `main.py` refers to the dataclass in `models.py`.
   - **Test suites** -- complete `pytest` files with edge cases, generated per source file via Claude Sonnet 4.5.

3. **Verifier** (`src/verifier.py`) -- Validates correctness automatically:
   - Syntax check (`py_compile`)
   - Type check (`mypy --ignore-missing-imports`)
   - Test execution (`pytest`)

4. **MCP Server** (`src/mcp_server.py`) -- Exposes the agent as a **Model Context Protocol** server with two tools:
   - `scan_project(path)` -- scans a file or directory, returns JSON with all functions missing type hints
   - `fix_file(path)` -- applies AI-powered type hint fixes with full project awareness, auto-detecting the project root

5. **Streamlit Dashboard** (`app.py`) -- Visual interface for live demos:
   - One-click codebase analysis with real-time metrics
   - Issues table with per-function detail (missing params, missing returns)
   - Auto-fix button with **live streaming progress** (function-by-function feedback)
   - Automatic re-scan after fix to show Red -> Green transition

---

## How Opus 4.6 Is Used

Every type inference call goes through Claude Opus 4.6 with the **full project context** injected into the system prompt. This is not a generic "add type hints" prompt -- it is a project-aware inference engine.

**Without global context** (what Copilot does):
```python
# Copilot sees only this file -- guesses "Any" for unknown types
def process(data, handler):  # -> ???
```

**With global context** (what TechDebtAssassin does):
```python
# Agent sees that 'data' comes from DataProcessor.load() which returns pd.DataFrame,
# and 'handler' is always an instance of EventHandler from events.py
def process(data: pd.DataFrame, handler: EventHandler) -> dict[str, int]:
```

The system prompt includes:
- Complete file tree of the project
- All class definitions, function signatures, and docstrings
- Full source bodies for projects under 100K tokens
- Intelligent summaries (signatures only) for larger projects

This context is capped at 200K tokens to stay within model limits, with graceful truncation.

---

## Quick Start

### Prerequisites

- Python 3.10+
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

### Installation

```bash
# Clone the repository
git clone https://github.com/jchiru21/tech-debt-assassin.git
cd tech-debt-assassin

# Create a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Set your API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

### CLI Usage

```bash
# Scan a directory for missing type hints
python main.py scan demo/

# Fix all missing type hints (uses Opus 4.6 with global context)
python main.py fix demo/

# Generate pytest test suites
python main.py gen-tests demo/

# Verify with mypy + pytest
python main.py verify demo/
```

### Streamlit Dashboard

```bash
# Launch the visual dashboard
streamlit run app.py

# Then open http://localhost:8501 in your browser
# 1. Enter a target path (defaults to demo/)
# 2. Click "Analyze Codebase"
# 3. Review the issues table and metrics
# 4. Click "Auto-Fix All Issues" and watch live progress
```

### MCP Server

```bash
# Start the MCP server (stdio transport)
python main.py serve
```

**Claude Desktop** -- add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "tech-debt-assassin": {
      "command": "/path/to/venv/bin/python",
      "args": ["/absolute/path/to/tech-debt-assassin/main.py", "serve"]
    }
  }
}
```

**Cursor** -- add to `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "tech-debt-assassin": {
      "command": "/path/to/venv/bin/python",
      "args": ["/absolute/path/to/tech-debt-assassin/main.py", "serve"]
    }
  }
}
```

Once configured, the AI assistant can call `scan_project` and `fix_file` as tools directly within the editor.

---

## CLI Commands

```bash
python main.py scan [PATH]       # Scan for missing type hints
python main.py fix [PATH]        # Fix with global project awareness (Opus 4.6)
python main.py gen-tests [PATH]  # Generate pytest test suites (Sonnet 4.5)
python main.py verify [PATH]     # Verify with mypy + pytest
python main.py serve             # Start MCP server (stdio transport)
```

> Directories like `.git`, `venv`, `node_modules`, and `__pycache__` are automatically excluded. Use `--exclude` to skip additional directories.

---

## Dependencies

| Package | Purpose |
|---|---|
| anthropic | Anthropic API client (Claude Opus 4.6 / Sonnet 4.5) |
| typer | CLI framework |
| rich | Terminal output formatting and progress bars |
| python-dotenv | Load `.env` for API keys |
| mcp | Model Context Protocol SDK for MCP server |
| libcst | Concrete syntax tree parsing and patching |
| streamlit | Visual dashboard for demos |
| pandas | Data display in dashboard tables |
| mypy | Type-hint verification (dev) |
| pytest | Test runner (dev) |
| ruff | Linter and formatter (dev) |

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: anthropic` | Run `pip install anthropic` or `pip install -e ".[dev]"` |
| `AuthenticationError` | Check your `.env` file has a valid `ANTHROPIC_API_KEY` |
| `404 model not found` | Ensure you are using a current model ID (Claude Opus 4.6 / Sonnet 4.5) |
| `ModuleNotFoundError` in tests | Verify `pythonpath = ["."]` is set in `pyproject.toml` |
| `ModuleNotFoundError: mcp` | Run `pip install mcp` or `pip install -e .` |
| MCP `SyntaxError` in client | Ensure `serve` command has no stdout prints (uses stderr only) |
| Auto-fix times out | Increase `_TIMEOUT_SECONDS` in `app.py` or target a smaller directory |

---

## Roadmap

- [x] Batch mode -- process entire directories in a single command
- [x] Global project awareness -- cross-file type consistency via Opus 4.6
- [x] MCP server integration -- use as a tool in Cursor, Claude Desktop, etc.
- [x] Streamlit dashboard -- visual metrics, one-click fix, live progress streaming
- [x] CI/CD integration -- GitHub Actions workflow (ruff lint + pytest)
- [ ] Confidence scoring -- flag low-confidence inferences for human review
- [ ] Multi-language support -- extend scanning beyond Python

---

## License

This project is licensed under the MIT License.
