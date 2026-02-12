"""Tests for src.generator."""

from pathlib import Path

from src.scanner import FunctionInfo
from src.generator import generate_type_hint_patch, apply_patches, TypeHintPatch


def _sample_func(tmp_file: Path) -> FunctionInfo:
    return FunctionInfo(
        name="add",
        file_path=tmp_file,
        line_number=1,
        has_return_type=False,
        params_missing_hints=["a", "b"],
    )


def test_generate_type_hint_patch_applies_hints(tmp_path: Path) -> None:
    src = tmp_path / "math_utils.py"
    src.write_text("def add(a, b):\n    return a + b\n")

    func = _sample_func(src)
    hints = {"a": "int", "b": "int", "return": "int"}
    patch = generate_type_hint_patch(func, hints)

    assert "a: int" in patch.patched_source
    assert "b: int" in patch.patched_source
    assert "-> int" in patch.patched_source


def test_apply_patches_returns_patched_sources() -> None:
    patch = TypeHintPatch(
        file_path=Path("dummy.py"),
        original_source="def foo(x): pass\n",
        patched_source="def foo(x: int) -> None: pass\n",
    )
    results = apply_patches([patch], dry_run=False)
    assert len(results) == 1
    assert "x: int" in results[0]


def test_generate_type_hint_patch_no_match(tmp_path: Path) -> None:
    """When the function isn't found, source is returned unchanged."""
    src = tmp_path / "other.py"
    src.write_text("def other_func(x):\n    pass\n")

    func = FunctionInfo(
        name="nonexistent",
        file_path=src,
        line_number=99,
        has_return_type=False,
        params_missing_hints=["x"],
    )
    hints = {"x": "str"}
    patch = generate_type_hint_patch(func, hints)
    assert patch.patched_source == patch.original_source
