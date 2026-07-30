"""Adım 9b — the quality-control report.

The flagging rule, the timeout accounting and the cross-hearing binomial test
are exercised on synthetic rows; ``session_qc`` is checked against a database
with a real config snapshot so the thresholds come from where they will in a run.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from mcgurk.analysis.qc_report import (
    QCError,
    cross_hearing_qc,
    flag_trials,
    module_qc,
    session_qc,
    timing_summary,
)
from mcgurk.config.loader import load_config
from mcgurk.db import Block, Database, Participant, Response, SessionRecord, Trial
from mcgurk.db.models import TrialTiming


def _trial_row(
    trial_id: int,
    *,
    module: str = "mcgurk",
    trial_index: int = 0,
    dropped_frames: int | None = None,
    actual_soa_ms: float | None = None,
    nominal_soa_ms: float | None = None,
    max_frame_interval_ms: float | None = None,
    response_id: int | None = None,
    category: str | None = None,
    signal_present: int | None = None,
    ear: str | None = None,
) -> dict[str, Any]:
    return {
        "module": module,
        "trial_id": trial_id,
        "trial_index": trial_index,
        "dropped_frames": dropped_frames,
        "actual_soa_ms": actual_soa_ms,
        "nominal_soa_ms": nominal_soa_ms,
        "max_frame_interval_ms": max_frame_interval_ms,
        "response_id": response_id,
        "category": category,
        "cross_hearing_signal_present": signal_present,
        "ear": ear,
    }


# ----------------------------------------------------------------- flagging


def test_a_trial_over_the_dropped_frame_threshold_is_flagged() -> None:
    rows = [_trial_row(1, dropped_frames=5, response_id=1, category="FUSION")]
    flagged = flag_trials(rows, max_dropped_frames=3, soa_tolerance_ms=20.0)
    assert len(flagged) == 1
    assert "düşen kare" in flagged[0].reasons[0]


def test_a_trial_at_the_threshold_is_not_flagged() -> None:
    rows = [_trial_row(1, dropped_frames=3, response_id=1)]
    assert flag_trials(rows, max_dropped_frames=3, soa_tolerance_ms=20.0) == []


def test_a_trial_over_the_soa_tolerance_is_flagged() -> None:
    rows = [_trial_row(1, actual_soa_ms=45.0, nominal_soa_ms=0.0, response_id=1)]
    flagged = flag_trials(rows, max_dropped_frames=3, soa_tolerance_ms=20.0)
    assert len(flagged) == 1
    assert "SOA sapması" in flagged[0].reasons[0]


def test_both_reasons_are_recorded_on_one_trial() -> None:
    rows = [
        _trial_row(1, dropped_frames=9, actual_soa_ms=-60.0, nominal_soa_ms=0.0, response_id=1)
    ]
    flagged = flag_trials(rows, max_dropped_frames=3, soa_tolerance_ms=20.0)
    assert len(flagged[0].reasons) == 2


def test_a_trial_with_no_timing_is_not_flagged() -> None:
    """A trial that never recorded timing (e.g. an aborted stream) has nothing to
    measure against and is left alone rather than flagged."""
    rows = [_trial_row(1, response_id=None)]
    assert flag_trials(rows, max_dropped_frames=3, soa_tolerance_ms=20.0) == []


# ------------------------------------------------------------------ timing


def test_timing_summary_reports_worst_case_numbers() -> None:
    rows = [
        _trial_row(1, dropped_frames=0, actual_soa_ms=1.0, nominal_soa_ms=0.0,
                   max_frame_interval_ms=17.0, response_id=1),
        _trial_row(2, dropped_frames=4, actual_soa_ms=30.0, nominal_soa_ms=0.0,
                   max_frame_interval_ms=41.0, response_id=2),
    ]
    summary = timing_summary(rows)
    assert summary.n_trials == 2
    assert summary.total_dropped_frames == 4
    assert summary.worst_dropped_frames == 4
    assert summary.worst_frame_interval_ms == pytest.approx(41.0)
    assert summary.worst_abs_soa_deviation_ms == pytest.approx(30.0)


# ------------------------------------------------------------------ module


def test_forced_choice_module_reports_a_timeout_rate() -> None:
    rows = [
        _trial_row(1, module="mcgurk", response_id=1, category="FUSION"),
        _trial_row(2, module="mcgurk", response_id=None),  # timeout
    ]
    (mcgurk,) = module_qc(rows)
    assert mcgurk.timeout_rate == pytest.approx(0.5)
    assert mcgurk.n_no_response == 1


def test_a_detection_module_has_no_timeout_rate() -> None:
    """A cross-hearing catch trial with no press is a correct rejection, not a
    timeout, so no timeout rate is reported for it."""
    rows = [
        _trial_row(1, module="cross_hearing", signal_present=0, response_id=None),
        _trial_row(2, module="cross_hearing", signal_present=1, response_id=5, category="HIT"),
    ]
    (cross,) = module_qc(rows)
    assert cross.timeout_rate is None
    assert cross.n_no_response == 1


def test_response_distribution_counts_categories() -> None:
    rows = [
        _trial_row(1, response_id=1, category="FUSION"),
        _trial_row(2, response_id=2, category="FUSION"),
        _trial_row(3, response_id=3, category="AUDITORY"),
    ]
    (mcgurk,) = module_qc(rows)
    assert mcgurk.response_distribution == {"FUSION": 2, "AUDITORY": 1}


# ---------------------------------------------------------- cross-hearing


def _cross_rows(
    signal_hits: int, signal_total: int, fa: int, catch_total: int
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    tid = 1
    for i in range(signal_total):
        pressed = i < signal_hits
        rows.append(_trial_row(tid, module="cross_hearing", signal_present=1, ear="right",
                               response_id=tid if pressed else None,
                               category="HIT" if pressed else None))
        tid += 1
    for i in range(catch_total):
        pressed = i < fa
        rows.append(_trial_row(tid, module="cross_hearing", signal_present=0, ear="right",
                               response_id=tid if pressed else None,
                               category="FALSE_ALARM" if pressed else None))
        tid += 1
    return rows


def test_cross_hearing_above_chance_is_detected() -> None:
    result = cross_hearing_qc(_cross_rows(5, 6, 1, 4), alpha=0.05)
    assert result is not None
    assert result.hits == 5 and result.misses == 1
    assert result.false_alarms == 1 and result.correct_rejections == 3
    assert result.null_p == pytest.approx(0.25)
    assert result.above_chance is True
    assert result.p_value is not None and result.p_value < 0.05


def test_chance_level_detection_is_not_flagged() -> None:
    """Hits no better than the false-alarm rate is chance — not above it."""
    result = cross_hearing_qc(_cross_rows(1, 6, 1, 4), alpha=0.05)
    assert result is not None
    assert result.above_chance is False


def test_no_catch_trials_falls_back_to_half() -> None:
    result = cross_hearing_qc(_cross_rows(6, 6, 0, 0), alpha=0.05)
    assert result is not None
    assert result.null_p == pytest.approx(0.5)


def test_no_cross_hearing_rows_gives_none() -> None:
    rows = [_trial_row(1, module="mcgurk", response_id=1, category="FUSION")]
    assert cross_hearing_qc(rows, alpha=0.05) is None


# ------------------------------------------------------------------ session


@pytest.fixture
def config(write_config: Any, config_dict: dict[str, Any]) -> Any:
    return load_config(write_config(config_dict), check_filesystem=False)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "data" / "test.sqlite")
    yield database
    database.close()


def test_session_qc_uses_snapshot_thresholds(db: Database, config: Any) -> None:
    pid = db.add_participant(
        Participant(participant_code="P001", group_code="SSD_R", age=40, sex="M")
    )
    sid = db.start_session(SessionRecord(
        participant_id=pid, seed=1,
        config_snapshot=db.snapshot_config(config.model_dump(mode="json")),
        config_mode="development", python_version="3.10", os_name="win",
    ))
    block_id = db.add_block(
        Block(session_id=sid, module="mcgurk", block_index=0, n_trials_planned=1)
    )
    trial_id = db.add_trial(Trial(block_id=block_id, trial_index=0, module="mcgurk",
                                  visual_token="ga", audio_token="ba", ear="left",
                                  nominal_soa_ms=0.0, design_extra={"speaker_id": 1}))
    # 5 dropped frames exceeds the shipped qc.max_dropped_frames (3).
    db.set_trial_timing(trial_id, TrialTiming(actual_soa_ms=2.0, dropped_frames=5))
    db.add_response(Response(trial_id=trial_id, raw_response="da", category="FUSION"))
    db.finish_block(block_id, status="completed")

    report = session_qc(db, sid)
    assert report.participant_code == "P001"
    assert len(report.flagged) == 1
    assert report.flagged[0].trial_id == trial_id
    report.summary_text().encode("cp1254")  # printable on the Turkish console


def test_unknown_session_is_an_error(db: Database) -> None:
    with pytest.raises(QCError):
        session_qc(db, 999)
