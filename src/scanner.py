"""Scanner module – discovers Python files and identifies missing type hints."""

from __future__ import annotations

import ast
import builtins as _builtins
from dataclasses import dataclass, field
from pathlib import Path

# Names that are valid to use in type annotations: all Python builtins
# (int, float, str, list, dict, bool, …) plus common typing constructs.
_KNOWN_TYPE_NAMES = set(dir(_builtins)) | {
    "Any", "Optional", "Union", "List", "Dict", "Tuple", "Set",
    "FrozenSet", "Type", "Callable", "Iterator", "Generator",
    "Sequence", "Mapping", "Iterable", "Awaitable", "Coroutine",
    "ClassVar", "Final", "Literal", "TypeVar", "Protocol",
    "TypedDict", "NamedTuple", "NoReturn", "Never", "Self",
    "TypeAlias", "TypeGuard", "ParamSpec", "Concatenate",
}


def _is_valid_annotation(node: ast.expr) -> bool:
    """Check whether an annotation node is present and non-trivial.

    Accepts any syntactically valid annotation — builtins, typing constructs,
    and user-defined types (``Path``, ``FunctionInfo``, ``pd.DataFrame``, etc.).

    Only rejects single-name annotations that look like common typos of
    builtin types (e.g. ``foat``, ``stirng``, ``boool``).
    """
    # Common typo patterns: single lowercase name that's close to a builtin
    # but not an actual builtin or known type.  Multi-part annotations like
    # ``list[Path]`` or ``dict[str, Any]`` are always accepted because
    # subscripts imply intentional typing.
    if isinstance(node, ast.Name):
        name = node.id
        # Accept anything that starts with an uppercase letter (class names,
        # typing constructs) or is a known builtin/typing name.
        if name[0].isupper() or name in _KNOWN_TYPE_NAMES:
            return True
        # Reject bare lowercase names that aren't known — likely typos
        return False
    # Subscripts (list[X]), attributes (mod.Type), constants ("forward refs"),
    # BinOps (X | Y), etc. are all valid annotations.
    return True


@dataclass
class FunctionInfo:
    """Metadata about a single function/method found during scanning."""

    name: str
    file_path: Path
    line_number: int
    has_return_type: bool = False
    params_missing_hints: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    """Aggregated result of scanning a codebase."""

    files_scanned: int = 0
    functions: list[FunctionInfo] = field(default_factory=list)
    force: bool = False

    @property
    def functions_missing_hints(self) -> list[FunctionInfo]:
        """Return functions that need type-hint work.

        When *force* is True every discovered function is returned,
        allowing existing hints to be overwritten.
        """
        if self.force:
            return list(self.functions)
        return [
            f
            for f in self.functions
            if f.params_missing_hints or not f.has_return_type
        ]


_DEFAULT_EXCLUDE_DIRS = {"venv", ".venv", "node_modules", "__pycache__", ".git"}


def get_python_files(path: str, excluded_dirs: list[str] | None = None) -> list[Path]:
    """Resolve *path* to a list of ``.py`` files.

    - If *path* is a file, return ``[Path(path)]``.
    - If *path* is a directory, recursively find all ``.py`` files, skipping
      ``venv``, ``.git``, ``__pycache__``, and any directories listed in
      *excluded_dirs*.

    Returns resolved :class:`~pathlib.Path` objects sorted alphabetically.
    """
    target = Path(path).resolve()

    if target.is_file():
        if target.suffix != ".py":
            return []
        return [target]

    if not target.is_dir():
        return []

    skip = _DEFAULT_EXCLUDE_DIRS | set(excluded_dirs or [])
    files: list[Path] = []
    for child in sorted(target.rglob("*.py")):
        rel_parts = child.relative_to(target).parts
        if any(part in skip for part in rel_parts):
            continue
        files.append(child)
    return files


def collect_python_files(root: Path, exclude_dirs: set[str] | None = None) -> list[Path]:
    """Recursively collect all .py files under *root*, skipping *exclude_dirs*."""
    root = root.resolve()
    if root.is_file():
        return [root] if root.suffix == ".py" else []

    exclude = exclude_dirs or set()
    files: list[Path] = []
    for path in sorted(root.rglob("*.py")):
        if any(part in exclude for part in path.relative_to(root).parts):
            continue
        files.append(path)
    return files


