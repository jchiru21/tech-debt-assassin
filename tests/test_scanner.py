"""Tests for src.scanner."""

from pathlib import Path

from src.scanner import collect_python_files, get_python_files, parse_function_signatures, scan_codebase


def test_collect_python_files_finds_py_files(tmp_path: Path) -> None:
    (tmp_path / "module.py").write_text("x = 1")
    (tmp_path / "readme.md").write_text("# hi")
    result = collect_python_files(tmp_path)
    assert all(p.suffix == ".py" for p in result)


def test_collect_python_files_excludes_dirs(tmp_path: Path) -> None:
    venv = tmp_path / "venv"
    venv.mkdir()
    (venv / "lib.py").write_text("")
    (tmp_path / "app.py").write_text("")
    result = collect_python_files(tmp_path, exclude_dirs={"venv"})
    assert not any("venv" in str(p) for p in result)


def test_parse_function_signatures(tmp_path: Path) -> None:
    src = tmp_path / "sample.py"
    src.write_text("def greet(name):\n    return f'hi {name}'\n")
    funcs = parse_function_signatures(src)
    assert len(funcs) >= 1
    assert funcs[0].name == "greet"


def test_scan_codebase_returns_scan_result(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def foo(x): pass\n")
    result = scan_codebase(tmp_path)
    assert result.files_scanned >= 1


# ── get_python_files tests ───────────────────────────────────────────


def test_get_python_files_single_file(tmp_path: Path) -> None:
    py = tmp_path / "app.py"
    py.write_text("x = 1")
    result = get_python_files(str(py))
    assert result == [py.resolve()]


def test_get_python_files_non_python_file(tmp_path: Path) -> None:
    txt = tmp_path / "notes.txt"
    txt.write_text("hello")
    assert get_python_files(str(txt)) == []


def test_get_python_files_directory(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("")
    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / "b.py").write_text("")
    result = get_python_files(str(tmp_path))
    names = {p.name for p in result}
    assert "a.py" in names
    assert "b.py" in names


def test_get_python_files_skips_default_excludes(tmp_path: Path) -> None:
    (tmp_path / "good.py").write_text("")
    for dirname in ("venv", "__pycache__", ".git"):
        d = tmp_path / dirname
        d.mkdir()
        (d / "hidden.py").write_text("")
    result = get_python_files(str(tmp_path))
    assert all("venv" not in str(p) for p in result)
    assert all("__pycache__" not in str(p) for p in result)
    assert all(".git" not in str(p) for p in result)
    assert len(result) == 1


def test_get_python_files_respects_custom_excludes(tmp_path: Path) -> None:
    (tmp_path / "keep.py").write_text("")
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "lib.py").write_text("")
    result = get_python_files(str(tmp_path), excluded_dirs=["vendor"])
    assert all("vendor" not in str(p) for p in result)
    assert len(result) == 1


def test_get_python_files_nonexistent_path() -> None:
    assert get_python_files("/tmp/does_not_exist_xyz_123") == []
