"""MCP Server – exposes TechDebtAssassin as tools for Cursor, Claude Desktop, etc."""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from src.scanner import (
    build_project_context,
    collect_python_files,
    parse_function_signatures,
    scan_codebase,
)
from src.generator import apply_patches, generate_type_hint_patch, infer_type_hints

mcp = FastMCP(
    name="TechDebtAssassin",
    instructions=(
        "TechDebtAssassin: An AI agent that finds missing Python type hints "
        "and fixes them using cross-file project awareness."
    ),
)

_DEFAULT_EXCLUDE = {"venv", ".venv", "node_modules", "__pycache__", ".git", "tests"}


@mcp.tool()
def scan_project(path: str) -> str:
    """Scan a Python file or directory and return all functions missing type hints.

    Args:
        path: Path to a Python file or directory to scan.

    Returns:
        JSON string with scan results including file count and missing hints.
    """
    root = Path(path).resolve()
    result = scan_codebase(root, exclude_dirs=_DEFAULT_EXCLUDE)
    at_risk = result.functions_missing_hints

    findings = []
    for func in at_risk:
        findings.append({
            "file": str(func.file_path),
            "line": func.line_number,
            "function": func.name,
            "missing_params": func.params_missing_hints,
            "has_return_type": func.has_return_type,
        })

    return json.dumps({
        "files_scanned": result.files_scanned,
        "functions_at_risk": len(at_risk),
        "findings": findings,
    }, indent=2)


@mcp.tool()
def fix_file(path: str) -> str:
    """Fix missing type hints in a Python file using AI with full project awareness.

    Uses Claude with global project context to infer consistent, cross-file
    type annotations and applies them directly to the source file.

    Args:
        path: Path to the Python file to fix.

    Returns:
        JSON string summarizing which functions were fixed.
    """
    file_path = Path(path).resolve()
    if not file_path.is_file() or file_path.suffix != ".py":
        return json.dumps({"error": f"Not a valid Python file: {path}"})

    # Build project context from the file's parent directory
    project_root = file_path.parent
    # Walk up to find a likely project root (has pyproject.toml, setup.py, or .git)
    for parent in [file_path.parent, *file_path.parents]:
        if any((parent / marker).exists() for marker in ("pyproject.toml", "setup.py", ".git")):
            project_root = parent
            break

    project_context = build_project_context(str(project_root), exclude_dirs=_DEFAULT_EXCLUDE)

    result = scan_codebase(file_path, exclude_dirs=_DEFAULT_EXCLUDE)
    at_risk = result.functions_missing_hints

    if not at_risk:
        return json.dumps({"message": "No missing type hints found.", "fixed": []})

    fixed = []
    skipped = []

    for func in at_risk:
        hints = infer_type_hints(func, project_context=project_context)
        if hints is None:
            skipped.append(func.name)
            continue

        patch = generate_type_hint_patch(func, hints)
        modified_sources = apply_patches([patch], dry_run=False)
        patch.file_path.write_text(modified_sources[0])
        fixed.append({
            "function": func.name,
            "line": func.line_number,
            "hints": hints,
        })

    return json.dumps({
        "file": str(file_path),
        "fixed": fixed,
        "skipped": skipped,
    }, indent=2)


def run_server() -> None:
    """Start the MCP server using stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()
