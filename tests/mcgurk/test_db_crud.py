"""Writing and reading a session: commit boundaries, design_extra, flat view."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from mcgurk.db import (
    SESSION_ABORTED,
    SESSION_COMPLETED,
    Block,
    Database,
    DesignExtraError,
    Participant,
    Response,
    SessionRecord,
    Trial,
    TrialTiming,
    calibration_record_from_file,
    parse_design_extra,
    validate_design_extra,
)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "test.sqlite")
    yield database
    database.close()


@pytest.fixture
def session(db: Database) -> tuple[int, int]:
    participant_id = db.add_participant(
        Participant(
            participant_code="SSD-014",
            group_code="SSD_L",
            age=42,
            sex="M",
            deprivation_months=36,
            pta_right_db=12.5,
            pta_left_db=88.0,
            postlingual=True,
        )
    )
    session_id = db.start_session(
        SessionRecord(
            participant_id=participant_id,
            seed=987654,
            config_snapshot='{"experiment": {"mode": "development"}}',
            config_mode="development",
            python_version="3.10.20",
            os_name="Windows 11",
            git_commit="abc1234",
        )
    )
    return participant_id, session_id


# ----------------------------------------------------------- participants


def test_participant_round_trip(db: Database, session: tuple[int, int]) -> None:
    participant_id, _ = session
    row = db.get_participant(participant_id)
    assert row is not None
    assert row["participant_code"] == "SSD-014"
    assert row["deprivation_months"] == 36
    assert row["postlingual"] == 1
    # §A.6 — there is no column that could hold a name.
    assert "name" not in row


def test_lookup_by_code(db: Database, session: tuple[int, int]) -> None:
    assert db.get_participant_by_code("SSD-014") is not None
    assert db.get_participant_by_code("yok") is None


# --------------------------------------------------------------- sessions


def test_session_records_the_environment(db: Database, session: tuple[int, int]) -> None:
    _, session_id = session
    row = db.get_session(session_id)
    assert row is not None
    assert row["seed"] == 987654
    assert row["git_commit"] == "abc1234"
    assert row["status"] == "running"


def test_finishing_a_session_sets_status_and_time(
    db: Database, session: tuple[int, int]
) -> None:
    _, session_id = session
    db.finish_session(session_id, SESSION_COMPLETED)
    row = db.get_session(session_id)
    assert row is not None
    assert row["status"] == SESSION_COMPLETED
    assert row["completed_at"] is not None


def test_aborted_session_is_distinguishable(
    db: Database, session: tuple[int, int]
) -> None:
    _, session_id = session
    db.finish_session(session_id, SESSION_ABORTED)
    row = db.get_session(session_id)
    assert row is not None
    assert row["status"] == SESSION_ABORTED


# --------------------------------------------- commit boundaries (§A.5)


def test_trials_are_not_committed_until_the_block_closes(
    db: Database, session: tuple[int, int], tmp_path: Path
) -> None:
    _, session_id = session
    block_id = db.add_block(
        Block(session_id=session_id, module="mcgurk", block_index=0, n_trials_planned=2)
    )
    db.add_trial(
        Trial(
            block_id=block_id,
            trial_index=0,
            module="mcgurk",
            design_extra={"speaker_id": 1},
        )
    )

    # A separate connection sees only committed data, which is exactly what
    # "no disk I/O inside a trial" means in practice.
    other = sqlite3.connect(tmp_path / "test.sqlite")
    try:
        before = other.execute("SELECT COUNT(*) FROM trials").fetchone()[0]
    finally:
        other.close()
    assert before == 0

    db.finish_block(block_id, SESSION_COMPLETED)

    other = sqlite3.connect(tmp_path / "test.sqlite")
    try:
        after = other.execute("SELECT COUNT(*) FROM trials").fetchone()[0]
    finally:
        other.close()
    assert after == 1


def test_timing_is_written_after_presentation(
    db: Database, session: tuple[int, int]
) -> None:
    _, session_id = session
    block_id = db.add_block(
        Block(session_id=session_id, module="tbw", block_index=0, n_trials_planned=1)
    )
    trial_id = db.add_trial(
        Trial(
            block_id=block_id,
            trial_index=0,
            module="tbw",
            visual_token="ba",
            audio_token="ba",
            nominal_soa_ms=-100.0,
            design_extra={"speaker_id": 1},
        )
    )
    db.set_trial_timing(
        trial_id,
        TrialTiming(
            video_onset_s=1.2345,
            audio_onset_s=1.1345,
            actual_soa_ms=-100.3,
            dropped_frames=0,
            max_frame_interval_ms=17.1,
        ),
    )
    db.finish_block(block_id, SESSION_COMPLETED)

    row = db.get_trials_for_block(block_id)[0]
    assert row["actual_soa_ms"] == pytest.approx(-100.3)
    assert row["dropped_frames"] == 0
    assert row["presented_at"] is not None


# ------------------------------------------------------------ design_extra


def test_dichotic_extra_is_required(db: Database, session: tuple[int, int]) -> None:
    _, session_id = session
    block_id = db.add_block(
        Block(
            session_id=session_id, module="dichotic", block_index=0, n_trials_planned=1
        )
    )
    with pytest.raises(DesignExtraError):
        db.add_trial(Trial(block_id=block_id, trial_index=0, module="dichotic"))


def test_unknown_extra_key_is_rejected() -> None:
    with pytest.raises(DesignExtraError, match="design_extra"):
        validate_design_extra("gin", {"gap_onsets_s": [1.0], "gap_lengths": [2]})


def test_unknown_module_is_rejected() -> None:
    with pytest.raises(DesignExtraError, match="Bilinmeyen modül"):
        validate_design_extra("telepati", {})


def test_gin_gap_lists_must_line_up() -> None:
    with pytest.raises(DesignExtraError):
        validate_design_extra(
            "gin", {"gap_onsets_s": [1.0, 2.0], "gap_durations_ms": [4.0]}
        )


def test_gin_gaps_must_be_ordered() -> None:
    with pytest.raises(DesignExtraError):
        validate_design_extra(
            "gin", {"gap_onsets_s": [3.0, 1.0], "gap_durations_ms": [4.0, 6.0]}
        )


def test_design_extra_round_trip() -> None:
    raw = validate_design_extra(
        "gin", {"gap_onsets_s": [1.0, 3.5], "gap_durations_ms": [4.0, 12.0]}
    )
    assert parse_design_extra("gin", raw) == {
        "gap_onsets_s": [1.0, 3.5],
        "gap_durations_ms": [4.0, 12.0],
    }


def test_module_without_extras_takes_none(db: Database, session: tuple[int, int]) -> None:
    """``practice`` fits entirely in the shared columns — TBW no longer does,
    since Adım 6 records which speaker the SOA was presented on."""
    _, session_id = session
    block_id = db.add_block(
        Block(
            session_id=session_id, module="practice", block_index=0, n_trials_planned=1
        )
    )
    trial_id = db.add_trial(Trial(block_id=block_id, trial_index=0, module="practice"))
    assert trial_id > 0


def test_tbw_trial_must_say_which_speaker(
    db: Database, session: tuple[int, int]
) -> None:
    _, session_id = session
    block_id = db.add_block(
        Block(session_id=session_id, module="tbw", block_index=0, n_trials_planned=1)
    )
    with pytest.raises(DesignExtraError, match="speaker_id"):
        db.add_trial(
            Trial(
                block_id=block_id,
                trial_index=0,
                module="tbw",
                nominal_soa_ms=0.0,
            )
        )


def test_mcgurk_trial_must_say_which_speaker(
    db: Database, session: tuple[int, int]
) -> None:
    """The config snapshot only pins the speaker down while the strategy is
    ``fixed`` (§F.4), so the trial itself has to carry it."""
    _, session_id = session
    block_id = db.add_block(
        Block(session_id=session_id, module="mcgurk", block_index=0, n_trials_planned=1)
    )
    with pytest.raises(DesignExtraError, match="speaker_id"):
        db.add_trial(Trial(block_id=block_id, trial_index=0, module="mcgurk"))


# --------------------------------------------------------------- flat view


def test_flat_view_joins_everything(db: Database, session: tuple[int, int]) -> None:
    _, session_id = session
    block_id = db.add_block(
        Block(
            session_id=session_id,
            module="dichotic",
            block_index=0,
            n_trials_planned=1,
            label="dichotic-1",
        )
    )
    trial_id = db.add_trial(
        Trial(
            block_id=block_id,
            trial_index=0,
            module="dichotic",
            ear="both",
            design_extra={
                "speaker_id": 1,
                "left_token": "ba",
                "right_token": "da",
            },
        )
    )
    db.add_response(
        Response(
            trial_id=trial_id,
            raw_response="BA",
            category="LEFT",
            rt_from_burst_ms=812.5,
        )
    )
    db.finish_block(block_id, SESSION_COMPLETED)

    rows = db.flat_rows()
    assert len(rows) == 1
    row = rows[0]
    assert row["participant_code"] == "SSD-014"
    assert row["group_code"] == "SSD_L"
    assert row["block_label"] == "dichotic-1"
    # design_extra is expanded into columns, so analysis never parses JSON.
    assert row["dichotic_left_token"] == "ba"
    assert row["dichotic_right_token"] == "da"
    # A dichotic trial carries its speaker too (Adım 7b), through the same
    # column as the other speaker-based modules.
    assert row["speaker_id"] == 1
    assert row["rt_from_burst_ms"] == pytest.approx(812.5)


def test_trial_without_response_still_appears(
    db: Database, session: tuple[int, int]
) -> None:
    # A timeout produces no response row.  Dropping the trial from the flat
    # view would silently bias the data.
    _, session_id = session
    block_id = db.add_block(
        Block(session_id=session_id, module="mcgurk", block_index=0, n_trials_planned=1)
    )
    db.add_trial(
        Trial(
            block_id=block_id,
            trial_index=0,
            module="mcgurk",
            design_extra={"speaker_id": 1},
        )
    )
    db.finish_block(block_id, SESSION_COMPLETED)

    rows = db.flat_rows()
    assert len(rows) == 1
    assert rows[0]["response_id"] is None


def test_multiple_responses_per_trial(db: Database, session: tuple[int, int]) -> None:
    # A GIN segment can hold three gaps and therefore three key presses.
    _, session_id = session
    block_id = db.add_block(
        Block(session_id=session_id, module="gin", block_index=0, n_trials_planned=1)
    )
    trial_id = db.add_trial(
        Trial(
            block_id=block_id,
            trial_index=0,
            module="gin",
            ear="right",
            design_extra={
                "gap_onsets_s": [1.0, 3.0, 5.0],
                "gap_durations_ms": [4.0, 10.0, 20.0],
            },
        )
    )
    for index in range(3):
        db.add_response(
            Response(
                trial_id=trial_id,
                response_index=index,
                raw_response="space",
                rt_from_burst_ms=200.0 + index,
            )
        )
    db.finish_block(block_id, SESSION_COMPLETED)

    rows = db.flat_rows(session_id)
    assert len(rows) == 3
    assert [row["response_index"] for row in rows] == [0, 1, 2]


def test_response_index_is_unique_per_trial(
    db: Database, session: tuple[int, int]
) -> None:
    _, session_id = session
    block_id = db.add_block(
        Block(session_id=session_id, module="gin", block_index=0, n_trials_planned=1)
    )
    trial_id = db.add_trial(
        Trial(
            block_id=block_id,
            trial_index=0,
            module="gin",
            design_extra={"gap_onsets_s": [], "gap_durations_ms": []},
        )
    )
    db.add_response(Response(trial_id=trial_id, response_index=0))
    with pytest.raises(sqlite3.IntegrityError):
        db.add_response(Response(trial_id=trial_id, response_index=0))


# ------------------------------------------------------ counts and helpers


def test_counts_cover_every_table(db: Database, session: tuple[int, int]) -> None:
    counts = db.counts()
    assert counts["participants"] == 1
    assert counts["sessions"] == 1
    assert counts["trials"] == 0


def test_config_snapshot_serialises_paths(db: Database) -> None:
    snapshot = db.snapshot_config({"paths": {"data": Path("data")}, "b": 1})
    assert "data" in snapshot


def test_calibration_import(db: Database, calibration_file: Path) -> None:
    record = calibration_record_from_file(calibration_file)
    calibration_id = db.add_calibration(record)
    assert calibration_id > 0

    latest = db.latest_calibration()
    assert latest is not None
    assert latest["k_mean_db"] == 80.9
    # The verbatim file is kept so the session stays auditable after the
    # calibration file is overwritten.
    assert "K_ortalama" in latest["raw_json"]
