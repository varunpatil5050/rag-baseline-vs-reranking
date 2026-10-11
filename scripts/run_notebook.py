#!/usr/bin/env python3
"""Execute the assignment notebook with this Python environment as its kernel."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile
import subprocess


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline", action="store_true",
        help="Use locally cached Hugging Face models without network access.",
    )
    parser.add_argument(
        "--discovery", action="store_true",
        help="Run all exploratory queries and disable new Gemini generation.",
    )
    parser.add_argument(
        "--skip-generation", action="store_true",
        help="Disable new Gemini requests; matching cached answers remain available.",
    )
    return parser.parse_args()


def save_notebook(notebook, destination: Path, nbformat) -> None:
    """Replace the destination only after writing the complete notebook."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.stem}-", suffix=".ipynb", dir=destination.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        nbformat.write(notebook, temporary_path)
        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
    if args.discovery:
        os.environ["LMA_QUERY_FILE"] = "data/discovery_queries.json"
    if args.discovery or args.skip_generation:
        os.environ["LMA_RUN_GEMINI"] = "0"

    import nbformat
    from jupyter_client import KernelManager
    from nbclient import NotebookClient

    source = root / "RAG_Baseline_vs_Reranking.ipynb"
    query_file = Path(os.getenv("LMA_QUERY_FILE", "data/queries.json")).resolve()
    selected = query_file == (root / "data/queries.json").resolve()
    results = root / "results"
    if not selected:
        results = results / query_file.stem
    destination = (
        source if selected else results / "discovery_execution.ipynb"
    )
    notebook = nbformat.read(source, as_version=4)
    code_cells = sum(cell.cell_type == "code" for cell in notebook.cells)
    completed = 0

    def report_progress(cell, cell_index, **_):
        nonlocal completed
        if cell.cell_type == "code":
            completed += 1
            print(f"Completed code cell {completed}/{code_cells}.", flush=True)

    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [
        sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}",
    ]
    client = NotebookClient(
        notebook, km=manager, timeout=1800,
        resources={"metadata": {"path": str(root)}},
        on_cell_executed=report_progress,
    )
    print(f"Executing {source.name} with {sys.executable}.", flush=True)
    try:
        client.execute()
    except Exception as error:
        failed = results / "failed_execution.ipynb"
        save_notebook(notebook, failed, nbformat)
        # Notebook/network exception text can contain credential-bearing URLs.
        print(f"Execution failed: {type(error).__name__}.", file=sys.stderr, flush=True)
        print(f"Diagnostic notebook saved to {failed}.", file=sys.stderr, flush=True)
        return 1
    save_notebook(notebook, destination, nbformat)
    print(f"Successful execution saved to {destination}.", flush=True)
    verification = [sys.executable, str(root / "scripts/verify_submission.py"), "--results", str(results)]
    if not selected or args.skip_generation:
        verification.append("--allow-incomplete-answers")
    return subprocess.run(verification, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
