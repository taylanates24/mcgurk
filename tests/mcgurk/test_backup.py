"""Backups and their verification.

An untested backup is not a backup, so the verifier is tested against a good
one, an empty one, a truncated one and a stale one.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest

from mcgurk.db import (
    SESSION_COMPLETED,
    BackupError,
    Block,
    Database,
    Participant,
    SessionRecord,
    Trial,
    backup_filename,
    latest_backup,
)
from tools.verify_backup import main as verify_main
from tools.verify_backup import verify


@pytest.fixture
def populated_db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "data" / "test.sqlite")
    participant_id = database.add_participant(
        Participant(participant_code="P001", group_code="CTRL", age=25, sex="F")
    )
    session_id = database.start_session(
        SessionRecord(
            participant_id=participant_id,
            seed=1,
            config_snapshot="{}",
            config_mode="development",
            python_version="3.10.20",
            os_name="Windows 11",
        )
    )
    block_id = database.add_block(
        Block(session_id=session_id, module="mcgurk", block_index=0, n_trials_planned=3)
    )
    for index in range(3):
        database.add_trial(
            Trial(
                block_id=block_id,
                trial_index=index,
                module="mcgurk",
                design_extra={"speaker_id": 1},
            )
        )
    database.finish_block(block_id, SESSION_COMPLETED)
    yield database
    database.close()


# ------------------------------------------------------------- file naming


def test_filename_uses_basic_iso_format() -> None:
    # Extended ISO 8601 uses colons, which Windows refuses in a filename.
    name = backup_filename(datetime(2026, 7, 26, 15, 31, 49))
    assert name == "mcgurk_20260726T153149.sqlite"
    assert ":" not in name


def test_label_is_sanitised() -> None:
    name = backup_filename(datetime(2026, 7, 26, 15, 31, 49), label="oturum 12/ABC")
    assert name == "mcgurk_20260726T153149_oturum-12-ABC.sqlite"


# ---------------------------------------------------------------- writing


def test_backup_is_written_and_verifies(
    populated_db: Database, tmp_path: Path
) -> None:
    target = populated_db.backup(tmp_path / "backups")
    assert target.is_file()

    ok, report = verify(target)
    assert ok, report
    assert "integrity_check: ok" in report


def test_backup_contains_the_data(populated_db: Database, tmp_path: Path) -> None:
    target = populated_db.backup(tmp_path / "backups")
    restored = Database(target)
    try:
        assert restored.counts()["trials"] == 3
        assert restored.get_participant_by_code("P001") is not None
    finally:
        restored.close()


def test_backup_directory_is_created(populated_db: Database, tmp_path: Path) -> None:
    target = populated_db.backup(tmp_path / "yeni" / "backups")
    assert target.parent.is_dir()


def test_existing_target_is_not_overwritten(
    populated_db: Database, tmp_path: Path
) -> None:
    when = datetime(2026, 7, 26, 15, 31, 49)
    directory = tmp_path / "backups"
    directory.mkdir()
    (directory / backup_filename(when)).write_text("mevcut", encoding="utf-8")
    from mcgurk.db.backup import backup_database

    with pytest.raises(BackupError, match="zaten var"):
        backup_database(populated_db.conn, directory, when=when)


def test_latest_backup_picks_the_newest(tmp_path: Path) -> None:
    directory = tmp_path / "backups"
    directory.mkdir()
    for stamp in ("20260101T000000", "20260726T153149", "20260301T120000"):
        (directory / f"mcgurk_{stamp}.sqlite").touch()
    newest = latest_backup(directory)
    assert newest is not None
    assert "20260726T153149" in newest.name


def test_latest_backup_on_empty_directory(tmp_path: Path) -> None:
    assert latest_backup(tmp_path / "yok") is None


# ------------------------------------------------------------ verification


def test_missing_backup_is_reported(tmp_path: Path) -> None:
    ok, report = verify(tmp_path / "yok.sqlite")
    assert not ok
    assert "KIRMIZI" in report


def test_empty_backup_is_flagged_but_valid(tmp_path: Path) -> None:
    empty = Database(tmp_path / "bos.sqlite")
    target = empty.backup(tmp_path / "backups")
    empty.close()

    ok, report = verify(target)
    assert ok
    assert "SARI" in report  # verifies clean, restores nothing


def test_count_comparison_against_the_live_database(
    populated_db: Database, tmp_path: Path
) -> None:
    target = populated_db.backup(tmp_path / "backups")
    ok, report = verify(target, populated_db.path)
    assert ok, report
    assert "= canlı" in report


def test_stale_backup_is_reported(populated_db: Database, tmp_path: Path) -> None:
    target = populated_db.backup(tmp_path / "backups")
    # More data lands in the live database after the backup was taken.
    session = populated_db.get_session(1)
    assert session is not None
    session_id = session["session_id"]
    block_id = populated_db.add_block(
        Block(session_id=session_id, module="tbw", block_index=1, n_trials_planned=1)
    )
    populated_db.add_trial(Trial(block_id=block_id, trial_index=0, module="tbw"))
    populated_db.finish_block(block_id, SESSION_COMPLETED)

    ok, report = verify(target, populated_db.path)
    assert not ok
    # "!=" rather than "≠": the report is printed on a cp1254 console
    # (tests/mcgurk/test_console_encoding.py).
    assert "!= canlı" in report


def test_missing_comparison_target_is_reported(
    populated_db: Database, tmp_path: Path
) -> None:
    target = populated_db.backup(tmp_path / "backups")
    ok, _ = verify(target, tmp_path / "yok.sqlite")
    assert not ok


def test_truncated_backup_fails_verification(
    populated_db: Database, tmp_path: Path
) -> None:
    target = populated_db.backup(tmp_path / "backups")
    target.write_bytes(b"SQLite format 3\x00" + b"\x00" * 200)
    ok, _ = verify(target)
    assert not ok


# ------------------------------------------------------------------- CLI


def test_cli_returns_zero_for_a_good_backup(
    populated_db: Database, tmp_path: Path, capsys
) -> None:
    target = populated_db.backup(tmp_path / "backups")
    assert verify_main([str(target)]) == 0
    assert "YEDEK KULLANILABİLİR" in capsys.readouterr().out


def test_cli_returns_one_for_a_missing_backup(tmp_path: Path, capsys) -> None:
    assert verify_main([str(tmp_path / "yok.sqlite")]) == 1
    assert "GÜVENİLİR DEĞİL" in capsys.readouterr().out