def parse_function_signatures(file_path: Path) -> list[FunctionInfo]:
    """Parse a single Python file and return metadata for every function/method."""
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))

    results: list[FunctionInfo] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        missing_params: list[str] = []
        for arg in node.args.args:
            if arg.arg == "self" or arg.arg == "cls":
                continue
            if arg.annotation is None or not _is_valid_annotation(arg.annotation):
                missing_params.append(arg.arg)

        has_return = node.returns is not None and _is_valid_annotation(node.returns)

        results.append(
            FunctionInfo(
                name=node.name,
                file_path=file_path,
                line_number=node.lineno,
                has_return_type=has_return,
                params_missing_hints=missing_params,
            )
        )
    return results


def _build_file_tree(root: Path, py_files: list[Path]) -> str:
    """Build a textual file-tree representation of the project."""
    lines: list[str] = [f"{root.name}/"]
    for f in py_files:
        rel = f.relative_to(root)
        depth = len(rel.parts) - 1
        indent = "  " * depth + ("├── " if f != py_files[-1] else "└── ")
        lines.append(f"{indent}{rel}")
    return "\n".join(lines)


def _extract_file_summary(file_path: Path) -> str:
    """Extract class names, function signatures, and docstrings from a .py file."""
    try:
        source = file_path.read_text(encoding="utf-8")
    except Exception:
        return f"# {file_path.name}: (could not read)\n"

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return f"# {file_path.name}: (syntax error)\n"

    parts: list[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            parts.append(f"class {node.name}:")
            docstring = ast.get_docstring(node)
            if docstring:
                parts.append(f'    """{docstring}"""')
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    sig = ast.get_source_segment(source, item)
                    if sig:
                        def_line = sig.split("\n")[0]
                        parts.append(f"    {def_line}")
                    else:
                        parts.append(f"    def {item.name}(...):")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sig = ast.get_source_segment(source, node)
            if sig:
                parts.append(sig.split("\n")[0])
            else:
                parts.append(f"def {node.name}(...):")
            docstring = ast.get_docstring(node)
            if docstring:
                parts.append(f'    """{docstring}"""')

    return "\n".join(parts) if parts else "# (no classes or functions)"


# Token estimate: ~4 chars per token for English text
_CHARS_PER_TOKEN = 4
_MAX_CONTEXT_TOKENS = 200_000  # conservative limit for Opus 4.6's 1M window
_FULL_BODY_TOKEN_BUDGET = 100_000


def build_project_context(root_path: str, exclude_dirs: set[str] | None = None) -> str:
    """Build a global context string describing the entire project structure.

    Includes file tree and per-file summaries (class names, function signatures,
    docstrings). If the total project source is under 100k tokens, includes full
    file bodies instead of summaries. Truncates gracefully if too large.
    """
    root = Path(root_path).resolve()
    skip = (_DEFAULT_EXCLUDE_DIRS | (exclude_dirs or set())) | {"tests"}
    py_files = collect_python_files(root, exclude_dirs=skip)

    if not py_files:
        return "# Empty project — no Python files found."

    # Check total source size to decide full-body vs summary mode
    total_chars = 0
    file_sources: dict[Path, str] = {}
    for f in py_files:
        try:
            src = f.read_text(encoding="utf-8")
            file_sources[f] = src
            total_chars += len(src)
        except Exception:
            file_sources[f] = ""

    use_full_body = (total_chars // _CHARS_PER_TOKEN) < _FULL_BODY_TOKEN_BUDGET

    # Build the context
    sections: list[str] = []
    sections.append("=" * 60)
    sections.append("PROJECT STRUCTURE")
    sections.append("=" * 60)
    sections.append(_build_file_tree(root, py_files))
    sections.append("")

    sections.append("=" * 60)
    sections.append("FILE DETAILS")
    sections.append("=" * 60)

    for f in py_files:
        rel = f.relative_to(root)
        sections.append(f"\n--- {rel} ---")
        if use_full_body:
            sections.append(file_sources.get(f, "# (could not read)"))
        else:
            sections.append(_extract_file_summary(f))

    context = "\n".join(sections)

    # Truncate if exceeding max context budget
    max_chars = _MAX_CONTEXT_TOKENS * _CHARS_PER_TOKEN
    if len(context) > max_chars:
        context = context[:max_chars] + "\n\n... [TRUNCATED — project context exceeded token budget]"

    return context


def scan_codebase(root: Path, exclude_dirs: set[str] | None = None, force: bool = False) -> ScanResult:
    """Orchestrate a full scan: collect files, parse each, return aggregated results.

    When *force* is True every function is reported, even those that already
    have complete type hints, so that hints can be overwritten.
    """
    files = collect_python_files(root, exclude_dirs)
    result = ScanResult(files_scanned=len(files), force=force)
    for f in files:
        result.functions.extend(parse_function_signatures(f))
    return result
