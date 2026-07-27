"""The TBW trial loop against real hardware, with a scripted keyboard.

Marked ``psychopy``: it opens a window and a sound device, so CI skips it.  It
covers what the CI tests cannot reach — that an SOA is actually *presented* as
one, in both directions, and that the trial is recorded with no correct answer.

The absolute A/V latency is not asserted here; only the photodiode measurement
(docs/01) can establish that, and what this file checks is that the software
puts the two streams where the design says.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from scripted_keyboard import ScriptedKeyboard

from mcgurk.config.loader import load_config, resolve_path
from mcgurk.db.database import Database
from mcgurk.db.models import Participant, SessionRecord
from mcgurk.engine.av_presenter import AVPresenter
from mcgurk.engine.scheduling import TimingParams
from mcgurk.engine.window import make_fixation, open_window
from mcgurk.modules.block import run_tbw
from mcgurk.modules.tbw import DIFFERENT, SAME, plan_trials, psychometric_points
from mcgurk.stimuli import manifest as manifest_module

pytestmark = pytest.mark.psychopy

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: Response keys of the shipped TBW config: "1" is "Aynı anda", "2" is not.
KEY_SAME = "1"
KEY_DIFFERENT = "2"


@pytest.fixture(scope="module")
def config() -> Any:
    configuration = load_config(project_root=PROJECT_ROOT)
    # Field by field rather than a fresh DisplayConfig: the boundary test
    # reloads the schema module, after which the class this file imported is no
    # longer the one ExperimentConfig validates against (Adım 4 note).
    configuration.display.fullscreen = False
    configuration.display.size = (800, 600)
    module = configuration.modules.tbw
    module.response_timeout_s = 0.6
    module.fixation_duration_ms = 100.0
    module.post_response_ms = 0.0
    return configuration


@pytest.fixture(scope="module")
def planned(config: Any) -> list[Any]:
    root = resolve_path(PROJECT_ROOT, config.paths.stimuli)
    try:
        manifest = manifest_module.load(root)
    except Exception as exc:  # noqa: BLE001 - any failure means "not prepared"
        pytest.skip(f"Hazırlanmış uyaran seti yok: {exc}")
    return plan_trials(config, manifest, seed=6, stimuli_root=root)


@pytest.fixture(scope="module")
def speaker(hardware_speaker: Any) -> Any:
    return hardware_speaker


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "tbw.sqlite")
    yield database
    database.close()


@pytest.fixture
def session(db: Database, config: Any) -> int:
    participant_id = db.add_participant(
        Participant(
            participant_code="TEST-TBW", group_code="CTRL", age=30, sex="UNDISCLOSED"
        )
    )
    return db.start_session(
        SessionRecord(
            participant_id=participant_id,
            seed=6,
            config_snapshot="{}",
            config_mode=config.experiment.mode,
            python_version="3.10",
            os_name="test",
        )
    )


def _at_soa(planned: list[Any], soa_ms: float) -> Any:
    return next(item for item in planned if item.trial.nominal_soa_ms == soa_ms)


def _run(
    config: Any,
    db: Database,
    session_id: int,
    speaker: Any,
    trials: list[Any],
    script: list[str | None],
) -> list[Any]:
    win = open_window(config.display)
    try:
        params = TimingParams(
            frame_period_s=1.0 / config.display.expected_refresh_hz,
            lead_frames=config.timing.lead_frames,
            system_av_offset_ms=config.timing.system_av_offset_ms or 0.0,
            dropped_frame_tolerance=config.timing.dropped_frame_tolerance,
        )
        presenter = AVPresenter(
            win,
            params,
            speaker=speaker,
            sample_rate=config.audio.sample_rate,
            alignment_tolerance_ms=config.stimulus_prep.burst.alignment_tolerance_ms,
            fixation=make_fixation(win),
        )
        return run_tbw(
            config=config,
            db=db,
            session_id=session_id,
            presenter=presenter,
            win=win,
            kb=ScriptedKeyboard(script),
            planned=trials,
        )
    finally:
        win.close()


def test_both_soa_directions_are_presented_and_recorded(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    """The whole module is one manipulation: when the sound arrives relative to
    the face.  A negative SOA has to put the audio *first*, which the engine
    pays for with presentation lead."""
    widest = min(config.modules.tbw.soa_values_ms)
    trials = [_at_soa(planned, widest), _at_soa(planned, 0.0), _at_soa(planned, -widest)]
    outcomes = _run(
        config, db, session, speaker, trials, [KEY_DIFFERENT, KEY_SAME, KEY_DIFFERENT]
    )
    assert outcomes[0].n_presented == 3

    rows = {row["nominal_soa_ms"]: row for row in db.flat_rows(session)}
    assert set(rows) == {widest, 0.0, -widest}
    for soa_ms, row in rows.items():
        assert row["module"] == "tbw"
        assert row["video_onset_s"] is not None
        assert row["audio_onset_s"] is not None
        # The experienced SOA is measured between the two acoustic bursts and
        # carries the system offset; a frame of slack is the flip grid.
        assert row["actual_soa_ms"] == pytest.approx(soa_ms, abs=25.0)

    # A negative SOA means the audio really started before the video.
    assert rows[widest]["audio_onset_s"] < rows[widest]["video_onset_s"]
    assert rows[-widest]["audio_onset_s"] > rows[-widest]["video_onset_s"]


def test_a_judgement_is_recorded_with_no_correct_answer(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    """§A.10 — and the database refuses ``is_correct`` on a ``tbw`` trial, so a
    module that tried to score one would fail here rather than in the data."""
    trials = [_at_soa(planned, 0.0), _at_soa(planned, 300.0)]
    outcomes = _run(config, db, session, speaker, trials, [KEY_SAME, KEY_DIFFERENT])

    rows = db.flat_rows(session)
    assert [row["category"] for row in rows] == [SAME, DIFFERENT]
    assert [row["is_correct"] for row in rows] == [None, None]
    assert [row["raw_response"] for row in rows] == [
        config.modules.tbw.response_labels["same"],
        config.modules.tbw.response_labels["different"],
    ]
    assert outcomes[0].n_scored == 0
    assert outcomes[0].categories[SAME] == 1

    # Both RT references land, and the burst one is the later of the two.
    for row in rows:
        assert row["rt_from_prompt_ms"] == pytest.approx(250.0, abs=1.0)
        assert row["rt_from_burst_ms"] > row["rt_from_prompt_ms"]


def test_a_timeout_leaves_no_response_row_and_no_point_on_the_curve(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    """A timeout is a missing observation here, not a "different" judgement."""
    outcomes = _run(config, db, session, speaker, planned[:1], [None])
    assert outcomes[0].n_timeouts == 1

    rows = db.flat_rows(session)
    assert len(rows) == 1
    assert rows[0]["response_id"] is None

    point = psychometric_points(rows)[0]
    assert point.n_responded == 0
    assert point.n_missing == 1
    assert point.p_same is None
