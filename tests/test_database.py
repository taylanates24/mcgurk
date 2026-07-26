"""Database schema, anonymity guarantees and session lifecycle."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from src.data.database import Database, SchemaMismatchError
from src.data.models import (
    SESSION_ABORTED,
    SESSION_COMPLETED,
    SESSION_RUNNING,
    Participant,
    Session,
    Trial,
)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "test.db")
    yield database
    database.close()


def _participant(code: str = "SSD-R-007") -> Participant:
    return Participant(participant_code=code, age=34, gender="female", group="SSD-right")


def _trial(session_id: int, participant_id: int, **overrides: Any) -> Trial:
    fields: dict[str, Any] = dict(
        session_id=session_id,
        participant_id=participant_id,
        section_type="mcgurk",
        speaker="female_speaker_1",
        visual_syllable="ga",
        audio_syllable="ba",
        noise_condition="clean",
        snr_db=None,
        participant_response="da",
        correct_answer="ba",
        is_correct=None,
        rt_from_video_end_ms=812.5,
        rt_from_options_shown_ms=640.25,
        trial_order=1,
    )
    fields.update(overrides)
    return Trial(**fields)


def test_participants_table_has_no_name_column(db: Database):
    """KVKK: names must not be storable at all, not merely unused."""
    columns = {row["name"] for row in db.conn.execute("PRAGMA table_info(participants)")}

    assert "participant_code" in columns
    assert "name" not in columns


def test_participant_roundtrip(db: Database):
    participant_id = db.add_participant(_participant())

    stored = db.get_participant(participant_id)

    assert stored is not None
    assert stored["participant_code"] == "SSD-R-007"
    assert stored["age"] == 34
    assert stored["group"] == "SSD-right"


def test_legacy_schema_is_rejected(tmp_path: Path):
    """A pre-anonymisation database must fail loudly, not be reused."""
    legacy_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(legacy_path)
    conn.execute(
        "CREATE TABLE participants ("
        "participant_id INTEGER PRIMARY KEY, name TEXT NOT NULL, age INTEGER)"
    )
    conn.commit()
    conn.close()

    with pytest.raises(SchemaMismatchError, match="eski şema"):
        Database(legacy_path)


def test_session_starts_running_and_records_seed(db: Database):
    participant_id = db.add_participant(_participant())

    session_id = db.add_session(
        Session(
            participant_id=participant_id,
            speaker="female_speaker_1",
            sections_run="mcgurk",
            seed=123456,
        )
    )

    stored = db.get_sessions_for_participant(participant_id)[0]
    assert stored["session_id"] == session_id
    assert stored["seed"] == 123456
    assert stored["status"] == SESSION_RUNNING
    assert stored["completed_at"] is None


@pytest.mark.parametrize("status", [SESSION_COMPLETED, SESSION_ABORTED])
def test_finish_session_records_status(db: Database, status: str):
    participant_id = db.add_participant(_participant())
    session_id = db.add_session(
        Session(
            participant_id=participant_id,
            speaker="female_speaker_1",
            sections_run="mcgurk",
            seed=1,
        )
    )

    db.finish_session(session_id, status, "2026-07-26T15:00:00")

    stored = db.get_sessions_for_participant(participant_id)[0]
    assert stored["status"] == status
    assert stored["completed_at"] == "2026-07-26T15:00:00"


def test_trial_without_correct_answer_stores_null(db: Database):
    """McGurk trials have no correct answer — NULL, not 0."""
    participant_id = db.add_participant(_participant())
    session_id = db.add_session(
        Session(
            participant_id=participant_id,
            speaker="female_speaker_1",
            sections_run="mcgurk",
            seed=1,
        )
    )

    db.add_trial(_trial(session_id, participant_id, is_correct=None))

    stored = db.get_trials_for_session(session_id)[0]
    assert stored["is_correct"] is None


@pytest.mark.parametrize(("is_correct", "expected"), [(True, 1), (False, 0)])
def test_scored_trial_stores_boolean(db: Database, is_correct: bool, expected: int):
    participant_id = db.add_participant(_participant())
    session_id = db.add_session(
        Session(
            participant_id=participant_id,
            speaker="female_speaker_1",
            sections_run="av_congruent",
            seed=1,
        )
    )

    db.add_trial(
        _trial(
            session_id, participant_id,
            section_type="av_congruent", is_correct=is_correct,
        )
    )

    stored = db.get_trials_for_session(session_id)[0]
    assert stored["is_correct"] == expected


def test_foreign_keys_are_enforced(db: Database):
    with pytest.raises(sqlite3.IntegrityError):
        db.add_trial(_trial(session_id=999, participant_id=999))


def test_export_view_exposes_code_not_name(db: Database):
    participant_id = db.add_participant(_participant())
    session_id = db.add_session(
        Session(
            participant_id=participant_id,
            speaker="female_speaker_1",
            sections_run="mcgurk",
            seed=1,
        )
    )
    db.add_trial(_trial(session_id, participant_id))

    row = db.get_all_trials()[0]

    assert row["participant_code"] == "SSD-R-007"
    assert row["participant_group"] == "SSD-right"
    assert "participant_name" not in row
