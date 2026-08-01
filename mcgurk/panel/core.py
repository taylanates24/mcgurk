"""Operator panel core — GUI-free, PsychoPy-free logic (Adım 10a).

The panel is a button-driven front end for the operator tools that are, today,
run from the command line: the checklist, the experiment, stimulus/backup
verification and the analysis exports.  Its *logic* lives here and its Qt shell
(Adım 10b) is a thin layer on top, the same way the engine keeps its timing
arithmetic out of ``av_presenter``:

* **Launch commands** are *built* here as plain ``argv`` lists (pure, testable);
  the actual spawning is a thin :func:`run_tool` wrapper.  PsychoPy and the
  hardware checklist must never share the panel's process (§A10.1), so the
  experiment and the checklist are always separate processes.
* **Results browsing** reads the database through a *read-only* connection and
  returns only anonymous columns (§A10.4 KVKK, §A10.5 read-only).
* **Tool wrappers** call the PsychoPy-free analysis layer directly and return
  panel-ready values.
* **Path resolution** answers "where is the read-only code" and "where may I
  write" for both a source checkout and a frozen ``.exe`` (§A10.6); Adım 10c
  wires the frozen branch to the real bundle.

This module imports no PsychoPy and no PySide6 — a boundary test enforces the
first, and the second is what keeps this layer testable in CI.  No string that
may be printed or raised uses a character outside cp1254 (§Don'ts).
"""

from __future__ import annotations

import sqlite3
import subprocess
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..analysis.export import export_database
from ..analysis.measures import session_measures
from ..analysis.qc_report import session_qc
from ..db.database import Database

# Path resolution (§A10.6) and the launch vocabulary live in the top-level
# ``mcgurk.paths`` so the session, the checklist, the tools and the frozen
# dispatcher share them without depending on the panel.  Re-exported here for
# the panel's callers and its tests.
from ..paths import (  # noqa: F401
    RUN_FLAG,
    SUB_CHECKLIST,
    SUB_RUN_MODULE,
    SUB_SESSION,
    SUB_VERIFY_BACKUP,
    SUB_VERIFY_STIMULI,
    PanelError,
    Runtime,
    detect_runtime,
    ensure_writable_config,
    resolve_roots,
)

# ---------------------------------------------------------------------------
# Launch command builders (§A10.1)
# ---------------------------------------------------------------------------

#: From a source checkout the same jobs run as ``-m <module>`` (session,
#: checklist) or as a ``tools/`` script (verify_*, run_module) instead of the
#: frozen ``exe --run <subcommand>``.
MODULE_UI = "mcgurk.ui"
MODULE_CHECKLIST = "mcgurk.checklist"


def _launch_prefix(
    runtime: Runtime,
    *,
    subcommand: str,
    module: str | None = None,
    script: str | None = None,
) -> list[str]:
    """The leading argv tokens for a subprocess, source or frozen.

    Frozen: ``[exe, --run, <subcommand>]``.  Source: ``[python, -m, <module>]``
    for a package entry point, or ``[python, tools/<script>]`` for a tool
    script.  Only the prefix differs between the two — every flag after it is
    shared, so a builder writes its arguments once.
    """
    if runtime.frozen:
        return [runtime.executable, RUN_FLAG, subcommand]
    if module is not None:
        return [runtime.executable, "-m", module]
    if script is not None:
        return [runtime.executable, str(runtime.resource_root / "tools" / script)]
    raise PanelError("Kaynak calismada module veya script verilmeli.")  # pragma: no cover


def session_command(
    runtime: Runtime,
    *,
    db: Path | str | None = None,
    limit: int | None = None,
    device: str | None = None,
    new_session: bool = False,
) -> list[str]:
    """Command that runs one full session (``mcgurk.ui``) as a separate process."""
    cmd = _launch_prefix(runtime, subcommand=SUB_SESSION, module=MODULE_UI)
    if db is not None:
        cmd += ["--db", str(db)]
    if limit is not None:
        cmd += ["--limit", str(limit)]
    if device is not None:
        cmd += ["--device", device]
    if new_session:
        cmd.append("--new-session")
    return cmd


def checklist_command(
    runtime: Runtime,
    *,
    config: Path | str | None = None,
    no_hardware: bool = False,
) -> list[str]:
    """Command that runs the pre-session GREEN/RED checklist (``mcgurk.checklist``)."""
    cmd = _launch_prefix(runtime, subcommand=SUB_CHECKLIST, module=MODULE_CHECKLIST)
    if config is not None:
        cmd += ["--config", str(config)]
    if no_hardware:
        cmd.append("--no-hardware")
    return cmd


def verify_stimuli_command(runtime: Runtime, *, quick: bool = False) -> list[str]:
    """Command that audits the prepared stimulus set (``tools/verify_stimuli.py``)."""
    cmd = _launch_prefix(
        runtime, subcommand=SUB_VERIFY_STIMULI, script="verify_stimuli.py"
    )
    if quick:
        cmd.append("--quick")
    return cmd


def verify_backup_command(
    runtime: Runtime,
    backup: Path | str,
    *,
    compare_with: Path | str | None = None,
) -> list[str]:
    """Command that verifies a database backup (``tools/verify_backup.py``)."""
    cmd = _launch_prefix(
        runtime, subcommand=SUB_VERIFY_BACKUP, script="verify_backup.py"
    )
    cmd.append(str(backup))
    if compare_with is not None:
        cmd += ["--compare-with", str(compare_with)]
    return cmd


