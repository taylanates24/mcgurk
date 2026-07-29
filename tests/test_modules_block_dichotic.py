"""The dichotic trial loop against real hardware, with a scripted keyboard.

Marked ``psychopy``: it opens a window and a sound device, so CI skips it.  It
covers what the CI tests cannot reach — that a stereo file is presented without
being routed anywhere, that the report is attributed to an ear and recorded with
no correct answer, and that a timeout leaves no response row.

What no automated test can establish is that the *left* channel actually comes
out of the left cup.  That is a listening test and it is in ``TEST_ADIM_7B.md``;
what is checked here is that the software hands the file over untouched.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from scripted_keyboard import ScriptedKeyboard

from mcgurk.config.loader import load_config, resolve_path
from mcgurk.db.database import Database
from mcgurk.db.models import Participant, SessionRecord
from mcgurk.engine.av_presenter import AVPresenter
from mcgurk.engine.scheduling import TimingParams
from mcgurk.engine.window import make_fixation, open_window
from mcgurk.modules.block import run_dichotic
from mcgurk.modules.dichotic import LEFT, OTHER, RIGHT, ear_advantage, plan_trials
from mcgurk.stimuli import manifest as manifest_module

pytestmark = pytest.mark.psychopy

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: Response keys of the shipped dichotic config: BA / DA / GA / DIGER.
KEY_BA = "1"
KEY_DA = "2"
KEY_GA = "3"
KEY_OTHER = "4"
SEED = 7


@pytest.fixture(scope="module")
def config() -> Any:
    configuration = load_config(project_root=PROJECT_ROOT)
    # Field by field rather than a fresh DisplayConfig: the boundary test
    # reloads the schema module, after which the class this file imported is no
    # longer the one ExperimentConfig validates against (Adım 4 note).
    configuration.display.fullscreen = False
    configuration.display.size = (800, 600)
    module = configuration.modules.dichotic
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
    return plan_trials(config, manifest, seed=SEED, stimuli_root=root)


@pytest.fixture(scope="module")
def speaker(hardware_speaker: Any) -> Any:
    return hardware_speaker


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "dichotic.sqlite")
    yield database
    database.close()


@pytest.fixture
def session(db: Database, config: Any) -> int:
    participant_id = db.add_participant(
        Participant(
            participant_code="TEST-DIC", group_code="CTRL", age=30, sex="UNDISCLOSED"
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


def _pair(planned: list[Any], left: str, right: str) -> Any:
    return next(
        item
        for item in planned
        if item.trial.design_extra["left_token"] == left
        and item.trial.design_extra["right_token"] == right
    )


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
        return run_dichotic(
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


def test_a_report_is_attributed_to_an_ear_with_no_correct_answer(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    """§A.10 — and the database refuses ``is_correct`` on a ``dichotic`` trial,
    so a module that tried to score one would fail here rather than in the
    data."""
    trials = [_pair(planned, "ba", "da"), _pair(planned, "ga", "ba")]
    outcomes = _run(config, db, session, speaker, trials, [KEY_BA, KEY_BA])

    rows = db.flat_rows(session)
    assert [row["module"] for row in rows] == ["dichotic", "dichotic"]
    # Same key, different pair: /ba/ is the left token of the first trial and
    # the right token of the second.
    assert [row["category"] for row in rows] == [LEFT, RIGHT]
    assert [row["is_correct"] for row in rows] == [None, None]
    assert [row["raw_response"] for row in rows] == ["BA", "BA"]
    assert outcomes[0].n_scored == 0
    assert outcomes[0].categories[LEFT] == 1
    assert outcomes[0].categories[RIGHT] == 1

    for row in rows:
        # Audio only: no video onset, both ears, no SOA.
        assert row["video_onset_s"] is None
        assert row["audio_onset_s"] is not None
        assert row["ear"] == "both"
        assert row["nominal_soa_ms"] is None
        assert row["presentation_mode"] == "A"
        # Both RT references land, and the burst one is the later of the two.
        assert row["rt_from_prompt_ms"] == pytest.approx(250.0, abs=1.0)
        assert row["rt_from_burst_ms"] > row["rt_from_prompt_ms"]


def test_the_two_tokens_are_recorded_per_trial(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    """``trials.audio_token`` is NULL — there are two of them — and both are
    exposed by ``v_trials_flat`` as columns."""
    trials = [_pair(planned, "da", "ga")]
    _run(config, db, session, speaker, trials, [KEY_GA])

    row = db.flat_rows(session)[0]
    assert row["audio_token"] is None
    assert row["visual_token"] is None
    assert row["dichotic_left_token"] == "da"
    assert row["dichotic_right_token"] == "ga"
    assert row["speaker_id"] == config.modules.dichotic.speaker_id
    assert row["category"] == RIGHT


def test_a_report_matching_neither_syllable_is_an_intrusion(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    """The third syllable and the free-text option both land in OTHER: §6.5's
    "karışım yanıtı" is a report matching neither of the two presented."""
    trials = [_pair(planned, "ba", "da"), _pair(planned, "ba", "ga")]
    outcomes = _run(config, db, session, speaker, trials, [KEY_GA, KEY_OTHER])

    rows = db.flat_rows(session)
    assert [row["category"] for row in rows] == [OTHER, OTHER]
    assert outcomes[0].categories[OTHER] == 2
    # The free-text screen opened for the second trial and nothing was typed
    # into it, which stores NULL rather than an empty string.  Either way the
    # category came from the option that was chosen, never from the text.
    assert [row["free_text"] for row in rows] == [None, None]

    stats = ear_advantage(rows)
    assert stats.n_answered == 2
    assert stats.laterality_index is None


def test_a_timeout_leaves_no_response_row_and_no_report(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    """A missing observation, as in TBW: with no correct answer, assigning it to
    either ear would move the index."""
    outcomes = _run(config, db, session, speaker, planned[:1], [None])
    assert outcomes[0].n_timeouts == 1

    rows = db.flat_rows(session)
    assert len(rows) == 1
    assert rows[0]["response_id"] is None

    stats = ear_advantage(rows)
    assert stats.n_trials == 1
    assert stats.n_missing == 1
    assert stats.n_answered == 0
    assert stats.laterality_index is None


def test_the_stereo_file_reaches_the_device_unrouted(
    config: Any, planned: list[Any], speaker: Any
) -> None:
    """The lateralisation is inside the file, so nothing may re-route it.

    Loaded through the same path a trial uses: two channels, both carrying
    signal, and different from each other — which is what makes the trial
    dichotic rather than diotic.
    """
    from mcgurk.engine.audio import load_audio

    item = _pair(planned, "ba", "da")
    stimulus = load_audio(
        item.spec.audio_path,
        ear=item.spec.ear,
        burst_time_s=item.spec.audio_burst_s,
        expected_sample_rate=config.audio.sample_rate,
    )
    samples = stimulus.samples
    assert samples.ndim == 2 and samples.shape[1] == 2
    assert np.max(np.abs(samples[:, 0])) > 0.01
    assert np.max(np.abs(samples[:, 1])) > 0.01
    assert not np.allclose(samples[:, 0], samples[:, 1])
