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
* **The design summary and the editable trial counts** (Adım 11) are projections
  of ``mcgurk.config``: the numbers come from ``config.trial_counts()`` and the
  writing from ``mcgurk.config.edit``, so the panel and ``python -m
  mcgurk.config`` can never report different designs.
* **Path resolution** answers "where is the read-only code" and "where may I
  write" for both a source checkout and a frozen ``.exe`` (§A10.6); Adım 10c
  wires the frozen branch to the real bundle.

This module imports no PsychoPy and no PyQt6 — a boundary test enforces the
first, and the second is what keeps this layer testable in CI.  No string that
may be printed or raised uses a character outside cp1254 (§Don'ts).
"""

from __future__ import annotations

import html
import sqlite3
import subprocess
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..analysis.export import export_database
from ..analysis.measures import session_measures
from ..analysis.qc_report import session_qc
from ..config import edit
from ..config.edit import RepField  # noqa: F401 - re-exported for the Qt shell
from ..config.loader import ConfigError  # noqa: F401 - the panel catches it
from ..config.schema import ExperimentConfig
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
# Output rendering — colour the GREEN/RED/WARN verdicts for the panel
# ---------------------------------------------------------------------------

#: Status word -> dot colour.  The checklist/verify tools print these words
#: (cp1254-safe, so a direct terminal run is fine); the panel turns a leading
#: one into a filled coloured dot.
_STATUS_COLOURS = {
    "YESIL": "#1a9e1a",  # green
    "UYARI": "#d19a00",  # amber
    "KIRMIZI": "#c0392b",  # red
}

#: The filled circle (U+25CF) written as an HTML entity, NOT a literal: the
#: character is outside cp1254 and would trip the console-encoding test, but it
#: is only ever shown in the panel's Qt widget (never printed), and the entity
#: is plain ASCII in the source.
_DOT = "&#9679;"


def status_html(text: str) -> str:
    """Render captured tool output as HTML, a leading verdict word as a dot.

    A line beginning ``YESIL``/``UYARI``/``KIRMIZI`` gets a filled green/amber/
    red dot in place of the word; the word's remaining width is padded so the
    report's columns stay aligned in a monospace pane.  Every other line is
    escaped and its spacing preserved.  Pure and ASCII-only, so it is
    CI-testable and does not affect the cp1254 console rule.
    """
    rendered: list[str] = []
    for line in text.split("\n"):
        dot_line = None
        for word, colour in _STATUS_COLOURS.items():
            if line.startswith(word):
                pad = "&nbsp;" * (len(word) - 1)
                rest = html.escape(line[len(word) :]).replace(" ", "&nbsp;")
                dot_line = f'<span style="color:{colour}">{_DOT}</span>{pad}{rest}'
                break
        if dot_line is None:
            dot_line = html.escape(line).replace(" ", "&nbsp;")
        rendered.append(dot_line)
    return "<br>".join(rendered)


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


@dataclass(frozen=True)
class DeleteResult:
    """The outcome of deleting a session: where it was backed up, and counts."""

    backup_path: Path
    deleted: dict[str, int]


def delete_session(
    path: Path | str, session_id: int, *, backup_dir: Path | str
) -> DeleteResult:
    """Back up the database, then delete one session and all its data.

    A fresh ``VACUUM INTO`` backup is taken *before* the delete (§A10.5: a
    12-month study has to survive an accidental deletion), so a regretted delete
    is recoverable from *backup_dir*.  The panel gates this behind an explicit
    confirmation; this function assumes the operator already confirmed.
    """
    with Database(path, create=False) as db:
        backup_path = db.backup(backup_dir, label=f"pre_delete_session{session_id}")
        deleted = db.delete_session(session_id)
    return DeleteResult(backup_path=backup_path, deleted=deleted)


def measures_text(path: Path | str, session_id: int) -> str:
    """One session's per-module measures as a console block for the panel."""
    with Database(path, create=False) as db:
        return session_measures(db, session_id).summary_text()


def qc_text(path: Path | str, session_id: int) -> str:
    """One session's quality-control report as a console block for the panel."""
    with Database(path, create=False) as db:
        return session_qc(db, session_id).summary_text()


# ---------------------------------------------------------------------------
# Design summary and the editable trial counts (Adım 11)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DesignRow:
    """One line of the design summary: a module, its trials, its estimate.

    ``duration_s`` is None for the steps that produce trials but no duration
    estimate — ``practice`` and ``cross_hearing`` have no ``modules.*`` entry
    and therefore no ``estimated_trial_duration_s`` (which is why the shipped
    ~59 minutes is a floor, not a prediction).
    """

    module: str
    n_trials: int
    duration_s: float | None


def design_rows(config: ExperimentConfig) -> list[DesignRow]:
    """Trials (and the duration estimate) per module, in session order.

    A thin projection of :meth:`ExperimentConfig.trial_counts` — the same
    numbers ``python -m mcgurk.config`` prints, so the panel and the command
    line cannot report different designs.
    """
    modules = config.modules.by_name()
    rows: list[DesignRow] = []
    for name, count in config.trial_counts().items():
        module = modules.get(name)
        duration = (
            module.estimated_duration_s()
            if module is not None and module.enabled
            else None
        )
        rows.append(DesignRow(module=name, n_trials=count, duration_s=duration))
    return rows


def rep_fields(config: ExperimentConfig) -> list[RepField]:
    """The repetition counts the Ayarlar tab may edit, with current values."""
    return edit.read_reps(config)


def preview_reps(
    config: ExperimentConfig, changes: Mapping[str, int]
) -> ExperimentConfig:
    """*config* with the given counts applied, in memory only.

    What the tab's live "Toplam: N deneme / ~X dk" is computed from, so the
    operator sees the cost of a change before deciding to save it.
    """
    return edit.preview_reps(config, changes)


def save_reps(
    config_path: Path | str,
    project_root: Path | str,
    changes: Mapping[str, int],
) -> ExperimentConfig:
    """Write the counts to the config file and return the re-validated config.

    Comments are preserved and an invalid result is rolled back — see
    :func:`mcgurk.config.edit.write_reps`.  Raises :class:`ConfigError`, which
    the Qt shell turns into a dialog.
    """
    return edit.write_reps(config_path, project_root, changes)


def default_reps(runtime: Runtime) -> dict[str, int]:
    """The factory counts, read from the read-only bundled defaults file.

    ``resource_root``, not ``writable_root``: the whole point of the defaults
    file is that it is the copy the operator cannot have edited.
    """
    return edit.default_reps(runtime.resource_root)