def run_module_command(
    runtime: Runtime,
    module: str,
    *,
    dry_run: bool = False,
    limit: int | None = None,
    seed: int | None = None,
    ear: str | None = None,
) -> list[str]:
    """Command that runs a single assessment module (``tools/run_module.py``)."""
    cmd = _launch_prefix(runtime, subcommand=SUB_RUN_MODULE, script="run_module.py")
    cmd += ["--module", module]
    if dry_run:
        cmd.append("--dry-run")
    if limit is not None:
        cmd += ["--limit", str(limit)]
    if seed is not None:
        cmd += ["--seed", str(seed)]
    if ear is not None:
        cmd += ["--ear", ear]
    return cmd


@dataclass(frozen=True)
class ToolResult:
    """The outcome of a finished tool subprocess: its exit code and its text."""

    returncode: int
    output: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run_tool(
    command: Sequence[str],
    *,
    cwd: Path | str | None = None,
    timeout: float | None = None,
) -> ToolResult:
    """Run a report-producing tool to completion and capture its text.

    A thin wrapper over :func:`subprocess.run`: stdout and stderr are merged so
    the operator sees the whole report, decode errors are replaced rather than
    raised (Turkish output on a mixed-codepage console), and a non-zero exit is
    a *result*, not an exception — a RED checklist is exactly what the panel
    wants to show.  This is for the short tools (checklist, verify_*); the
    experiment's non-blocking launch is the Qt shell's job (Adım 10b).
    """
    completed = subprocess.run(  # noqa: S603 - argv is built here, never shell
        list(command),
        cwd=None if cwd is None else str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    parts = [part for part in (completed.stdout, completed.stderr) if part]
    return ToolResult(returncode=completed.returncode, output="".join(parts))


# ---------------------------------------------------------------------------
# Results browsing — read-only, anonymous (§A10.4, §A10.5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionRow:
    """One row of the session browser — anonymous code only, never a name."""

    session_id: int
    participant_code: str
    group_code: str
    started_at: str
    status: str
    n_trials: int


@dataclass(frozen=True)
class ParticipantRow:
    """One row of the participant browser — anonymous code only."""

    participant_id: int
    participant_code: str
    group_code: str
    n_sessions: int


_SESSIONS_SQL = """
    SELECT s.session_id                         AS session_id,
           p.participant_code                   AS participant_code,
           p.group_code                         AS group_code,
           s.started_at                         AS started_at,
           s.status                             AS status,
           (SELECT COUNT(*) FROM trials t
              JOIN blocks b ON b.block_id = t.block_id
             WHERE b.session_id = s.session_id) AS n_trials
      FROM sessions s
      JOIN participants p ON p.participant_id = s.participant_id
     ORDER BY s.session_id DESC
"""

_PARTICIPANTS_SQL = """
    SELECT p.participant_id                     AS participant_id,
           p.participant_code                   AS participant_code,
           p.group_code                         AS group_code,
           (SELECT COUNT(*) FROM sessions s
             WHERE s.participant_id = p.participant_id) AS n_sessions
      FROM participants p
     ORDER BY p.participant_id
"""


def open_readonly(path: Path | str) -> sqlite3.Connection:
    """Open a results database for reading only.

    The connection is opened with SQLite's ``mode=ro`` URI, so a write is
    refused by the engine itself rather than merely by convention — the results
    browser cannot alter 12 months of data even by accident (§A10.5).
    """
    db_path = Path(path)
    if not db_path.is_file():
        raise PanelError(f"Veritabani bulunamadi: {db_path}")
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def list_sessions(path: Path | str) -> list[SessionRow]:
    """Every session, newest first, with its participant code and trial count."""
    conn = open_readonly(path)
    try:
        rows = conn.execute(_SESSIONS_SQL).fetchall()
    finally:
        conn.close()
    return [
        SessionRow(
            session_id=int(row["session_id"]),
            participant_code=str(row["participant_code"]),
            group_code=str(row["group_code"]),
            started_at=str(row["started_at"]),
            status=str(row["status"]),
            n_trials=int(row["n_trials"]),
        )
        for row in rows
    ]


def list_participants(path: Path | str) -> list[ParticipantRow]:
    """Every participant, with how many sessions each has."""
    conn = open_readonly(path)
    try:
        rows = conn.execute(_PARTICIPANTS_SQL).fetchall()
    finally:
        conn.close()
    return [
        ParticipantRow(
            participant_id=int(row["participant_id"]),
            participant_code=str(row["participant_code"]),
            group_code=str(row["group_code"]),
            n_sessions=int(row["n_sessions"]),
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Analysis tool wrappers — panel-ready returns
# ---------------------------------------------------------------------------


def export_session(
    path: Path | str,
    out_dir: Path | str,
    session_id: int,
    *,
    formats: Iterable[str] = ("csv",),
) -> list[Path]:
    """Export one session's flat rows; returns the files written."""
    with Database(path, create=False) as db:
        return export_database(
            db, out_dir, session_id=session_id, formats=formats
        )


def export_all(
    path: Path | str,
    out_dir: Path | str,
    *,
    formats: Iterable[str] = ("csv",),
) -> list[Path]:
    """Export the whole database (flat view + raw tables); returns the files."""
    with Database(path, create=False) as db:
        return export_database(db, out_dir, formats=formats)


def measures_text(path: Path | str, session_id: int) -> str:
    """One session's per-module measures as a console block for the panel."""
    with Database(path, create=False) as db:
        return session_measures(db, session_id).summary_text()


def qc_text(path: Path | str, session_id: int) -> str:
    """One session's quality-control report as a console block for the panel."""
    with Database(path, create=False) as db:
        return session_qc(db, session_id).summary_text()
