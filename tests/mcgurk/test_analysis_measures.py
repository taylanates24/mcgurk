"""Adım 9a — wiring each module's measures to the database.

The measurement mathematics is tested in each module's own test file; here the
concern is the orchestration: reading a session's rows and its *config snapshot*,
grouping by module, dispatching to the right measurer, and tolerating a module
whose data is too degenerate to measure.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from mcgurk.analysis.measures import (
    AvsrSummary,
    MeasuresError,
    measure_module,
    session_measures,
)
from mcgurk.config.loader import load_config
from mcgurk.db import Block, Database, Participant, Response, SessionRecord, Trial
from mcgurk.modules.mcgurk import McGurkRates


@pytest.fixture
def config(write_config: Any, config_dict: dict[str, Any]) -> Any:
    return load_config(write_config(config_dict), check_filesystem=False)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "data" / "test.sqlite")
    yield database
    database.close()


def _start_session(db: Database, config: Any, *, seed: int = 7) -> int:
    participant_id = db.add_participant(
        Participant(participant_code="P001", group_code="SSD_R", age=40, sex="M")
    )
    return db.start_session(
        SessionRecord(
            participant_id=participant_id,
            seed=seed,
            config_snapshot=db.snapshot_config(config.model_dump(mode="json")),
            config_mode="development",
            python_version="3.10.20",
            os_name="Windows 11",
        )
    )


def _block(db: Database, session_id: int, module: str) -> int:
    return db.add_block(
        Block(
            session_id=session_id,
            module=module,
            block_index=db.next_block_index(session_id),
            n_trials_planned=0,
        )
    )


# ------------------------------------------------------------- dispatch


def test_mcgurk_rows_are_measured_as_rates(db: Database, config: Any) -> None:
    session_id = _start_session(db, config)
    block_id = _block(db, session_id, "mcgurk")
    for index, (visual, category) in enumerate(
        [("ga", "FUSION"), ("ga", "FUSION"), ("ba", "AUDITORY"), ("da", None)]
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
                Response(trial_id=trial_id, raw_response=category.lower(), category=category)
            )
    db.finish_block(block_id, status="completed")

    measures = session_measures(db, session_id)
    mcgurk = {m.module: m for m in measures.modules}["mcgurk"]
    assert isinstance(mcgurk.data, McGurkRates)
    assert mcgurk.data.n_trials == 4
    assert mcgurk.data.fusion_rate == pytest.approx(0.5)
    assert mcgurk.error is None


def test_avsr_rows_are_measured_as_a_summary(db: Database, config: Any) -> None:
    session_id = _start_session(db, config)
    block_id = _block(db, session_id, "avsr")
    trials = [("AV", True), ("A", False), ("V", True)]
    for index, (mode, correct) in enumerate(trials):
        trial_id = db.add_trial(
            Trial(
                block_id=block_id,
                trial_index=index,
                module="avsr",
                audio_token=None if mode == "V" else "ba",
                presentation_mode=mode,
                ear=None if mode == "V" else "left",
                design_extra={"speaker_id": 1, "stimulus_type": "syllable", "item": "ba"},
            )
        )
        db.add_response(
            Response(trial_id=trial_id, raw_response="ba", category=None, is_correct=correct)
        )
    db.finish_block(block_id, status="completed")

    summary = {m.module: m for m in session_measures(db, session_id).modules}["avsr"]
    assert isinstance(summary.data, AvsrSummary)
    assert summary.data.by_mode["AV"].accuracy == pytest.approx(1.0)
    assert summary.data.by_mode["A"].accuracy == pytest.approx(0.0)
    # AV - A over the same session.
    assert summary.data.visual_benefit == pytest.approx(1.0)
    assert summary.data.lipreading == pytest.approx(1.0)


def test_a_module_that_did_not_run_is_absent(db: Database, config: Any) -> None:
    session_id = _start_session(db, config)
    block_id = _block(db, session_id, "mcgurk")
    trial_id = db.add_trial(
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
    db.add_response(Response(trial_id=trial_id, raw_response="da", category="FUSION"))
    db.finish_block(block_id, status="completed")

    modules = {m.module for m in session_measures(db, session_id).modules}
    assert modules == {"mcgurk"}


def test_a_degenerate_module_records_the_error_but_still_summarises(
    db: Database, config: Any
) -> None:
    """An oddball stream with no target has no hit rate — d' cannot be computed.
    The structured data is None with the reason, but the console text still
    reports the counts rather than crashing the whole session report."""
    session_id = _start_session(db, config)
    block_id = _block(db, session_id, "oddball")
    for index in range(3):
        db.add_trial(
            Trial(
                block_id=block_id,
                trial_index=index,
                module="oddball",
                design_extra={"tone_type": "standard", "tone_hz": 1000.0},
            )
        )
    db.finish_block(block_id, status="completed")

    oddball = {m.module: m for m in session_measures(db, session_id).modules}["oddball"]
    assert oddball.data is None
    assert oddball.error is not None
    assert "Sinyal tespiti" in oddball.summary


# ------------------------------------------------------------- edges


def test_measure_module_is_pure(config: Any) -> None:
    rows: list[object] = [
        {"module": "mcgurk", "trial_id": 1, "response_id": 1, "category": "FUSION",
         "rt_from_burst_ms": 500.0, "snr_db": None, "ear": "left"},
    ]
    measure = measure_module("mcgurk", rows, config, seed=1)
    assert isinstance(measure.data, McGurkRates)
    assert measure.n_trials == 1


def test_unknown_session_is_an_error(db: Database) -> None:
    with pytest.raises(MeasuresError):
        session_measures(db, 999)


def test_summary_text_has_a_header_and_module_sections(db: Database, config: Any) -> None:
    session_id = _start_session(db, config)
    block_id = _block(db, session_id, "mcgurk")
    trial_id = db.add_trial(
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
    db.add_response(Response(trial_id=trial_id, raw_response="da", category="FUSION"))
    db.finish_block(block_id, status="completed")

    text = session_measures(db, session_id).summary_text()
    assert "P001" in text
    assert "McGurk kategorileri" in text
    text.encode("cp1254")  # printable on the Turkish console
