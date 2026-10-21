"""Writable workspace paths shared by the CLI and provenance server."""
import os
from pathlib import Path


def workspace_root() -> Path:
    if os.getenv("SYFLOW_PROJECT_ROOT"):
        return Path(os.environ["SYFLOW_PROJECT_ROOT"]).expanduser().resolve()
    checkout = Path(__file__).resolve().parents[2]
    if (checkout / "pyproject.toml").is_file() and (checkout / "targets").is_dir():
        return checkout
    return Path.cwd().resolve()


def runs_directory() -> Path:
    return Path(os.getenv("SYFLOW_RUNS_DIR", workspace_root() / "runs")).expanduser().resolve()
