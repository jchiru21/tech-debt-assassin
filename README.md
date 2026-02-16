# TechDebtAssassin

[![CI](https://github.com/jchiru21/tech-debt-assassin/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/jchiru21/tech-debt-assassin/actions/workflows/ci.yml)

An autonomous AI agent that scans a Python codebase, identifies missing type hints, patches them with cross-file accuracy, and verifies the results.

Powered by **Claude Opus 4.6** (global project context + type inference) and **Claude Sonnet 4.5** (test generation).

---

## How It Works

```
scan ──> fix (with global project context) ──> verify
  │               │                                │
  │       Claude Opus 4.6                    mypy + pytest
  │       sees entire project
  │                                                │
  └────────────── re-scan to confirm ◄─────────────┘
```

1. **Scan** -- Parses every `.py` file with Python's `ast` module and identifies functions missing type annotations.
2. **Fix** -- Builds a global project context (file tree, class definitions, function signatures) and sends it with each function to Claude Opus 4.6 for cross-file type inference. Patches are applied directly to source files.
3. **Verify** -- Runs `mypy` and `pytest` to confirm the patches are correct.

The global context means the model knows that `User` in `main.py` refers to the dataclass in `models.py` -- it doesn't guess `Any`.

---

## Quick Start

**Prerequisites:** Python 3.10+, an [Anthropic API key](https://console.anthropic.com)

```bash
git clone https://github.com/jchiru21/tech-debt-assassin.git
cd tech-debt-assassin
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

### CLI

```bash
python main.py scan demo/        # Scan for missing type hints
python main.py fix demo/         # Fix with Opus 4.6 + global context
python main.py gen-tests demo/   # Generate pytest test suites
python main.py verify demo/      # Verify with mypy + pytest
```

> `.git`, `venv`, `node_modules`, and `__pycache__` are excluded by default. Use `--exclude` to skip others.

### Streamlit Dashboard

```bash
streamlit run app.py
```

Open `http://localhost:8501`, enter a target path, click **Analyze Codebase**, then **Auto-Fix All Issues**. The dashboard streams progress in real time and re-scans automatically after fixing.

### MCP Server

```bash
python main.py serve
```

Exposes `scan_project` and `fix_file` as MCP tools over stdio. Add to Claude Desktop (`claude_desktop_config.json`) or Cursor (`.cursor/mcp.json`):

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

---

## Project Structure

```
tech-debt-assassin/
├── app.py                 # Streamlit dashboard
├── main.py                # Typer CLI (scan, fix, gen-tests, verify, serve)
├── src/
│   ├── scanner.py         # AST parsing + global project context builder
│   ├── generator.py       # Type-hint patches + test suites via Claude
│   ├── mcp_server.py      # MCP server (scan_project, fix_file)
│   └── verifier.py        # mypy + pytest verification
├── tests/
│   ├── test_scanner.py
│   ├── test_generator.py
│   ├── test_verifier.py
│   └── generated/         # Auto-generated test files
├── demo/                  # Sample Python files for testing
├── pyproject.toml
└── .github/workflows/
    └── ci.yml             # Ruff lint + pytest on every push
```

---

## Dependencies

| Package | Purpose |
|---|---|
| anthropic | Claude API client |
| typer | CLI framework |
| rich | Terminal formatting and progress bars |
| python-dotenv | `.env` loading |
| mcp | Model Context Protocol SDK |
| streamlit | Dashboard UI |
| pandas | Dashboard data display |
| mypy | Type checking (dev) |
| pytest | Test runner (dev) |
| ruff | Linter (dev) |

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: anthropic` | `pip install -e ".[dev]"` |
| `AuthenticationError` | Check `.env` has a valid `ANTHROPIC_API_KEY` |
| `ModuleNotFoundError: mcp` | `pip install mcp` |
| Auto-fix times out | Increase `_TIMEOUT_SECONDS` in `app.py` or target a smaller directory |

---

## License

MIT
