"""What the session menu reads back out of the database (ADIM 12c).

Both queries are read-only and answer a question the schema never stored
directly: which speaker a participant was tested with, and how the speakers are
spread over the sessions so far.  They come from ``trials.design_extra`` rather
than from the config snapshot because a ``balanced`` or ``random`` strategy
leaves the snapshot without a speaker — the snapshot says how one was chosen,
the trials say which one it was.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from mcgurk.db import (
    SESSION_COMPLETED,
    Block,
    Database,
    Participant,
    SessionRecord,
    Trial,
)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "test.sqlite")
    yield database
    database.close()


def _participant(db: Database, code: str) -> int:
    return db.add_participant(
        Participant(participant_code=code, group_code="CTRL", age=30, sex="F")
    )


def _session_with_speaker(
    db: Database, participant_id: int, speaker_id: int | None, *, module: str = "mcgurk"
) -> int:
    """One session holding a single trial, so the speaker is recorded."""
    session_id = db.start_session(
        SessionRecord(
            participant_id=participant_id,
            seed=1,
            config_snapshot="{}",
            config_mode="development",
            python_version="3.10.20",
            os_name="Windows 11",
            git_commit="abc1234",
        )
    )
    block_id = db.add_block(
        Block(session_id=session_id, module=module, block_index=0, n_trials_planned=1)
    )
    extra: dict[str, Any] = {"speaker_id": speaker_id} if speaker_id else {}
    if module == "oddball":
        extra = {"tone_type": "standard", "tone_hz": 1000.0, "isi_ms": 1000.0}
    db.add_trial(
        Trial(block_id=block_id, trial_index=0, module=module, design_extra=extra)
    )
    db.finish_block(block_id, SESSION_COMPLETED)
    db.finish_session(session_id, SESSION_COMPLETED)
    return session_id


# ------------------------------------------------ participant_speaker_id


def test_a_participant_with_no_sessions_has_no_speaker(db: Database) -> None:
    """A first session must not be warned about a speaker change."""
    assert db.participant_speaker_id(_participant(db, "YENI")) is None


def test_the_speaker_comes_from_the_participants_own_trials(db: Database) -> None:
    mine = _participant(db, "BENIM")
    theirs = _participant(db, "BASKASI")
    _session_with_speaker(db, theirs, 7)
    _session_with_speaker(db, mine, 2)

    assert db.participant_speaker_id(mine) == 2
    assert db.participant_speaker_id(theirs) == 7


def test_the_most_recent_session_wins(db: Database) -> None:
    """The menu defaults to what this participant last saw, not what they saw first."""
    participant_id = _participant(db, "IKI-OTURUM")
    _session_with_speaker(db, participant_id, 2)
    _session_with_speaker(db, participant_id, 5)

    assert db.participant_speaker_id(participant_id) == 5


def test_a_session_with_no_speaker_bearing_trial_is_skipped(db: Database) -> None:
    """An oddball-only session says nothing about the speaker — tones have no face."""
    participant_id = _participant(db, "SADECE-ODDBALL")
    _session_with_speaker(db, participant_id, 3)
    _session_with_speaker(db, participant_id, None, module="oddball")

    assert db.participant_speaker_id(participant_id) == 3


# ------------------------------------------------- speaker_session_counts


def test_counts_are_empty_before_anything_ran(db: Database) -> None:
    assert db.speaker_session_counts() == {}


def test_each_session_counts_once_however_many_trials_it_has(
    db: Database,
) -> None:
    """Otherwise the menu would report trials and call them sessions."""
    participant_id = _participant(db, "SAYIM")
    session_id = _session_with_speaker(db, participant_id, 4)
    block_id = db.add_block(
        Block(session_id=session_id, module="tbw", block_index=1, n_trials_planned=2)
    )
    for index in range(2):
        db.add_trial(
            Trial(
                block_id=block_id,
                trial_index=index,
                module="tbw",
                design_extra={"speaker_id": 4},
            )
        )
    db.finish_block(block_id, SESSION_COMPLETED)

    assert db.speaker_session_counts() == {4: 1}


def test_counts_are_per_speaker_over_every_participant(db: Database) -> None:
    first = _participant(db, "BIR")
    second = _participant(db, "IKI")
    _session_with_speaker(db, first, 1)
    _session_with_speaker(db, second, 1)
    _session_with_speaker(db, second, 6)

    assert db.speaker_session_counts() == {1: 2, 6: 1}
