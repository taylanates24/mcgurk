"""Adım 10a — the operator panel's GUI-free core.

Everything here runs without a screen, a sound card, PsychoPy or PyQt6: the
launch commands are built as plain argv lists, the result browsing reads a
throwaway database, and the analysis wrappers call the PsychoPy-free layer.  The
frozen (``.exe``) branch of the path resolution is exercised with constructed
inputs rather than an actual freeze.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any

import pytest

from mcgurk.db import Block, Database, Participant, Response, SessionRecord, Trial
from mcgurk.panel import core

# A source checkout and a frozen exe, built directly so no real freeze is needed.
SOURCE = core.Runtime(
    frozen=False,
    executable="python",
    resource_root=Path("/proj"),
    writable_root=Path("/proj"),
)
FROZEN = core.Runtime(
    frozen=True,
    executable="/app/mcgurk.exe",
    resource_root=Path("/meipass"),
    writable_root=Path("/app"),
)


def _tool_path(runtime: core.Runtime, script: str) -> str:
    return str(runtime.resource_root / "tools" / script)


# ------------------------------------------------------------- path resolution


def test_resolve_roots_source_uses_one_root_for_both() -> None:
    resource, writable = core.resolve_roots(
        frozen=False, source_root=Path("/proj"), meipass=None, exe_dir=None
    )
    assert resource == Path("/proj")
    assert writable == Path("/proj")


def test_resolve_roots_frozen_splits_read_only_from_writable() -> None:
    resource, writable = core.resolve_roots(
        frozen=True,
        source_root=Path("/proj"),
        meipass=Path("/meipass"),
        exe_dir=Path("/app"),
    )
    assert resource == Path("/meipass")  # read-only unpacked bundle
    assert writable == Path("/app")  # next to the .exe


def test_resolve_roots_frozen_needs_both_locations() -> None:
    with pytest.raises(core.PanelError):
        core.resolve_roots(
            frozen=True, source_root=Path("/proj"), meipass=None, exe_dir=Path("/app")
        )


def test_detect_runtime_from_source_is_not_frozen() -> None:
    runtime = core.detect_runtime()
    assert runtime.frozen is False
    assert runtime.executable == sys.executable
    # From a checkout both roots are the repository root, which holds tools/.
    assert runtime.resource_root == runtime.writable_root
    assert (runtime.resource_root / "tools" / "run_module.py").is_file()


# ------------------------------------------------------------- launch commands


def test_session_command_from_source() -> None:
    assert core.session_command(SOURCE) == ["python", "-m", "mcgurk.ui"]


def test_session_command_forwards_every_flag() -> None:
    cmd = core.session_command(
        SOURCE, db="data/x.sqlite", limit=8, device="Speakers", new_session=True
    )
    assert cmd == [
        "python",
        "-m",
        "mcgurk.ui",
        "--db",
        "data/x.sqlite",
        "--limit",
        "8",
        "--device",
        "Speakers",
        "--new-session",
    ]


def test_session_command_when_frozen_uses_the_exe_and_subcommand() -> None:
    cmd = core.session_command(FROZEN, limit=8)
    assert cmd == ["/app/mcgurk.exe", "--run", "session", "--limit", "8"]


def test_checklist_command_source_and_frozen() -> None:
    assert core.checklist_command(SOURCE, no_hardware=True) == [
        "python",
        "-m",
        "mcgurk.checklist",
        "--no-hardware",
    ]
    assert core.checklist_command(FROZEN, no_hardware=True) == [
        "/app/mcgurk.exe",
        "--run",
        "checklist",
        "--no-hardware",
    ]


def test_verify_stimuli_command_uses_the_tools_script_from_source() -> None:
    assert core.verify_stimuli_command(SOURCE, quick=True) == [
        "python",
        _tool_path(SOURCE, "verify_stimuli.py"),
        "--quick",
    ]
    assert core.verify_stimuli_command(FROZEN, quick=True) == [
        "/app/mcgurk.exe",
        "--run",
        "verify-stimuli",
        "--quick",
    ]


def test_verify_backup_command_carries_the_paths() -> None:
    cmd = core.verify_backup_command(
        SOURCE, "backups/b.sqlite", compare_with="data/live.sqlite"
    )
    assert cmd == [
        "python",
        _tool_path(SOURCE, "verify_backup.py"),
        "backups/b.sqlite",
        "--compare-with",
        "data/live.sqlite",
    ]


def test_verify_backup_command_frozen_omits_optional_compare() -> None:
    assert core.verify_backup_command(FROZEN, "backups/b.sqlite") == [
        "/app/mcgurk.exe",
        "--run",
        "verify-backup",
        "backups/b.sqlite",
    ]


def test_run_module_command_from_source() -> None:
    cmd = core.run_module_command(
        SOURCE, "gin", dry_run=True, limit=4, seed=11, ear="left"
    )
    assert cmd == [
        "python",
        _tool_path(SOURCE, "run_module.py"),
        "--module",
        "gin",
        "--dry-run",
        "--limit",
        "4",
        "--seed",
        "11",
        "--ear",
        "left",
    ]


def test_run_module_command_frozen_minimal() -> None:
    assert core.run_module_command(FROZEN, "mcgurk") == [
        "/app/mcgurk.exe",
        "--run",
        "run-module",
        "--module",
        "mcgurk",
    ]


# ------------------------------------------------------------- run_tool


def test_run_tool_captures_output_and_zero_exit() -> None:
    result = core.run_tool([sys.executable, "-c", "print('merhaba')"])
    assert result.ok is True
    assert result.returncode == 0
    assert "merhaba" in result.output


def test_run_tool_reports_a_nonzero_exit_as_a_result_not_an_error() -> None:
    result = core.run_tool(
        [sys.executable, "-c", "import sys; sys.stderr.write('bozuk\\n'); sys.exit(3)"]
    )
    assert result.ok is False
    assert result.returncode == 3
    assert "bozuk" in result.output


# ------------------------------------------------------------- results browsing


@pytest.fixture
def config(write_config: Any, config_dict: dict[str, Any]) -> Any:
    from mcgurk.config.loader import load_config

    return load_config(write_config(config_dict), check_filesystem=False)


@pytest.fixture
def db_path(tmp_path: Path, config: Any) -> Path:
    """A results database with one participant, one session, three trials."""
    path = tmp_path / "data" / "results.sqlite"
    db = Database(path)
    try:
        participant_id = db.add_participant(
            Participant(participant_code="P007", group_code="SSD_L", age=45, sex="F")
        )
        session_id = db.start_session(
            SessionRecord(
                participant_id=participant_id,
                seed=13,
                config_snapshot=db.snapshot_config(config.model_dump(mode="json")),
                config_mode="development",
                python_version="3.10.20",
                os_name="Windows 11",
            )
        )
        block_id = db.add_block(
            Block(
                session_id=session_id,
                module="mcgurk",
                block_index=db.next_block_index(session_id),
                n_trials_planned=3,
            )
        )
        for index, (visual, category) in enumerate(
            [("ga", "FUSION"), ("ba", "AUDITORY"), ("da", None)]
        ):
            trial_id = db.add_trial(
                Trial(
                    block_id=block_id,
                    trial_index=index,
                    module="mcgurk",
                    visual_token=visual,
                    audio_token="ba",
                    ear="left",
                    design_extra={"speaker_id": 1},
                )
            )
            if category is not None:
                db.add_response(
                    Response(
                        trial_id=trial_id,
                        raw_response=category.lower(),
                        category=category,
                    )
                )
        db.finish_block(block_id, status="completed")
    finally:
        db.close()
    return path


def test_list_sessions_is_anonymous_and_counts_trials(db_path: Path) -> None:
    sessions = core.list_sessions(db_path)
    assert len(sessions) == 1
    row = sessions[0]
    assert row.participant_code == "P007"
    assert row.group_code == "SSD_L"
    assert row.status == "running"
    assert row.n_trials == 3
    # KVKK: the row model carries no name field at all.
    assert not hasattr(row, "name")
    assert set(vars(row)) == {
        "session_id",
        "participant_code",
        "group_code",
        "started_at",
        "status",
        "n_trials",
    }


def test_list_participants_counts_sessions(db_path: Path) -> None:
    participants = core.list_participants(db_path)
    assert len(participants) == 1
    assert participants[0].participant_code == "P007"
    assert participants[0].n_sessions == 1


def test_list_sessions_on_empty_database_is_empty(tmp_path: Path) -> None:
    empty = tmp_path / "empty.sqlite"
    Database(empty).close()
    assert core.list_sessions(empty) == []


def test_open_readonly_refuses_a_write(db_path: Path) -> None:
    conn = core.open_readonly(db_path)
    try:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute(
                "INSERT INTO participants (participant_code, group_code, age, sex, "
                "created_at) VALUES ('X', 'CTRL', 30, 'M', '2026-01-01')"
            )
    finally:
        conn.close()


def test_open_readonly_missing_file_raises_panel_error(tmp_path: Path) -> None:
    with pytest.raises(core.PanelError):
        core.open_readonly(tmp_path / "nope.sqlite")


# ------------------------------------------------------------- tool wrappers


def test_export_session_writes_a_csv(db_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "export"
    written = core.export_session(db_path, out, session_id=1)
    assert written == [out / "trials_flat.csv"]
    assert written[0].is_file()


def test_export_all_includes_the_raw_tables(db_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "export_all"
    written = core.export_all(db_path, out)
    names = {path.name for path in written}
    assert "trials_flat.csv" in names
    assert "participants.csv" in names
    assert "responses.csv" in names


def test_measures_text_returns_a_console_block(db_path: Path) -> None:
    text = core.measures_text(db_path, session_id=1)
    assert "P007" in text
    assert "mcgurk" in text.lower()


def test_qc_text_returns_a_console_block(db_path: Path) -> None:
    text = core.qc_text(db_path, session_id=1)
    assert "P007" in text


def test_measures_text_missing_session_raises(db_path: Path) -> None:
    from mcgurk.analysis.measures import MeasuresError

    with pytest.raises(MeasuresError):
        core.measures_text(db_path, session_id=999)


# ------------------------------------------------------------- session deletion


def test_delete_session_removes_it_and_backs_up_first(
    db_path: Path, tmp_path: Path
) -> None:
    backups = tmp_path / "backups"
    (session,) = core.list_sessions(db_path)  # the fixture's one session
    result = core.delete_session(db_path, session.session_id, backup_dir=backups)

    # Backed up before deleting, so the session is recoverable.
    assert result.backup_path.is_file()
    assert result.deleted == {
        "responses": 2,  # two answered trials
        "trials": 3,
        "blocks": 1,
        "sessions": 1,
    }
    assert core.list_sessions(db_path) == []


def test_delete_session_missing_raises(db_path: Path, tmp_path: Path) -> None:
    from mcgurk.db.database import DatabaseError

    with pytest.raises(DatabaseError):
        core.delete_session(db_path, 999, backup_dir=tmp_path / "backups")
