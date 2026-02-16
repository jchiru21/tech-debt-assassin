"""Generator module – produces type-hint patches and unit-test skeletons."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import anthropic

from src.scanner import FunctionInfo

TYPE_HINT_SYSTEM_PROMPT = (
    "You are a Python expert. Return ONLY the function signature with precise type hints.\n"
    "CRITICAL RULES:\n"
    "1. Use Python 3.10+ built-in types (list, dict, tuple) instead of the typing module.\n"
    "2. Use pipe syntax for Optionals (e.g., 'str | None' instead of 'Optional[str]').\n"
    "3. Do NOT use typing.List, typing.Dict, or typing.Optional.\n"
    "4. Return ONLY the def line. No markdown. No imports."
)

TYPE_HINT_SYSTEM_PROMPT_WITH_CONTEXT = (
    "You are a Python expert with access to the entire project context below. "
    "Use this to ensure type hints are consistent across files "
    "(e.g., if utils.py defines class User, use User correctly in main.py).\n\n"
    "Return ONLY the function signature with precise type hints.\n"
    "CRITICAL RULES:\n"
    "1. Use Python 3.10+ built-in types (list, dict, tuple) instead of the typing module.\n"
    "2. Use pipe syntax for Optionals (e.g., 'str | None' instead of 'Optional[str]').\n"
    "3. Do NOT use typing.List, typing.Dict, or typing.Optional.\n"
    "4. Return ONLY the def line. No markdown. No imports.\n"
    "5. Reference types from other project files when appropriate (e.g., custom classes, dataclasses).\n"
    "6. Be consistent with type patterns used elsewhere in the project."
)


@dataclass
class TypeHintPatch:
    """A proposed change that adds type hints to a function."""

    file_path: Path
    original_source: str
    patched_source: str


@dataclass
class TestCase:
    """A generated unit-test skeleton for a single function."""

    function_name: str
    source_file: Path
    test_code: str


# ── Type-hint generation ─────────────────────────────────────────────

def infer_type_hints(func: FunctionInfo, project_context: str | None) -> dict[str, str] | None:
    """Call the LLM to infer precise type hints for *func*.

    When *project_context* is provided, the LLM uses cross-file awareness
    to produce consistent, project-aware type annotations.

    Returns a mapping of param-name -> type string (plus ``"return"`` key),
    or ``None`` when inference fails.
    """
    # Extract the function source from the file
    source = func.file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(func.file_path))

    func_source = None
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name == func.name and node.lineno == func.line_number:
            func_source = ast.get_source_segment(source, node)
            break

    if func_source is None:
        return None

    # Build the prompt — with or without global context
    if project_context:
        system_prompt = (
            TYPE_HINT_SYSTEM_PROMPT_WITH_CONTEXT
            + "\n\n--- PROJECT CONTEXT ---\n"
            + project_context
        )
        model = "claude-opus-4-6"
    else:
        system_prompt = TYPE_HINT_SYSTEM_PROMPT
        model = "claude-sonnet-4-5-20250929"

    user_msg = f"Add type hints to this function from {func.file_path.name}:\n\n{func_source}"

    # Ask the LLM for a typed signature
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=256,
            system=system_prompt,
            messages=[{"role": "user", "content": user_msg}],
            temperature=0,
        )
        signature_line = response.content[0].text.strip()
    except Exception:
        return None

    # Strip markdown fences and extract only the def line
    if signature_line.startswith("```"):
        lines = signature_line.splitlines()
        lines = [line for line in lines if not line.startswith("```")]
        signature_line = lines[0].strip() if lines else signature_line

    # If the LLM returned a full function body, keep only the def line
    for line in signature_line.splitlines():
        stripped = line.strip()
        if stripped.startswith("def ") or stripped.startswith("async def "):
            signature_line = stripped
            break

    # Parse the returned signature to extract hints
    try:
        stub = signature_line if signature_line.endswith(":") else signature_line + ":"
        stub += "\n    pass"
        parsed = ast.parse(stub)
        func_node = parsed.body[0]

        hints: dict[str, str] = {}
        for arg in func_node.args.args:
            if arg.arg in ("self", "cls"):
                continue
            if arg.annotation is not None:
                hints[arg.arg] = ast.unparse(arg.annotation)
        if func_node.returns is not None:
            hints["return"] = ast.unparse(func_node.returns)

        return hints
    except Exception:
        return None


def generate_type_hint_patch(func: FunctionInfo, hints: dict[str, str]) -> TypeHintPatch:
    """Build a full source-level patch that inserts the inferred type hints."""
    source = func.file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(func.file_path))

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != func.name or node.lineno != func.line_number:
            continue

        # Build new parameter list
        new_params = []
        for arg in node.args.args:
            if arg.arg in ("self", "cls"):
                new_params.append(arg.arg)
            elif arg.arg in hints:
                new_params.append(f"{arg.arg}: {hints[arg.arg]}")
            elif arg.annotation is not None:
                new_params.append(f"{arg.arg}: {ast.unparse(arg.annotation)}")
            else:
                new_params.append(arg.arg)

        # Build return annotation
        return_hint = ""
        if "return" in hints:
            return_hint = f" -> {hints['return']}"
        elif node.returns is not None:
            return_hint = f" -> {ast.unparse(node.returns)}"

        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        new_def = f"{prefix} {node.name}({', '.join(new_params)}){return_hint}:"

        # Find the original def lines (may span multiple lines)
        lines = source.splitlines(keepends=True)
        start_idx = node.lineno - 1
        end_idx = start_idx
        paren_depth = 0
        found_colon = False
        for i in range(start_idx, len(lines)):
            for ch in lines[i]:
                if ch == '(':
                    paren_depth += 1
                elif ch == ')':
                    paren_depth -= 1
                elif ch == ':' and paren_depth == 0:
                    found_colon = True
                    break
            if found_colon:
                end_idx = i
                break

        indent = lines[start_idx][: len(lines[start_idx]) - len(lines[start_idx].lstrip())]
        new_lines = lines[:start_idx] + [f"{indent}{new_def}\n"] + lines[end_idx + 1:]
        patched_source = "".join(new_lines)

        return TypeHintPatch(
            file_path=func.file_path,
            original_source=source,
            patched_source=patched_source,
        )

    # Function not found — return unchanged source
    return TypeHintPatch(
        file_path=func.file_path,
        original_source=source,
        patched_source=source,
    )


def apply_patches(patches: list[TypeHintPatch], dry_run: bool) -> list[str]:
    """Apply patches and return the modified source code strings.

    Returns the list of patched source code strings.
    """
    return [patch.patched_source for patch in patches]


# ── Unit-test generation ─────────────────────────────────────────────

def generate_test_case(func: FunctionInfo) -> TestCase:
    """Create a pytest-style test skeleton for a single function."""
    pass


def generate_test_suite(source_code: str, filename: str) -> str:
    """Use the LLM to generate a complete pytest file for the provided source code."""
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        system=(
            "You are a QA Engineer. Write a complete pytest file for the provided code. "
            "Include edge cases. Return ONLY the raw python code (no markdown fences). "
            "Use standard pytest fixtures if needed."
        ),
        messages=[
            {"role": "user", "content": f"Here is the code for {filename}:\n\n{source_code}"},
        ],
    )
    clean_code = response.content[0].text
    if clean_code.startswith("```python"):
        clean_code = clean_code.split("\n", 1)[1]
    if clean_code.startswith("```"):
        clean_code = clean_code.split("\n", 1)[1]
    if clean_code.endswith("```"):
        clean_code = clean_code[: -len("```")]
    return clean_code
