"""Adım 9b — failure modes.

steps.md Adım 9 lists five ways a session can go wrong; each must fail *loudly*
or be recorded honestly, never bent into a plausible-looking result:

* interruption mid-session -> the session is ``aborted``, the data already
  collected survives, and the session can be resumed;
* no response -> a timeout, recorded as the absence of a response (``NONE`` in
  McGurk, an incorrect answer in AVSR), never invented;
* a missing stimulus -> caught before the participant sits down;
* the audio path failing -> an ``AudioError``, never a silent fallback (§A.2);
* a write failing (a full disk) -> a raised error, never a silent data loss.

The audio-device and disk-full modes are represented by CI-runnable stand-ins:
the audio path refusing a missing file / wrong sample rate, and a write to a
read-only connection.  The hardware paths themselves are covered by the
``psychopy``-marked engine tests.
"""

from __future__ import annotations

import copy
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
import yaml

from mcgurk.config.loader import ConfigError, load_config
from mcgurk.db import Block, Database, Participant, SessionRecord, Trial
from mcgurk.engine.audio import AudioError, load_audio
from mcgurk.modules import avsr, mcgurk
from mcgurk.stimuli.wavfile import write as write_wav

SHIPPED_CONFIG = Path(__file__).resolve().parents[2] / "config" / "experiment.yaml"


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "data" / "test.sqlite")
    yield database
    database.close()


# ---------------------------------------------- interruption mid-session


def test_interruption_preserves_data_and_leaves_the_session_resumable(db: Database) -> None:
    pid = db.add_participant(
        Participant(participant_code="ABORT01", group_code="SSD_R", age=40, sex="M")
    )
    sid = db.start_session(SessionRecord(
        participant_id=pid, seed=1, config_snapshot="{}", config_mode="development",
        python_version="3.10", os_name="win",
    ))
    # A completed mcgurk block: two trials that must survive.
    done = db.add_block(Block(session_id=sid, module="mcgurk", block_index=0, n_trials_planned=2))
    for i in range(2):
        db.add_trial(Trial(block_id=done, trial_index=i, module="mcgurk", visual_token="ga",
                           audio_token="ba", ear="left", design_extra={"speaker_id": 1}))
    db.finish_block(done, status="completed")
    # A partial block interrupted by ESC: one trial, block aborted.
    partial = db.add_block(Block(session_id=sid, module="avsr", block_index=1, n_trials_planned=10))
    db.add_trial(Trial(block_id=partial, trial_index=0, module="avsr", presentation_mode="AV",
                       audio_token="ba", ear="left",
                       design_extra={"speaker_id": 1, "stimulus_type": "syllable", "item": "ba"}))
    db.finish_block(partial, status="aborted")
    db.set_session_status(sid, "aborted")

    # The completed data survives.
    assert db.conn.execute(
        "SELECT COUNT(*) FROM trials t JOIN blocks b ON b.block_id = t.block_id "
        "WHERE b.session_id = ?", (sid,)
    ).fetchone()[0] == 3
    # Only the completed block counts toward what has been done — the aborted
    # partial does not, so resume re-runs it.
    assert db.completed_trial_counts(sid) == {"mcgurk": 2}
    # And the session is offered for resume.
    resumable = db.latest_resumable_session(pid)
    assert resumable is not None and resumable["session_id"] == sid


# ------------------------------------------------------ no response


def test_a_missing_response_is_none_in_mcgurk() -> None:
    """A timed-out McGurk trial is a row with no response; it reads as NONE and
    stays in the denominator, never dropped."""
    rows = [
        {"module": "mcgurk", "trial_id": 1, "response_id": 1, "category": "FUSION",
         "rt_from_burst_ms": 500.0, "snr_db": None, "ear": "left"},
        {"module": "mcgurk", "trial_id": 2, "response_id": None, "category": None,
         "rt_from_burst_ms": None, "snr_db": None, "ear": "left"},
    ]
    rates = mcgurk.rates_from_rows(rows)
    assert rates.n_trials == 2
    assert rates.counts[mcgurk.NONE] == 1
    assert mcgurk.categorise(None, visual_token="ga", audio_token="ba") == mcgurk.NONE


def test_a_missing_response_is_incorrect_in_avsr() -> None:
    """AVSR has a correct answer, so a timeout is an incorrect trial, not a
    missing observation — excluding it would flatter whoever ran out of time."""
    rows = [
        {"module": "avsr", "trial_id": 1, "presentation_mode": "AV", "is_correct": 1,
         "snr_db": None, "ear": "left"},
        {"module": "avsr", "trial_id": 2, "presentation_mode": "AV", "is_correct": None,
         "snr_db": None, "ear": "left"},  # timeout
    ]
    by_mode = avsr.accuracy_by_mode(rows)
    assert by_mode["AV"].n_trials == 2
    assert by_mode["AV"].n_correct == 1
    assert by_mode["AV"].n_missing == 1
    assert by_mode["AV"].accuracy == pytest.approx(0.5)


# ------------------------------------------------------ missing stimulus


def test_an_unprepared_token_is_caught_at_config_load(tmp_path: Path) -> None:
    """A design token with no prepared recording is a config error at load —
    before the participant sits down, not a missing file mid-session."""
    raw = yaml.safe_load(SHIPPED_CONFIG.read_text(encoding="utf-8"))
    raw = copy.deepcopy(raw)
    raw["modules"]["mcgurk"]["av_pairs"].append(
        {"visual": "zz", "audio": "ba", "label": "bogus", "reps": 1}
    )
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path, check_filesystem=False)


def test_a_missing_stimulus_file_is_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(AudioError):
        load_audio(tmp_path / "yok.wav", ear="both")


# ------------------------------------------------------ audio path


def test_the_audio_path_refuses_a_wrong_sample_rate(tmp_path: Path) -> None:
    """§A.12/§A.2: resampling at run time would move every burst time, so a
    mismatch is refused loudly rather than silently resampled."""
    path = tmp_path / "token.wav"
    write_wav(path, np.zeros(4800, dtype=np.float64), 44100, bit_depth=24)
    with pytest.raises(AudioError, match="örnekleme hızı"):
        load_audio(path, ear="both", expected_sample_rate=48000)


# ------------------------------------------------------ write failure (disk full)


def test_a_write_failure_is_not_silently_swallowed(db: Database) -> None:
    """A full disk (or any I/O failure) must raise, never look like a successful
    write — silent data loss in a 12-month study is the worst outcome."""
    db.conn.execute("PRAGMA query_only = ON")
    with pytest.raises(sqlite3.OperationalError):
        db.add_participant(
            Participant(participant_code="NOPE", group_code="CTRL", age=25, sex="F")
        )
