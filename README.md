# TechDebtAssassin

[![CI](https://github.com/jchiru21/tech-debt-assassin/actions/workflows/ci.yml/badge.svg)](https://github.com/jchiru21/tech-debt-assassin/actions/workflows/ci.yml)

An autonomous AI agent that hunts down legacy Python code, injects missing type hints, and writes unit tests -- so you don't have to.

Powered by **Claude 4.5 Haiku** (fast type inference) and **Claude 4.5 Sonnet** (precise test generation).

## Architecture

```
tech-debt-assassin/
├── main.py              # Typer CLI – four commands: scan, fix, gen-tests, verify
├── src/
│   ├── scanner.py       # File discovery + ast parsing (finds functions missing hints)
│   ├── generator.py     # Produces type-hint patches and pytest test suites via Claude
│   └── verifier.py      # Runs mypy and pytest on source files and generated tests
├── tests/
│   └── generated/       # Auto-generated test files from gen-tests
├── pyproject.toml       # Project metadata and dependencies
└── .env                 # ANTHROPIC_API_KEY (required)
```

### Pipeline

```
scan ──> fix / gen-tests ──> verify
```

1. **Scanner** (`src/scanner.py`) -- Recursively collects `.py` files, parses them with Python's built-in `ast` module, and builds a list of `FunctionInfo` objects for every function/method that is missing type hints.

2. **Generator** (`src/generator.py`) -- Calls the Anthropic API (no templates, raw LLM generation) to produce two kinds of output:
   - **Type-hint patches** -- inferred type annotations applied directly to source files.
   - **Test suites** -- complete `pytest` files with edge cases, generated per source file.

3. **Verifier** (`src/verifier.py`) -- Validates correctness automatically:
   - Type check (`mypy --ignore-missing-imports`)
   - Test execution (`pytest`)

### CLI Commands

The Assassin now supports **Batch Mode**. You can pass a single file OR a directory.

```bash
python main.py scan [PATH]       # Scan a file or entire folder for missing hints
python main.py fix [PATH]        # Fix types in a file or recursively in a folder
python main.py gen-tests [PATH]  # Generate tests for a file or entire folder
python main.py verify [PATH]     # Verify a file or entire folder
```

> **Note:** Directories like `.git`, `venv`, `node_modules`, and `__pycache__` are automatically excluded. Use `--exclude` to skip others.

## Quick Start

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Set your Anthropic API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# 3. Run the Assassin (Batch Mode)
# Fix EVERY python file in the 'src' directory
python main.py fix src/

# Generate tests for the whole project
python main.py gen-tests src/

# Verify everything
python main.py verify src/
```

## Dependencies

| Package        | Purpose                                      |
|----------------|----------------------------------------------|
| typer          | CLI framework                                |
| anthropic      | Anthropic API client (Claude 4.5)            |
| libcst         | Concrete syntax tree parsing and patching    |
| python-dotenv  | Load `.env` for API keys                     |
| rich           | Terminal output formatting                   |
| mypy           | Type-hint verification (dev)                 |
| pytest         | Test runner (dev)                            |
| pytest-cov     | Test coverage (dev)                          |
| ruff           | Linter / formatter (dev)                     |

## Troubleshooting

| Problem                          | Solution                                                       |
|----------------------------------|----------------------------------------------------------------|
| `ModuleNotFoundError: anthropic` | Run `pip install anthropic` or `pip install -e ".[dev]"`       |
| `AuthenticationError`            | Check your `.env` file has a valid `ANTHROPIC_API_KEY`         |
| `404 model not found`            | Ensure you are using a current model ID (Claude 4.5 family)   |
| `ModuleNotFoundError` in tests   | Verify `pythonpath = ["."]` is set in `pyproject.toml`         |
| mypy reports `any` type errors   | Use `typing.Any` instead of the builtin `any` in annotations  |

## Future Roadmap

- [x] Batch mode -- process entire directories in a single command
- [ ] Confidence scoring -- flag low-confidence type inferences for human review
- [x] CI/CD integration -- GitHub Actions workflow (lint + test on every push/PR)
- [ ] Multi-language support -- extend scanning beyond Python

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m "Add my feature"`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.
