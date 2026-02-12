"""Tests for src.verifier."""

from pathlib import Path

from src.verifier import verify_syntax


def test_verify_syntax_valid_file(tmp_path: Path) -> None:
    f = tmp_path / "ok.py"
    f.write_text("x: int = 1\n")
    result = verify_syntax(f)
    assert result.passed


def test_verify_syntax_invalid_file(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("def broken(\n")
    result = verify_syntax(f)
    assert not result.passed
