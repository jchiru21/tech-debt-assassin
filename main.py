"""TechDebtAssassin – CLI entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, MofNCompleteColumn
from rich.table import Table

from src.scanner import get_python_files, scan_codebase
from src.generator import apply_patches, generate_test_suite, generate_type_hint_patch, infer_type_hints
from src.verifier import run_mypy, run_pytest

load_dotenv()

app = typer.Typer(
    name="tech-debt-assassin",
    help="Scan a codebase to add missing type hints and generate unit tests.",
    add_completion=False,
)
console = Console()

DEFAULT_EXCLUDE = {"venv", ".venv", "node_modules", "__pycache__", ".git"}


@app.command()
def scan(
    root: Path = typer.Argument(Path("."), help="Root directory to scan."),
    exclude: Optional[list[str]] = typer.Option(None, "--exclude", "-e", help="Directories to skip."),
    force: bool = typer.Option(False, "--force", help="Include functions that already have type hints."),
) -> None:
    """Scan the codebase and report functions missing type hints."""
    exclude_dirs = DEFAULT_EXCLUDE | set(exclude or [])
    result = scan_codebase(root, exclude_dirs=exclude_dirs, force=force)

    at_risk = result.functions_missing_hints
    console.print(f"[bold]Scanned {result.files_scanned} file(s) — {len(at_risk)} function(s) at risk[/bold]\n")

    if not at_risk:
        console.print("[green]No missing type hints found![/green]")
        return

    table = Table(title="Functions Missing Type Hints")
    table.add_column("File", style="cyan")
    table.add_column("Line", justify="right", style="magenta")
    table.add_column("Function", style="yellow")
    table.add_column("Missing Params", style="red")
    table.add_column("Return Type?", justify="center")

    for func in at_risk:
        missing = ", ".join(func.params_missing_hints) if func.params_missing_hints else "-"
        ret = "[green]yes[/green]" if func.has_return_type else "[red]no[/red]"
        table.add_row(str(func.file_path), str(func.line_number), func.name, missing, ret)

    console.print(table)


@app.command()
def fix(
    path: str = typer.Argument(..., help="Python file or directory to fix."),
    exclude: Optional[list[str]] = typer.Option(None, "--exclude", "-e", help="Directories to skip."),
    force: bool = typer.Option(False, "--force", help="Re-infer and overwrite existing type hints."),
) -> None:
    """Fix missing type hints in a file or every .py file in a directory."""
    files = get_python_files(path, excluded_dirs=exclude)
    if not files:
        console.print("[yellow]No Python files found.[/yellow]")
        return

    exclude_dirs = DEFAULT_EXCLUDE | set(exclude or [])
    succeeded, failed = 0, 0
    errors: list[tuple[Path, str]] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Fixing files...", total=len(files))

        for file in files:
            progress.update(task, description=f"Fixing {file.name}")
            try:
                result = scan_codebase(file, exclude_dirs=exclude_dirs, force=force)
                at_risk = result.functions_missing_hints
                if not at_risk:
                    succeeded += 1
                    progress.advance(task)
                    continue

                for func in at_risk:
                    hints = infer_type_hints(func)
                    if hints is None:
                        console.print(
                            f"  [yellow]Skipping '{func.name}' in {file} — could not infer[/yellow]"
                        )
                        continue
                    patch = generate_type_hint_patch(func, hints)
                    modified_sources = apply_patches([patch], dry_run=False)
                    patch.file_path.write_text(modified_sources[0])
                    console.print(
                        f"  [green]Fixed '{func.name}' in {func.file_path}:{func.line_number}[/green]"
                    )
                succeeded += 1
            except Exception as exc:
                failed += 1
                errors.append((file, str(exc)))
                console.print(f"  [red]Error processing {file}: {exc}[/red]")
            progress.advance(task)

    _print_summary("Fixed", succeeded, failed, errors)


@app.command()
def gen_tests(
    path: str = typer.Argument(..., help="Python file or directory to generate tests for."),
    exclude: Optional[list[str]] = typer.Option(None, "--exclude", "-e", help="Directories to skip."),
) -> None:
    """Generate pytest test suites for a file or every .py file in a directory."""
    files = get_python_files(path, excluded_dirs=exclude)
    if not files:
        console.print("[yellow]No Python files found.[/yellow]")
        return

    output_dir = Path("tests/generated")
    output_dir.mkdir(parents=True, exist_ok=True)

    succeeded, failed = 0, 0
    errors: list[tuple[Path, str]] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Generating tests...", total=len(files))

        for file in files:
            progress.update(task, description=f"Generating tests for {file.name}")
            try:
                source_code = file.read_text(encoding="utf-8")
                test_code = generate_test_suite(source_code, file.name)
                output_file = output_dir / f"test_{file.name}"
                output_file.write_text(test_code, encoding="utf-8")
                console.print(f"  [green]Generated tests/generated/test_{file.name}[/green]")
                succeeded += 1
            except Exception as exc:
                failed += 1
                errors.append((file, str(exc)))
                console.print(f"  [red]Error generating tests for {file}: {exc}[/red]")
            progress.advance(task)

    _print_summary("Generated tests for", succeeded, failed, errors)


@app.command()
def verify(
    path: str = typer.Argument(..., help="Python file or directory to verify."),
    exclude: Optional[list[str]] = typer.Option(None, "--exclude", "-e", help="Directories to skip."),
) -> None:
    """Run mypy and pytest verification on file(s) and their generated tests."""
    files = get_python_files(path, excluded_dirs=exclude)
    if not files:
        console.print("[yellow]No Python files found.[/yellow]")
        return

    succeeded, failed = 0, 0
    errors: list[tuple[Path, str]] = []

    table = Table(title="Verification Summary")
    table.add_column("Check", style="cyan")
    table.add_column("Target", style="white")
    table.add_column("Result", justify="center")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Verifying files...", total=len(files))

        for file in files:
            progress.update(task, description=f"Verifying {file.name}")
            try:
                test_file = f"tests/generated/test_{file.name}"
                mypy_passed = run_mypy(str(file))
                pytest_passed = run_pytest(test_file)

                mypy_status = "[green]PASS[/green]" if mypy_passed else "[red]FAIL[/red]"
                pytest_status = "[green]PASS[/green]" if pytest_passed else "[red]FAIL[/red]"

                table.add_row("Type Check", str(file), mypy_status)
                table.add_row("Unit Tests", test_file, pytest_status)

                if mypy_passed and pytest_passed:
                    succeeded += 1
                else:
                    failed += 1
                    if not mypy_passed:
                        errors.append((file, "mypy check failed"))
                    if not pytest_passed:
                        errors.append((file, "pytest failed"))
            except Exception as exc:
                failed += 1
                errors.append((file, str(exc)))
                console.print(f"  [red]Error verifying {file}: {exc}[/red]")
            progress.advance(task)

    console.print()
    console.print(table)
    console.print()
    _print_summary("Verified", succeeded, failed, errors)


def _print_summary(
    verb: str,
    succeeded: int,
    failed: int,
    errors: list[tuple[Path, str]],
) -> None:
    """Print a coloured summary line after a batch operation."""
    parts: list[str] = []
    if succeeded:
        parts.append(f"[green]{verb} {succeeded} file(s)[/green]")
    if failed:
        parts.append(f"[red]Failed {failed} file(s)[/red]")
    console.print(" | ".join(parts) if parts else "[dim]Nothing to do.[/dim]")

    if errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for path, msg in errors:
            console.print(f"  [red]{path}:[/red] {msg}")


if __name__ == "__main__":
    app()
