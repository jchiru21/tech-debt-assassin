"""Verifier module – validates generated patches and tests before committing them."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from src.generator import TestCase, TypeHintPatch


@dataclass
class VerificationResult:
    """Outcome of verifying a single patch or test file."""

    path: Path
    passed: bool
    errors: list[str]


def run_pytest(test_file: str) -> bool:
    """Run pytest on *test_file* and return True if all tests pass."""
    result = subprocess.run(
        ["pytest", test_file],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def run_mypy(source_file: str) -> bool:
    """Run mypy on *source_file* and return True if no type errors are found."""
    result = subprocess.run(
        ["mypy", source_file, "--ignore-missing-imports"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def verify_syntax(file_path: Path) -> VerificationResult:
    """Check that a Python file is syntactically valid (compile check)."""
    pass


def verify_type_hints(file_path: Path) -> VerificationResult:
    """Run mypy on a single file and report any type errors."""
    pass


def verify_tests(test_file: Path) -> VerificationResult:
    """Execute a test file with pytest and report pass/fail."""
    pass


def verify_all(
    patches: list[TypeHintPatch],
    test_cases: list[TestCase],
) -> list[VerificationResult]:
    """Run the full verification pipeline over all generated artefacts."""
    pass
