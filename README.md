# TechDebtAssassin

[![CI](https://github.com/jchiru21/tech-debt-assassin/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/jchiru21/tech-debt-assassin/actions/workflows/ci.yml)

An autonomous AI agent that hunts down legacy Python code, injects missing type hints, and writes unit tests -- so you don't have to.

Powered by **Claude Opus 4.6** (global project awareness + type inference) and **Claude Sonnet 4.5** (precise test generation).

---

## What's New (Pro Features)

### Global Project Awareness (The Brain Upgrade)

The agent no longer fixes files in isolation. Before applying any type hints, it builds a **complete project context** -- file tree, class definitions, function signatures, and docstrings -- and feeds it to Claude Opus 4.6's 1M-token context window. This enables:

- **Cross-file type consistency** -- if `utils.py` defines `class User`, the agent uses `User` correctly in `main.py`
- **Smart mode switching** -- projects under 100k tokens get full source bodies injected; larger projects get intelligent summaries (signatures + docstrings only)
- **Graceful truncation** -- context is capped at 200k tokens to stay well within model limits

### MCP Server Integration (The Interface Upgrade)

TechDebtAssassin is now available as a **Model Context Protocol (MCP) server**, making it usable as a tool inside **Cursor**, **Claude Desktop**, **Windsurf**, or any MCP-compatible client.

- Exposes `scan_project` and `fix_file` as MCP tools over stdio transport
- Auto-detects project root by walking up to find `pyproject.toml`, `setup.py`, or `.git`
- Returns structured JSON results for easy consumption by AI clients

---

## Architecture

```
tech-debt-assassin/
├── main.py                # Typer CLI – five commands: scan, fix, gen-tests, verify, serve
├── src/
│   ├── scanner.py         # File discovery + AST parsing + global project context builder
│   ├── generator.py       # Produces type-hint patches and pytest test suites via Claude
│   ├── mcp_server.py      # MCP server exposing scan_project and fix_file tools
│   └── verifier.py        # Runs mypy and pytest on source files and generated tests
├── tests/
│   ├── test_scanner.py    # Unit tests for scanner module
│   ├── test_generator.py  # Unit tests for generator module
│   ├── test_verifier.py   # Unit tests for verifier module
│   └── generated/         # Auto-generated test files from gen-tests
├── demo/                  # Sample untyped Python files for testing the agent
│   ├── data_processor.py
│   ├── math_helpers.py
│   ├── string_utils.py
│   └── validators.py
├── messy_code.py          # Example file with missing type hints
├── messy_inventory.py     # Example inventory module for demo purposes
├── pyproject.toml         # Project metadata and dependencies
├── .github/workflows/
│   └── ci.yml             # GitHub Actions CI (ruff lint + pytest)
└── .env                   # ANTHROPIC_API_KEY (required)
```

### Pipeline

```
                        ┌─────────────────────────┐
                        │  build_project_context   │
                        │  (file tree + signatures │
                        │   + docstrings)          │
                        └───────────┬─────────────┘
                                    │
                                    ▼
scan ──> fix (with global context) / gen-tests ──> verify
                                    │
                        ┌───────────┴─────────────┐
                        │   Claude Opus 4.6 (1M)   │
                        │   cross-file type hints  │
                        └─────────────────────────┘
```

1. **Scanner** (`src/scanner.py`) -- Recursively collects `.py` files, parses them with Python's built-in `ast` module, and builds a list of `FunctionInfo` objects for every function/method that is missing type hints. Also includes `build_project_context()` which generates a global context string containing the file tree and per-file summaries (class names, function signatures, docstrings) or full source bodies for smaller projects.

2. **Generator** (`src/generator.py`) -- Calls the Anthropic API to produce two kinds of output:
   - **Type-hint patches** -- inferred type annotations applied directly to source files. When project context is provided, uses Claude Opus 4.6 with a cross-file-aware system prompt that ensures type consistency across the entire codebase.
   - **Test suites** -- complete `pytest` files with edge cases, generated per source file via Claude Sonnet 4.5.

3. **Verifier** (`src/verifier.py`) -- Validates correctness automatically:
   - Type check (`mypy --ignore-missing-imports`)
   - Test execution (`pytest`)

4. **MCP Server** (`src/mcp_server.py`) -- Exposes the agent as a Model Context Protocol server with two tools:
   - `scan_project(path)` -- scans a file or directory and returns JSON with all functions missing type hints
   - `fix_file(path)` -- applies AI-powered type hint fixes with full project awareness, auto-detecting the project root

---

## CLI Commands

The Assassin supports **Batch Mode** (single file OR directory) and **MCP Server Mode**.

```bash
python main.py scan [PATH]       # Scan a file or entire folder for missing hints
python main.py fix [PATH]        # Fix types with global project awareness
python main.py gen-tests [PATH]  # Generate tests for a file or entire folder
python main.py verify [PATH]     # Verify a file or entire folder
python main.py serve             # Start MCP server (stdio transport)
```

> **Note:** Directories like `.git`, `venv`, `node_modules`, and `__pycache__` are automatically excluded. Use `--exclude` to skip others.

---

## Quick Start

### CLI Usage

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Set your Anthropic API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# 3. Run the Assassin (Batch Mode with Global Context)
# Fix EVERY python file in the 'src' directory
python main.py fix src/

# Generate tests for the whole project
python main.py gen-tests src/

# Verify everything
python main.py verify src/

# Try it on the demo files
python main.py scan demo/
python main.py fix demo/
```

### MCP Server Usage

#### Start the server directly

```bash
python main.py serve
```

#### Configure in Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tech-debt-assassin": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["/absolute/path/to/tech-debt-assassin/main.py", "serve"]
    }
  }
}
```

#### Configure in Cursor

Add this to your `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "tech-debt-assassin": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["/absolute/path/to/tech-debt-assassin/main.py", "serve"]
    }
  }
}
```

Once configured, the AI assistant can call `scan_project` and `fix_file` as tools directly within the editor.

---

## How Global Context Works

When you run `python main.py fix <path>`, the agent:

1. **Scans the project** -- traverses the directory tree (respecting excludes) and collects all `.py` files.
2. **Estimates token budget** -- if the total source is under 100k tokens (~400k chars), it includes full file bodies in the context. Otherwise, it extracts only class names, function signatures, and docstrings.
3. **Builds the context string** -- a structured text block containing the file tree and per-file details.
4. **Passes to every LLM call** -- the same context is injected into the system prompt for every `infer_type_hints` call, so the model sees the entire codebase when deciding what types to apply.
5. **Uses Claude Opus 4.6** -- when project context is available, the agent upgrades from Sonnet to Opus for higher-quality cross-file inference.

---

## Dependencies

| Package        | Purpose                                                  |
|----------------|----------------------------------------------------------|
| typer          | CLI framework                                            |
| anthropic      | Anthropic API client (Claude Opus 4.6 / Sonnet 4.5)     |
| libcst         | Concrete syntax tree parsing and patching                |
| jinja2         | Template engine (reserved for future use)                |
| python-dotenv  | Load `.env` for API keys                                 |
| rich           | Terminal output formatting                               |
| mcp            | Model Context Protocol SDK for MCP server integration    |
| mypy           | Type-hint verification (dev)                             |
| pytest         | Test runner (dev)                                        |
| pytest-cov     | Test coverage (dev)                                      |
| ruff           | Linter / formatter (dev)                                 |

---

## Troubleshooting

| Problem                          | Solution                                                       |
|----------------------------------|----------------------------------------------------------------|
| `ModuleNotFoundError: anthropic` | Run `pip install anthropic` or `pip install -e ".[dev]"`       |
| `AuthenticationError`            | Check your `.env` file has a valid `ANTHROPIC_API_KEY`         |
| `404 model not found`            | Ensure you are using a current model ID (Claude 4.5/4.6)      |
| `ModuleNotFoundError` in tests   | Verify `pythonpath = ["."]` is set in `pyproject.toml`        |
| mypy reports `any` type errors   | Use `typing.Any` instead of the builtin `any` in annotations  |
| `ModuleNotFoundError: mcp`       | Run `pip install mcp` or `pip install -e .`                    |
| MCP `SyntaxError` in client      | Ensure `serve` command has no stdout prints (uses stderr only) |

---

## Future Roadmap

- [x] Batch mode -- process entire directories in a single command
- [x] Global project awareness -- cross-file type consistency via Opus 4.6's 1M context
- [x] MCP server integration -- use as a tool in Cursor, Claude Desktop, etc.
- [x] CI/CD integration -- GitHub Actions workflow (ruff lint + pytest on every push/PR)
- [ ] Confidence scoring -- flag low-confidence type inferences for human review
- [ ] Multi-language support -- extend scanning beyond Python

---

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m "Add my feature"`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.
