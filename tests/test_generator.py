"""Tests for src.generator."""

from pathlib import Path

from src.scanner import FunctionInfo, ScanResult
from src.generator import infer_type_hints, generate_test_case, generate_test_suite


def _sample_func() -> FunctionInfo:
    return FunctionInfo(
        name="add",
        file_path=Path("math_utils.py"),
        line_number=10,
        has_return_type=False,
        params_missing_hints=["a", "b"],
    )


def test_infer_type_hints_returns_dict() -> None:
    hints = infer_type_hints(_sample_func())
    assert isinstance(hints, dict)


def test_generate_test_case_produces_code() -> None:
    tc = generate_test_case(_sample_func())
    assert "def test_" in tc.test_code


def test_generate_test_suite_creates_files(tmp_path: Path) -> None:
    scan = ScanResult(files_scanned=1, functions=[_sample_func()])
    created = generate_test_suite(scan, output_dir=tmp_path)
    assert isinstance(created, list)
