"""The GIN stream runner against real hardware, with a scripted keyboard.

Marked ``psychopy``: it opens a window and a sound device, so CI skips it.  It
covers what the CI tests cannot reach — that a six-second segment is actually
presented, that a press made *inside* it lands on the gap it followed, that a
press in a catch segment is written as a false alarm, and that a gap nobody
answered leaves no row behind.

What no automated test can establish is whether the gaps are audible at all.
That is a listening test and it is in ``TEST_ADIM_7C.md``.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from scripted_keyboard import StreamKeyboard

from mcgurk.config.loader import load_config, resolve_path
from mcgurk.db.database import Database
from mcgurk.db.models import Participant, SessionRecord
from mcgurk.engine.scheduling import TimingParams
from mcgurk.engine.window import make_fixation, open_window
from mcgurk.modules.gin import FALSE_ALARM, HIT, measures_from_rows, plan_trials
from mcgurk.modules.stream import run_gin
from mcgurk.stimuli import manifest as manifest_module

pytestmark = pytest.mark.psychopy

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEED = 11


@pytest.fixture(scope="module")
def config() -> Any:
    configuration = load_config(project_root=PROJECT_ROOT)
    # Field by field rather than a fresh DisplayConfig: the boundary test
    # reloads the schema module, after which the class this file imported is no
    # longer the one ExperimentConfig validates against (Adım 4 note).
    configuration.display.fullscreen = False
    configuration.display.size = (800, 600)
    # The segments are 6 s each and there is no shortening them — they are
    # prepared files — so these tests present two or three of them, not thirty.
    configuration.modules.gin.lead_in_s = 0.5
    return configuration


@pytest.fixture(scope="module")
def planned(config: Any) -> list[Any]:
    root = resolve_path(PROJECT_ROOT, config.paths.stimuli)
    try:
        manifest = manifest_module.load(root)
    except Exception as exc:  # noqa: BLE001 - any failure means "not prepared"
        pytest.skip(f"Hazırlanmış uyaran seti yok: {exc}")
    return plan_trials(
        config, manifest, seed=SEED, stimuli_root=root, ear="right"
    )


@pytest.fixture(scope="module")
def speaker(hardware_speaker: Any) -> Any:
    return hardware_speaker


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "gin.sqlite")
    yield database
    database.close()


@pytest.fixture
def session(db: Database, config: Any) -> int:
    participant_id = db.add_participant(
        Participant(
            participant_code="TEST-GIN", group_code="CTRL", age=30, sex="UNDISCLOSED"
        )
    )
    return db.start_session(
        SessionRecord(
            participant_id=participant_id,
            seed=SEED,
            config_snapshot="{}",
            config_mode=config.experiment.mode,
            python_version="3.10",
            os_name="test",
        )
    )


def _with_gaps(planned: list[Any], n_gaps: int) -> Any:
    for item in planned:
        if len(item.trial.design_extra["gap_onsets_s"]) == n_gaps:
            return item
    pytest.skip(f"Hazırlanmış sette {n_gaps} boşluklu segment yok")


def _run(
    config: Any,
    db: Database,
    session_id: int,
    speaker: Any,
    trials: list[Any],
    schedule_s: list[float],
) -> tuple[list[Any], StreamKeyboard]:
    """Present *trials*, pressing the key at *schedule_s* after the run's start."""
    win = open_window(config.display)
    kb = StreamKeyboard(schedule_s, key=config.modules.gin.response_key)
    try:
        params = TimingParams(
            frame_period_s=1.0 / config.display.expected_refresh_hz,
            lead_frames=config.timing.lead_frames,
            system_av_offset_ms=config.timing.system_av_offset_ms or 0.0,
            dropped_frame_tolerance=config.timing.dropped_frame_tolerance,
        )
        outcomes = run_gin(
            config=config,
            db=db,
            session_id=session_id,
            planned=trials,
            win=win,
            kb=kb,
            params=params,
            speaker=speaker,
            calibration=None,
            fixation=make_fixation(win),
        )
        return outcomes, kb
    finally:
        win.close()


