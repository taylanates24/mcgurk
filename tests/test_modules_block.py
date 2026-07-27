"""The McGurk trial loop against real hardware, with a scripted keyboard.

Marked ``psychopy``: it opens a window and a sound device, so CI skips it.  The
keyboard is the one part that is faked — a test cannot press a key (see
``tests/scripted_keyboard.py``) — and faking it is what makes the rest
checkable: that the fixation, the presentation, the response and the database
writes happen in that order, that both reaction times are recorded, that a
timeout leaves no response row, and that the block closes (and therefore
commits) exactly once.

Timing quality is not asserted here.  This runs in a small non-fullscreen window
where vsync is not guaranteed; ``tools/timing_selftest.py`` is what measures
timing, with an operator.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from scripted_keyboard import ScriptedKeyboard

from mcgurk.config.loader import load_config, resolve_path
from mcgurk.db.database import Database
from mcgurk.db.models import SESSION_COMPLETED, Participant, SessionRecord
from mcgurk.engine.av_presenter import AVPresenter
from mcgurk.engine.scheduling import TimingParams
from mcgurk.engine.window import make_fixation, open_window
from mcgurk.modules.block import run_mcgurk
from mcgurk.modules.mcgurk import plan_trials
from mcgurk.stimuli import manifest as manifest_module

pytestmark = pytest.mark.psychopy

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: Two response keys from the shipped config: "1" is BA, "2" is DA.
KEY_BA = "1"
KEY_DA = "2"


# --------------------------------------------------------------------- fixtures


@pytest.fixture(scope="module")
def config() -> Any:
    configuration = load_config(project_root=PROJECT_ROOT)
    # A small window: this test is about the loop, not about timing, and a
    # fullscreen window would take over the machine running the suite.
    #
    # Field by field, not by assigning a fresh ``DisplayConfig``: the boundary
    # test reloads ``mcgurk.config.schema``, after which the class this module
    # imported is no longer the one ``ExperimentConfig`` validates against, and
    # the assignment fails with a confusing "not a valid DisplayConfig".
    configuration.display.fullscreen = False
    configuration.display.size = (800, 600)
    module = configuration.modules.mcgurk
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
    return plan_trials(config, manifest, seed=1, stimuli_root=root)


@pytest.fixture(scope="module")
def speaker(hardware_speaker: Any) -> Any:
    """The session's shared device — see ``tests/conftest.py``."""
    return hardware_speaker


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "block.sqlite")
    yield database
    database.close()


@pytest.fixture
def session(db: Database, config: Any) -> int:
    participant_id = db.add_participant(
        Participant(
            participant_code="TEST-BLOCK", group_code="CTRL", age=30, sex="UNDISCLOSED"
        )
    )
    return db.start_session(
        SessionRecord(
            participant_id=participant_id,
            seed=1,
            config_snapshot="{}",
            config_mode=config.experiment.mode,
            python_version="3.10",
            os_name="test",
        )
    )


def _run(
    config: Any,
    db: Database,
    session_id: int,
    speaker: Any,
    planned: list[Any],
    script: list[str | None],
) -> tuple[list[Any], Path]:
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
        outcomes = run_mcgurk(
            config=config,
            db=db,
            session_id=session_id,
            presenter=presenter,
            win=win,
            kb=ScriptedKeyboard(script),
            planned=planned,
        )
    finally:
        win.close()
    return outcomes, db.path


# ------------------------------------------------------------------- the tests


def test_a_short_block_is_recorded_end_to_end(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    trials = planned[:2]
    outcomes, _ = _run(config, db, session, speaker, trials, [KEY_BA, KEY_DA])

    assert len(outcomes) == 1
    assert outcomes[0].n_presented == 2
    assert outcomes[0].n_timeouts == 0
    assert outcomes[0].status == SESSION_COMPLETED

    rows = db.flat_rows(session)
    assert len(rows) == 2
    for row, item in zip(rows, trials, strict=True):
        assert row["module"] == "mcgurk"
        assert row["visual_token"] == item.trial.visual_token
        assert row["audio_token"] == item.trial.audio_token
        assert row["presentation_mode"] == "AV"
        assert row["speaker_id"] == item.trial.design_extra["speaker_id"]
        assert row["noise_instance"] == item.trial.design_extra["noise_instance"]
        # Realised timing (§A.4) is written for every trial.
        assert row["video_onset_s"] is not None
        assert row["audio_onset_s"] is not None
        assert row["actual_soa_ms"] is not None
        assert row["dropped_frames"] is not None
        # §A.10 — no correct answer in this module.
        assert row["is_correct"] is None


def test_both_reaction_times_are_recorded(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    _run(config, db, session, speaker, planned[:1], [KEY_BA])
    row = db.flat_rows(session)[0]

    assert row["rt_from_prompt_ms"] == pytest.approx(250.0, abs=1.0)
    # The burst reference includes the stimulus that played before the prompt,
    # so it is necessarily the larger of the two — by about the length of the
    # video after the burst.
    assert row["rt_from_burst_ms"] > row["rt_from_prompt_ms"]
    assert row["rt_from_burst_ms"] < 10_000.0


def test_the_response_is_categorised_from_the_config_maps(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    fusion = next(
        item for item in planned if item.trial.condition_label == "fusion_pair"
    )
    _run(config, db, session, speaker, [fusion], [KEY_DA])
    row = db.flat_rows(session)[0]
    assert row["raw_response"] == "DA"
    assert row["category"] == "FUSION"


def test_a_timeout_leaves_no_response_row(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    outcomes, _ = _run(config, db, session, speaker, planned[:1], [None])
    assert outcomes[0].n_timeouts == 1
    assert outcomes[0].categories["NONE"] == 1

    rows = db.flat_rows(session)
    assert len(rows) == 1
    # The trial is still there — dropping it would silently bias the data.
    assert rows[0]["response_id"] is None
    assert rows[0]["video_onset_s"] is not None


def test_the_block_commits_at_its_boundary(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    """§A.5: nothing reaches disk during the trials, everything after them."""
    _, path = _run(config, db, session, speaker, planned[:2], [KEY_BA, KEY_BA])
    other = sqlite3.connect(path)
    try:
        assert other.execute("SELECT COUNT(*) FROM trials").fetchone()[0] == 2
        assert (
            other.execute(
                "SELECT status FROM blocks WHERE session_id = ?", (session,)
            ).fetchone()[0]
            == SESSION_COMPLETED
        )
    finally:
        other.close()


def test_a_long_module_is_split_into_several_blocks(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    """The commit boundary is ``session.break_every_n_trials``, which is also
    where Adım 8 will put the break screens."""
    config.session.break_every_n_trials = 2
    try:
        outcomes, _ = _run(
            config, db, session, speaker, planned[:3], [KEY_BA, KEY_BA, KEY_DA]
        )
    finally:
        config.session.break_every_n_trials = 60

    assert [outcome.n_planned for outcome in outcomes] == [2, 1]
    assert [outcome.block_index for outcome in outcomes] == [0, 1]
    # Trial indices keep running across the blocks, so the order within the
    # module stays readable in the data.
    rows = db.flat_rows(session)
    assert [row["trial_index"] for row in rows] == [0, 1, 2]
