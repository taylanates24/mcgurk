"""Source/frozen path resolution — the single authority (§A10.6).

Every entry point (the panel, the session, the checklist, the tools) needs the
same two answers: *where is the read-only code and its bundled defaults* and
*where may I write* (``data/``, ``backups/``, ``logs/``, ``config/``,
``stimuli/``).  From a source checkout both are the repository root, so nothing
changes.  Frozen under PyInstaller they split: the code lives in the read-only
``_MEIPASS`` bundle, while the data has to sit somewhere writable next to the
``.exe``.

Keeping this in one place, used by all entry points, is what §A10.6 asks for: a
single path layer that is correct from source and frozen alike.  It imports no
PsychoPy and no PySide6 — a boundary test enforces the first — so ``mcgurk.ui``
and ``mcgurk.checklist`` can depend on it without pulling anything heavy in.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

#: The config path, relative to a root.  Kept here rather than imported from the
#: config loader so this module stays a leaf with no mcgurk dependencies.
_CONFIG_RELATIVE = Path("config") / "experiment.yaml"

#: The launch vocabulary shared by the command builders (``panel.core``) and the
#: frozen dispatcher (``app_entry``).  They MUST agree — a frozen ``.exe`` is
#: launched as ``exe --run <subcommand>`` — so the strings live here, in the one
#: leaf module both import, rather than being duplicated in each.
RUN_FLAG = "--run"
SUB_SESSION = "session"
SUB_CHECKLIST = "checklist"
SUB_VERIFY_STIMULI = "verify-stimuli"
SUB_VERIFY_BACKUP = "verify-backup"
SUB_RUN_MODULE = "run-module"


class PanelError(RuntimeError):
    """Raised for a path/panel problem the operator has to act on.

    Named for the panel, its first consumer; it is also raised by the shared
    path resolution the other entry points use.
    """


@dataclass(frozen=True)
class Runtime:
    """Where the application is running from.

    ``executable`` is what spawns a subprocess: the Python interpreter from a
    source checkout, or the frozen ``.exe`` itself.  ``resource_root`` is the
    read-only code/data root (the checkout, or PyInstaller's unpacked
    ``_MEIPASS``); ``writable_root`` is where ``data/``, ``backups/``, ``logs/``,
    ``config/`` and ``stimuli/`` live and may be written.  From a source
    checkout the two roots are the same directory.
    """

    frozen: bool
    executable: str
    resource_root: Path
    writable_root: Path


def resolve_roots(
    *,
    frozen: bool,
    source_root: Path,
    meipass: Path | None,
    exe_dir: Path | None,
) -> tuple[Path, Path]:
    """Return ``(resource_root, writable_root)`` for the given situation.

    Pure, so the frozen branch is testable without actually being frozen:

    * source (``frozen=False``) — both roots are ``source_root``;
    * frozen — ``resource_root`` is ``meipass`` (the read-only unpacked bundle)
      and ``writable_root`` is ``exe_dir`` (next to the ``.exe`` — a portable
      layout; a ``%APPDATA%`` fallback for read-only install locations could be
      added here without touching any caller).
    """
    if not frozen:
        return source_root, source_root
    if meipass is None or exe_dir is None:
        raise PanelError(
            "Donmus calismada _MEIPASS ve exe dizini gerekli, ikisi de verilmedi."
        )
    return meipass, exe_dir


def detect_runtime() -> Runtime:
    """Build the :class:`Runtime` for the current process (thin wrapper)."""
    frozen = bool(getattr(sys, "frozen", False))
    executable = sys.executable
    # ``mcgurk/paths.py`` -> repository root is two levels up.
    source_root = Path(__file__).resolve().parents[1]

    if frozen:
        exe_dir = Path(executable).resolve().parent
        meipass = Path(getattr(sys, "_MEIPASS", exe_dir))
        resource_root, writable_root = resolve_roots(
            frozen=True, source_root=source_root, meipass=meipass, exe_dir=exe_dir
        )
    else:
        resource_root, writable_root = resolve_roots(
            frozen=False, source_root=source_root, meipass=None, exe_dir=None
        )
    return Runtime(
        frozen=frozen,
        executable=executable,
        resource_root=resource_root,
        writable_root=writable_root,
    )


def ensure_writable_config(runtime: Runtime) -> Path:
    """The config file to load, copying the bundled default out on first run.

    * source — the repository's ``config/experiment.yaml``, unchanged;
    * frozen — ``writable_root/config/experiment.yaml``.  On first run it does
      not exist yet, so the read-only default bundled at
      ``resource_root/config/experiment.yaml`` is copied out to the writable
      location the operator can edit.  Afterwards the writable copy is always
      the one loaded, so an edit survives and a re-run never overwrites it.
    """
    if not runtime.frozen:
        return runtime.resource_root / _CONFIG_RELATIVE

    writable_config = runtime.writable_root / _CONFIG_RELATIVE
    if not writable_config.exists():
        bundled = runtime.resource_root / _CONFIG_RELATIVE
        writable_config.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(bundled, writable_config)
    return writable_config
