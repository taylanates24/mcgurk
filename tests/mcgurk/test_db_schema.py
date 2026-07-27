"""Schema, pragmas and the integrity rules the database enforces itself."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from mcgurk.db import (
    SCHEMA_VERSION,
    Block,
    Database,
    Participant,
    Response,
    SchemaVersionError,
    SessionRecord,
    Trial,
)

TABLES = {
    "participants",
    "calibrations",
    "sessions",
    "blocks",
    "trials",
    "responses",
}


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "data" / "test.sqlite")
    yield database
    database.close()


def _participant(db: Database, code: str = "P001") -> int:
    return db.add_participant(
        Participant(participant_code=code, group_code="SSD_R", age=34, sex="F")
    )


def _session(db: Database, participant_id: int) -> int:
    return db.start_session(
        SessionRecord(
            participant_id=participant_id,
            seed=12345,
            config_snapshot="{}",
            config_mode="development",
            python_version="3.10.20",
            os_name="Windows 11",
        )
    )


def _block(db: Database, session_id: int, module: str = "mcgurk") -> int:
    return db.add_block(
        Block(
            session_id=session_id,
            module=module,
            block_index=0,
            n_trials_planned=10,
        )
    )


# ------------------------------------------------------------------ schema


def test_schema_is_created(db: Database) -> None:
    names = {
        row["name"]
        for row in db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert TABLES <= names


def test_flat_view_exists(db: Database) -> None:
    views = {
        row["name"]
        for row in db.conn.execute("SELECT name FROM sqlite_master WHERE type='view'")
    }
    assert "v_trials_flat" in views


def test_schema_version_is_stamped(db: Database) -> None:
    assert int(db.conn.execute("PRAGMA user_version").fetchone()[0]) == SCHEMA_VERSION


def test_foreign_keys_are_enforced(db: Database) -> None:
    assert db.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_wal_mode_is_active(db: Database) -> None:
    mode = db.conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"


def test_reopening_keeps_the_data(tmp_path: Path) -> None:
    path = tmp_path / "test.sqlite"
    first = Database(path)
    _participant(first)
    first.close()

    second = Database(path)
    assert second.get_participant_by_code("P001") is not None
    second.close()


def test_parent_directory_is_created(tmp_path: Path) -> None:
    database = Database(tmp_path / "yeni" / "klasor" / "test.sqlite")
    database.close()
    assert (tmp_path / "yeni" / "klasor" / "test.sqlite").is_file()


def test_missing_file_with_create_false(tmp_path: Path) -> None:
    with pytest.raises(Exception, match="bulunamadı"):
        Database(tmp_path / "yok.sqlite", create=False)


# -------------------------------------------------------- schema rejection


def test_legacy_src_database_is_rejected(tmp_path: Path) -> None:
    # The Adım 0 database has a different participants table; opening it here
    # would create a second, inconsistent schema in the same file.
    path = tmp_path / "mcgurk.db"
    legacy = sqlite3.connect(path)
    legacy.execute(
        "CREATE TABLE participants (participant_id INTEGER PRIMARY KEY, "
        "participant_code TEXT, age INTEGER)"
    )
    legacy.commit()
    legacy.close()

    with pytest.raises(SchemaVersionError, match="şemasını kullanmıyor"):
        Database(path)


def test_future_schema_version_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "test.sqlite"
    database = Database(path)
    database.close()

    conn = sqlite3.connect(path)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
    conn.commit()
    conn.close()

    with pytest.raises(SchemaVersionError, match="şema sürümü"):
        Database(path)


# --------------------------------------------------------------- integrity


def test_foreign_key_violation_is_refused(db: Database) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        db.start_session(
            SessionRecord(
                participant_id=999,
                seed=1,
                config_snapshot="{}",
                config_mode="development",
                python_version="3.10.20",
                os_name="Windows 11",
            )
        )


def test_participant_code_is_unique(db: Database) -> None:
    _participant(db, "P001")
    with pytest.raises(sqlite3.IntegrityError):
        _participant(db, "P001")


def test_group_code_is_constrained(db: Database) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        db.add_participant(
            Participant(
                participant_code="P002", group_code="SSD-right", age=30, sex="F"
            )
        )


def test_age_outside_the_inclusion_range_is_refused(db: Database) -> None:
    # Method document §4: 18-60.  Outside that the row is a protocol
    # violation, not a data point.
    with pytest.raises(sqlite3.IntegrityError):
        db.add_participant(
            Participant(participant_code="P003", group_code="CTRL", age=71, sex="M")
        )


def test_session_status_is_constrained(db: Database) -> None:
    participant_id = _participant(db)
    session_id = _session(db, participant_id)
    with pytest.raises(sqlite3.IntegrityError):
        db.finish_session(session_id, "bitti")


def test_unknown_module_is_refused(db: Database) -> None:
    participant_id = _participant(db)
    session_id = _session(db, participant_id)
    with pytest.raises(sqlite3.IntegrityError):
        db.add_block(
            Block(
                session_id=session_id,
                module="telepati",
                block_index=0,
                n_trials_planned=1,
            )
        )


def test_block_index_is_unique_per_session(db: Database) -> None:
    participant_id = _participant(db)
    session_id = _session(db, participant_id)
    _block(db, session_id)
    with pytest.raises(sqlite3.IntegrityError):
        _block(db, session_id)


# ------------------------------------------------------ §A.10 at the storage layer


def _mcgurk_trial(db: Database) -> int:
    participant_id = _participant(db)
    session_id = _session(db, participant_id)
    block_id = _block(db, session_id, "mcgurk")
    return db.add_trial(
        Trial(
            block_id=block_id,
            trial_index=0,
            module="mcgurk",
            visual_token="ga",
            audio_token="ba",
            ear="left",
            design_extra={"speaker_id": 1},
        )
    )


def test_incongruent_trial_cannot_be_scored(db: Database) -> None:
    trial_id = _mcgurk_trial(db)
    with pytest.raises(sqlite3.IntegrityError, match="A.10"):
        db.add_response(Response(trial_id=trial_id, raw_response="DA", is_correct=True))


def test_incongruent_trial_cannot_be_scored_by_update(db: Database) -> None:
    trial_id = _mcgurk_trial(db)
    response_id = db.add_response(
        Response(trial_id=trial_id, raw_response="DA", category="FUSION")
    )
    with pytest.raises(sqlite3.IntegrityError, match="A.10"):
        db.conn.execute(
            "UPDATE responses SET is_correct = 1 WHERE response_id = ?", (response_id,)
        )


def test_dichotic_trial_cannot_be_scored(db: Database) -> None:
    participant_id = _participant(db)
    session_id = _session(db, participant_id)
    block_id = _block(db, session_id, "dichotic")
    trial_id = db.add_trial(
        Trial(
            block_id=block_id,
            trial_index=0,
            module="dichotic",
            ear="both",
            design_extra={"left_token": "ba", "right_token": "da"},
        )
    )
    with pytest.raises(sqlite3.IntegrityError, match="A.10"):
        db.add_response(Response(trial_id=trial_id, raw_response="BA", is_correct=True))


def test_simultaneity_judgement_cannot_be_scored(db: Database) -> None:
    """A TBW trial has no correct answer either (Adım 6, schema version 3).

    At +300 ms the streams really are asynchronous, but the measurement is
    whether they were *perceived* as one event; scoring "different" as correct
    would turn the width of the participant's binding window into an error rate.
    """
    participant_id = _participant(db)
    session_id = _session(db, participant_id)
    block_id = _block(db, session_id, "tbw")
    trial_id = db.add_trial(
        Trial(
            block_id=block_id,
            trial_index=0,
            module="tbw",
            visual_token="ba",
            audio_token="ba",
            ear="both",
            nominal_soa_ms=300.0,
            presentation_mode="AV",
            design_extra={"speaker_id": 1},
        )
    )
    with pytest.raises(sqlite3.IntegrityError, match="A.10"):
        db.add_response(
            Response(trial_id=trial_id, raw_response="Farklı zamanda", is_correct=True)
        )
    # The judgement itself is recorded, as a category.
    assert (
        db.add_response(
            Response(
                trial_id=trial_id, raw_response="Farklı zamanda", category="DIFFERENT"
            )
        )
        > 0
    )


def test_congruent_module_may_be_scored(db: Database) -> None:
    participant_id = _participant(db)
    session_id = _session(db, participant_id)
    block_id = _block(db, session_id, "avsr")
    trial_id = db.add_trial(
        Trial(
            block_id=block_id,
            trial_index=0,
            module="avsr",
            audio_token="ba",
            presentation_mode="A",
            design_extra={
                "speaker_id": 1,
                "stimulus_type": "syllable",
                "item": "ba",
            },
        )
    )
    response_id = db.add_response(
        Response(trial_id=trial_id, raw_response="BA", is_correct=True)
    )
    assert response_id > 0