def test_a_press_lands_on_the_gap_it_followed(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    """The whole module rests on this: a segment is one trial, and which gap was
    detected is recorded per response."""
    item = _with_gaps(planned, 1)
    gap_s = item.trial.design_extra["gap_onsets_s"][0]
    # The run starts after lead_in_s, so a press 300 ms after the gap is at
    # lead_in + gap + 0.3 on the keyboard clock.
    press_at = config.modules.gin.lead_in_s + gap_s + 0.3

    outcomes, _ = _run(config, db, session, speaker, [item], [press_at])
    assert outcomes[0].n_presented == 1
    assert outcomes[0].categories[HIT] == 1

    rows = [row for row in db.flat_rows(session) if row["response_id"] is not None]
    assert len(rows) == 1
    row = rows[0]
    assert row["module"] == "gin"
    assert row["category"] == HIT
    assert row["event_index"] == 0
    assert row["rt_from_burst_ms"] == pytest.approx(300.0, abs=60.0)
    # A stream has no response prompt, so the second reference is not
    # applicable rather than zero.
    assert row["rt_from_prompt_ms"] is None
    # There is no correct answer to record: the category already says it.
    assert row["is_correct"] is None
    assert row["ear"] == "right"
    assert row["gin_segment_index"] == item.trial.design_extra["segment_index"]


def test_a_gap_nobody_answered_leaves_no_row(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    """A miss is the absence of a press; inventing a row for it would put the
    analyst's reading into the data.  The trial itself still appears."""
    item = _with_gaps(planned, 1)
    _run(config, db, session, speaker, [item], [])

    rows = db.flat_rows(session)
    assert len(rows) == 1
    assert rows[0]["response_id"] is None

    measures = measures_from_rows(rows, config.modules.gin)
    assert measures.n_gaps == 1
    assert measures.n_detected == 0
    assert measures.n_false_alarms == 0


def test_a_press_in_a_catch_segment_is_a_false_alarm(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    """The segment with no gaps is what the false-alarm rate is measured
    against."""
    item = _with_gaps(planned, 0)
    press_at = config.modules.gin.lead_in_s + 2.0

    outcomes, _ = _run(config, db, session, speaker, [item], [press_at])
    assert outcomes[0].categories[FALSE_ALARM] == 1

    rows = [row for row in db.flat_rows(session) if row["response_id"] is not None]
    assert len(rows) == 1
    assert rows[0]["category"] == FALSE_ALARM
    # It followed no gap, so there is nothing to index and nothing to measure
    # the reaction time from.
    assert rows[0]["event_index"] is None
    assert rows[0]["rt_from_burst_ms"] is None


def test_a_press_after_the_window_is_a_false_alarm_on_that_segment(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    item = _with_gaps(planned, 1)
    gap_s = item.trial.design_extra["gap_onsets_s"][0]
    late = config.modules.gin.response_window_ms[1] / 1000.0 + 0.3
    press_at = config.modules.gin.lead_in_s + gap_s + late

    _run(config, db, session, speaker, [item], [press_at])

    rows = [row for row in db.flat_rows(session) if row["response_id"] is not None]
    assert len(rows) == 1
    assert rows[0]["category"] == FALSE_ALARM
    assert rows[0]["event_index"] is None

    measures = measures_from_rows(db.flat_rows(session), config.modules.gin)
    assert measures.n_detected == 0
    assert measures.n_false_alarms == 1


def test_two_segments_run_back_to_back_on_one_origin(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    """Onsets are cumulative from one origin, so the second segment starts a
    whole segment-plus-interval after the first."""
    trials = planned[:2]
    _run(config, db, session, speaker, trials, [])

    rows = db.flat_rows(session)
    assert len(rows) == 2
    step = (
        config.modules.gin.segment_duration_s
        + config.modules.gin.inter_segment_interval_s
    )
    assert rows[1]["audio_onset_s"] - rows[0]["audio_onset_s"] == pytest.approx(step)
    assert all(row["dropped_frames"] == 0 for row in rows)
