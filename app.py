import os
import re
import streamlit as st
import subprocess
import sys
import time
from pathlib import Path
import pandas as pd

# Import internal modules
try:
    from src.scanner import FunctionInfo, ScanResult, scan_codebase
except ImportError:
    st.error("Scanner module not found. Run from the project root: `streamlit run app.py`")
    st.stop()

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="TechDebtAssassin",
    page_icon="🥷",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 2. Professional UI Styling ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #eeeeee;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .success-box {
        padding: 2rem;
        border-radius: 0.8rem;
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Session State Initialization ---
if "scan_results" not in st.session_state:
    st.session_state.scan_results = None
if "scanned_path" not in st.session_state:
    st.session_state.scanned_path = None
if "celebrate" not in st.session_state:
    st.session_state.celebrate = False

# --- 4. Sidebar: Configuration ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/ninja-head.png", width=80)
    st.title("TechDebtAssassin")
    st.caption("v1.0.0 | Autonomous Agent")
    st.markdown("---")

    default_path = str(Path.cwd() / "demo")
    project_path = st.text_input("Target Repository Path:", value=default_path)

    st.markdown("---")

    scan_btn = st.button("🔍 Analyze Codebase", type="primary")
    status_placeholder = st.empty()

# Invalidate stale results when the user changes the target path
if st.session_state.scanned_path and st.session_state.scanned_path != project_path:
    st.session_state.scan_results = None
    st.session_state.scanned_path = None
    st.session_state.celebrate = False


# --- 5. Core Controller ---

def run_analysis() -> ScanResult | None:
    """Perform a fresh scan and store results in session state."""
    root = Path(project_path)
    if not root.is_dir():
        status_placeholder.error("Path not found or is not a directory.")
        return None

    # Clear previous results to prevent ghost data between runs
    st.session_state.scan_results = None
    st.session_state.scanned_path = None

    with st.spinner("Agent is analyzing codebase..."):
        try:
            results = scan_codebase(
                root,
                exclude_dirs={".git", "__pycache__", "venv", "node_modules", "tests"},
                force=False,
            )
            st.session_state.scan_results = results
            st.session_state.scanned_path = project_path
            status_placeholder.success("Analysis complete.")
            return results
        except Exception as e:
            st.warning(f"Scanner error: {e}")
            return None


if scan_btn:
    st.session_state.celebrate = False
    run_analysis()


# --- 6. Auto-Fix Engine ---

_STRIP_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_TIMEOUT_SECONDS = 600  # 10 minutes


def _run_auto_fix(target_path: str, total_issues: int) -> None:
    """Stream the fix subprocess with live progress feedback."""
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"   # flush output immediately
    env["NO_COLOR"] = "1"           # disable Rich color codes
    env["TERM"] = "dumb"            # disable Rich progress bars

    fixed, skipped, errors = 0, 0, 0
    log_lines = []

    with st.status(
        f"Fixing 0/{total_issues} functions...", expanded=True
    ) as status:
        log_area = st.empty()

        try:
            proc = subprocess.Popen(
                [sys.executable, "main.py", "fix", target_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )
        except FileNotFoundError:
            st.warning("Could not locate `main.py`. Run from the project root.")
            return

        deadline = time.time() + _TIMEOUT_SECONDS

        for raw_line in proc.stdout:
            line = _STRIP_ANSI.sub("", raw_line).rstrip()
            if not line:
                continue

            # Parse progress from main.py output
            if "Fixed" in line:
                fixed += 1
            elif "Skipping" in line:
                skipped += 1
            elif "Error" in line:
                errors += 1

            log_lines.append(line)
            done = fixed + skipped + errors
            status.update(
                label=f"Fixing {done}/{total_issues} — {fixed} fixed, {skipped} skipped",
            )
            log_area.code("\n".join(log_lines[-25:]))

            if time.time() > deadline:
                proc.kill()
                st.warning(
                    f"Timed out after {_TIMEOUT_SECONDS // 60} minutes. "
                    f"Fixed {fixed} functions before timeout."
                )
                break

        proc.wait(timeout=30)

        if proc.returncode == 0:
            status.update(
                label=f"Done — {fixed} fixed, {skipped} skipped",
                state="complete",
            )
            st.toast("Patches applied! Re-scanning...", icon="🎉")
            time.sleep(1)
            st.session_state.celebrate = True
            run_analysis()
            st.rerun()
        else:
            status.update(
                label=f"Finished with errors — {fixed} fixed, {skipped} skipped, {errors} errors",
                state="error",
            )
            with st.expander("Full log"):
                st.code("\n".join(log_lines))


# --- 7. Dashboard View ---

def _get_actually_missing(res: ScanResult) -> list[FunctionInfo]:
    """Compute functions with genuinely missing hints (ignores force flag)."""
    return [
        f for f in res.functions
        if f.params_missing_hints or not f.has_return_type
    ]


if st.session_state.scan_results:
    res = st.session_state.scan_results

    total_funcs = len(res.functions)
    missing_funcs = _get_actually_missing(res)
    missing_count = len(missing_funcs)

    st.header(f"Project: {Path(project_path).name}")

    # Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Files Scanned", res.files_scanned)
    m2.metric("Functions Found", total_funcs)
    m3.metric(
        "Missing Type Hints",
        missing_count,
        delta=-missing_count if missing_count > 0 else 0,
        delta_color="inverse",
    )
    health_val = (
        100
        if total_funcs == 0
        else int(((total_funcs - missing_count) / total_funcs) * 100)
    )
    m4.metric("Codebase Health", f"{health_val}%")

    st.markdown("---")

    # Tabs
    tab1, tab2 = st.tabs(["📉 Issues Overview", "🛠️ Repair Pipeline"])

    with tab1:
        if missing_count == 0:
            # Fire balloons only once per transition to clean state
            if st.session_state.celebrate:
                st.balloons()
                st.session_state.celebrate = False
            st.markdown("""
                <div class="success-box">
                    <h2>✅ Codebase is Clean!</h2>
                    <p>No technical debt detected. All functions are correctly typed.</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.subheader(f"⚠️ {missing_count} functions require modernization")
            data = []
            for f in missing_funcs:
                data.append({
                    "File": str(f.file_path).replace(str(Path(project_path)), ""),
                    "Function": f.name,
                    "Missing Params": ", ".join(f.params_missing_hints) if f.params_missing_hints else "None",
                    "Missing Return": "Yes" if not f.has_return_type else "No",
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Autonomous AI Repair")
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown("""
            **Deployment Strategy:**
            * Generate type hint patches using **Claude Opus 4.6**.
            * Maintain global project context for accuracy.
            * Apply physical patches to files.
            * Run verification pass via `mypy`.
            """)
        with c2:
            if missing_count > 0:
                if st.button("✨ Auto-Fix All Issues", key="exec_fix", type="primary"):
                    _run_auto_fix(project_path, missing_count)
            else:
                st.success("Everything looks good! No repairs needed.")
else:
    st.info("👈 Enter a target path in the sidebar and click 'Analyze Codebase' to begin.")
