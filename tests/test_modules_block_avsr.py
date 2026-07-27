"""The AVSR trial loop against real hardware, with a scripted keyboard.

Marked ``psychopy``: it opens a window and a sound device, so CI skips it.  It
covers the part of Modül 2 that the CI tests cannot reach — that the three
presentation modes really do present what they claim, that a scored module
writes ``is_correct``, and that the shared loop in ``block.py`` behaves the
same for AVSR as it does for McGurk.

Timing quality is not asserted here; ``tools/timing_selftest.py`` measures that.
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
from mcgurk.modules.avsr import (
    AUDIO_ONLY,
    AUDIOVISUAL,
    VISUAL_ONLY,
    accuracy_by_mode,
    plan_trials,
)
from mcgurk.modules.block import run_avsr
from mcgurk.stimuli import manifest as manifest_module

pytestmark = pytest.mark.psychopy

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: Response keys of the shipped AVSR config: "1" is BA, "2" is DA.
KEY_BA = "1"
KEY_DA = "2"


@pytest.fixture(scope="module")
def config() -> Any:
    configuration = load_config(project_root=PROJECT_ROOT)
    # Field by field rather than a fresh DisplayConfig: the boundary test
    # reloads the schema module, after which the class this file imported is no
    # longer the one ExperimentConfig validates against (Adım 4 note).
    configuration.display.fullscreen = False
    configuration.display.size = (800, 600)
    module = configuration.modules.avsr
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
    return plan_trials(config, manifest, seed=5, stimuli_root=root)


@pytest.fixture(scope="module")
def speaker(hardware_speaker: Any) -> Any:
    return hardware_speaker


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "avsr.sqlite")
    yield database
    database.close()


@pytest.fixture
def session(db: Database, config: Any) -> int:
    participant_id = db.add_participant(
        Participant(
            participant_code="TEST-AVSR", group_code="CTRL", age=30, sex="UNDISCLOSED"
        )
    )
    return db.start_session(
        SessionRecord(
            participant_id=participant_id,
            seed=5,
            config_snapshot="{}",
            config_mode=config.experiment.mode,
            python_version="3.10",
            os_name="test",
        )
    )


def _one_per_mode(planned: list[Any]) -> list[Any]:
    """One trial of each presentation mode, in A / V / AV order."""
    chosen = []
    for mode in (AUDIO_ONLY, VISUAL_ONLY, AUDIOVISUAL):
        chosen.append(
            next(item for item in planned if item.trial.presentation_mode == mode)
        )
    return chosen


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
        return run_avsr(
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


def test_every_presentation_mode_is_presented_and_recorded(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    trials = _one_per_mode(planned)
    outcomes = _run(config, db, session, speaker, trials, [KEY_BA] * len(trials))

    assert outcomes[0].n_presented == len(trials)
    rows = {row["presentation_mode"]: row for row in db.flat_rows(session)}
    assert set(rows) == {AUDIO_ONLY, VISUAL_ONLY, AUDIOVISUAL}

    # A-only never opens a video, V-only never opens a sound — this is the
    # engine path the module is required to use (steps.md §C Adım 5).
    assert rows[AUDIO_ONLY]["video_onset_s"] is None
    assert rows[AUDIO_ONLY]["audio_onset_s"] is not None
    assert rows[VISUAL_ONLY]["audio_onset_s"] is None
    assert rows[VISUAL_ONLY]["video_onset_s"] is not None
    assert rows[AUDIOVISUAL]["video_onset_s"] is not None
    assert rows[AUDIOVISUAL]["audio_onset_s"] is not None

    for row in rows.values():
        assert row["module"] == "avsr"
        assert row["dropped_frames"] is not None
        assert row["avsr_item"] is not None
        assert row["speaker_id"] == config.modules.avsr.speaker_id


def test_a_scored_module_writes_is_correct(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    """Unlike McGurk, AVSR has a right answer — and the database trigger only
    refuses one for ``mcgurk`` and ``dichotic``."""
    ba = next(item for item in planned if item.trial.design_extra["item"] == "ba")
    da = next(item for item in planned if item.trial.design_extra["item"] == "da")
    _run(config, db, session, speaker, [ba, da], [KEY_BA, KEY_BA])

    rows = db.flat_rows(session)
    assert [row["raw_response"] for row in rows] == ["BA", "BA"]
    assert [bool(row["is_correct"]) for row in rows] == [True, False]
    # The percept categories belong to Modül 1; here the score carries it.
    assert [row["category"] for row in rows] == [None, None]
    assert accuracy_by_mode(rows)


def test_both_reaction_times_are_recorded_including_v_only(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    """In V-only there is no acoustic burst, so the RT reference is the visual
    one — without it the mode could not be compared with AV at all."""
    visual = next(
        item for item in planned if item.trial.presentation_mode == VISUAL_ONLY
    )
    _run(config, db, session, speaker, [visual], [KEY_DA])
    row = db.flat_rows(session)[0]
    assert row["rt_from_prompt_ms"] == pytest.approx(250.0, abs=1.0)
    assert row["rt_from_burst_ms"] > row["rt_from_prompt_ms"]
    assert row["rt_from_burst_ms"] < 10_000.0


def test_a_timeout_leaves_no_response_row(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    outcomes = _run(config, db, session, speaker, planned[:1], [None])
    assert outcomes[0].n_timeouts == 1
    assert outcomes[0].n_scored == 0

    rows = db.flat_rows(session)
    assert len(rows) == 1
    assert rows[0]["response_id"] is None
    # The trial is still counted, and counted as incorrect (Adım 5 decision).
    assert accuracy_by_mode(rows)[rows[0]["presentation_mode"]].n_missing == 1
