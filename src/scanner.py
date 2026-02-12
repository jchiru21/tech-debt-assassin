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
    """Heuristically check whether an annotation uses known type names.

    Walks the annotation AST and verifies every bare name (``ast.Name``)
    appears in ``_KNOWN_TYPE_NAMES``.  This catches typos like ``foat``
    or ``lst`` that are syntactically valid but not real types.
    """
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id not in _KNOWN_TYPE_NAMES:
            return False
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


def scan_codebase(
    root: Path,
    exclude_dirs: set[str] | None = None,
    force: bool = False,
) -> ScanResult:
    """Orchestrate a full scan: collect files, parse each, return aggregated results.

    When *force* is True every function is reported, even those that already
    have complete type hints, so that hints can be overwritten.
    """
    files = collect_python_files(root, exclude_dirs)
    result = ScanResult(files_scanned=len(files), force=force)
    for f in files:
        result.functions.extend(parse_function_signatures(f))
    return result
