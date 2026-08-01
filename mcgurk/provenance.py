"""Environment facts recorded on every session row.

A data set collected over 12 months has to stay interpretable after the code
has moved on, so each session stores the commit it ran from, the interpreter
and the library versions.

Nothing here imports PsychoPy: ``importlib.metadata`` reads the installed
version from package metadata, which costs no import side effects and works on
a CI runner where PsychoPy is not installed at all.  The audio backend cannot
be determined without loading PsychoPy, so it stays a database column that the
presentation layer fills in (Adım 3).
"""

from __future__ import annotations

import logging
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from . import __version__

logger = logging.getLogger(__name__)

_GIT_TIMEOUT_S = 5

#: Keep git from flashing a console window when called by the windowed frozen
#: app (provenance is recorded at session start).  0 on non-Windows.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def package_version(name: str) -> str | None:
    """Installed version of *name*, or None when it is not installed."""
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _run_git(repo_root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_S,
            check=False,
            creationflags=_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("git çalıştırılamadı (%s): %s", args, exc)
        return None
    if result.returncode != 0:
        logger.debug("git %s başarısız: %s", args, result.stderr.strip())
        return None
    return result.stdout.strip()


def git_commit(repo_root: Path | str) -> str | None:
    """Short commit hash, suffixed ``+dirty`` when the tree has changes.

    Returns None outside a git repository or when git is unavailable — that is
    a legitimate state on an analysis machine, not an error.
    """
    root = Path(repo_root)
    commit = _run_git(root, "rev-parse", "--short", "HEAD")
    if commit is None:
        return None
    status = _run_git(root, "status", "--porcelain")
    if status:
        return f"{commit}+dirty"
    return commit


@dataclass(frozen=True)
class Provenance:
    app_version: str
    git_commit: str | None
    python_version: str
    os_name: str
    psychopy_version: str | None
    psychtoolbox_version: str | None

    def as_dict(self) -> dict[str, str | None]:
        return asdict(self)


def collect(repo_root: Path | str | None = None) -> Provenance:
    """Gather everything the session row records about this machine."""
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[1]
    return Provenance(
        app_version=__version__,
        git_commit=git_commit(root),
        python_version=sys.version.split()[0],
        os_name=f"{platform.system()} {platform.release()} ({platform.machine()})",
        psychopy_version=package_version("psychopy"),
        psychtoolbox_version=package_version("psychtoolbox"),
    )
