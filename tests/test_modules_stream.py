"""The oddball stream against real hardware, with a keyboard that presses itself.

Marked ``psychopy``: it opens a window and a sound device, so CI skips it.  It
covers what the CI tests cannot reach — that the tones are actually *presented*
at the intervals the design drew, and that a press made during the stream ends
up on the tone it answered, with the reaction time measured from that tone.

The absolute latency of the sound path is not asserted here; only the photodiode
and loopback measurements (docs/01, ``tools/timing_selftest.py --level 2``) can
establish that.  What this file checks is that the software puts the tones and
the presses where the design says.
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
from mcgurk.modules.oddball import OUTSIDE_WINDOW, TARGET, measures_from_rows, plan_trials
from mcgurk.modules.stream import run_oddball
from mcgurk.stimuli import manifest as manifest_module

pytestmark = pytest.mark.psychopy

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEED = 7

#: Enough tones to cross a block boundary twice without costing a minute.
N_TONES = 6


@pytest.fixture(scope="module")
def config() -> Any:
    configuration = load_config(project_root=PROJECT_ROOT)
    # Field by field rather than a fresh DisplayConfig: the boundary test
    # reloads the schema module, after which the class this file imported is no
    # longer the one ExperimentConfig validates against (Adım 4 note).
    configuration.display.fullscreen = False
    configuration.display.size = (800, 600)
    configuration.modules.oddball.lead_in_s = 0.3
    # Three tones per block, so the run crosses a block boundary and the press
    # that arrives after one has been committed still has to land correctly.
    configuration.session.break_every_n_trials = 3
    return configuration


@pytest.fixture(scope="module")
def planned(config: Any) -> list[Any]:
    root = resolve_path(PROJECT_ROOT, config.paths.stimuli)
    try:
        manifest = manifest_module.load(root)
    except Exception as exc:  # noqa: BLE001 - any failure means "not prepared"
        pytest.skip(f"Hazırlanmış uyaran seti yok: {exc}")
    return plan_trials(config, manifest, seed=SEED, stimuli_root=root)[:N_TONES]


@pytest.fixture(scope="module")
def speaker(hardware_speaker: Any) -> Any:
    return hardware_speaker


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "oddball.sqlite")
    yield database
    database.close()


@pytest.fixture
def session(db: Database, config: Any) -> int:
    participant_id = db.add_participant(
        Participant(
            participant_code="TEST-ODD", group_code="CTRL", age=30, sex="UNDISCLOSED"
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


def _onset_offsets(config: Any, planned: list[Any]) -> list[float]:
    """When each tone sounds, in seconds from the keyboard's clock reset."""
    offsets = [config.modules.oddball.lead_in_s]
    for item in planned[1:]:
        offsets.append(offsets[-1] + float(item.trial.design_extra["isi_ms"]) / 1000.0)
    return offsets


def _run(
    config: Any,
    db: Database,
    session_id: int,
    speaker: Any,
    planned: list[Any],
    schedule_s: list[float],
) -> tuple[list[Any], StreamKeyboard]:
    win = open_window(config.display)
    kb = StreamKeyboard(schedule_s, key=config.modules.oddball.response_key)
    try:
        params = TimingParams(
            frame_period_s=1.0 / config.display.expected_refresh_hz,
            lead_frames=config.timing.lead_frames,
            system_av_offset_ms=config.timing.system_av_offset_ms or 0.0,
            dropped_frame_tolerance=config.timing.dropped_frame_tolerance,
        )
        outcomes = run_oddball(
            config=config,
            db=db,
            session_id=session_id,
            planned=planned,
            win=win,
            kb=kb,
            params=params,
            speaker=speaker,
            fixation=make_fixation(win),
        )
        return outcomes, kb
    finally:
        win.close()


def test_the_tones_arrive_at_the_intervals_the_design_drew(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    """The whole module is a stream, so the thing to check is the stream: the
    realised intervals have to be the nominal ones, over the whole run rather
    than tone by tone — a schedule that re-references itself would drift."""
    outcomes, _ = _run(config, db, session, speaker, planned, [])
    assert sum(outcome.n_presented for outcome in outcomes) == N_TONES
    assert [outcome.status for outcome in outcomes] == ["completed"] * len(outcomes)

    rows = sorted(db.flat_rows(session), key=lambda row: row["trial_index"])
    assert len(rows) == N_TONES
    assert [row["module"] for row in rows] == ["oddball"] * N_TONES
    assert all(row["presentation_mode"] == "A" for row in rows)
    assert all(row["video_onset_s"] is None for row in rows)
    assert all(row["response_id"] is None for row in rows)

    nominal = [float(item.trial.design_extra["isi_ms"]) for item in planned[1:]]
    realised = [
        (later["audio_onset_s"] - earlier["audio_onset_s"]) * 1000.0
        for earlier, later in zip(rows, rows[1:], strict=False)
    ]
    assert realised == pytest.approx(nominal, abs=1.0)


def test_a_press_lands_on_the_tone_it_answered(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    """One press 300 ms after the fourth tone.  Fourth on purpose: it is in the
    second block, so the tone it answers was scheduled before its own block row
    existed and the attribution still has to find it."""
    offsets = _onset_offsets(config, planned)
    outcomes, kb = _run(config, db, session, speaker, planned, [offsets[3] + 0.3])
    assert kb.delivered, "tuş basımı hiç teslim edilmedi"

    answered = [row for row in db.flat_rows(session) if row["response_id"] is not None]
    assert len(answered) == 1
    row = answered[0]
    assert row["trial_index"] == 3
    assert row["category"] is None
    assert row["rt_from_burst_ms"] == pytest.approx(300.0, abs=25.0)
    # There is no response prompt in a stream, so the second RT reference is
    # not applicable rather than zero.
    assert row["rt_from_prompt_ms"] is None
    assert row["raw_response"] == config.modules.oddball.response_key

    # Scored against the tone: a press on a target is correct, on a standard it
    # is a false alarm.  The database allows both here — unlike mcgurk/tbw.
    is_target = planned[3].trial.design_extra["tone_type"] == TARGET
    assert bool(row["is_correct"]) is is_target

    # The operator's live tally counts presses, not detection outcomes: a miss
    # is the absence of one and cannot be counted as it happens.
    tallied = sum(sum(outcome.categories.values()) for outcome in outcomes)
    assert tallied == 1


def test_a_press_after_its_block_closed_is_still_recorded(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    """A press 700 ms after the last tone of a block arrives while the next
    block is already running — the block that owns the tone has been committed.

    It is written anyway, against its own tone, and committed with the next
    block.  Losing it would mean the hit rate depended on where the block
    boundaries happened to fall.
    """
    offsets = _onset_offsets(config, planned)
    # Tone 2 is the last of the first block (break_every_n_trials = 3).
    _run(config, db, session, speaker, planned, [offsets[2] + 0.7])

    answered = [row for row in db.flat_rows(session) if row["response_id"] is not None]
    assert len(answered) == 1
    assert answered[0]["trial_index"] == 2
    assert answered[0]["rt_from_burst_ms"] == pytest.approx(700.0, abs=25.0)
    assert answered[0]["category"] is None


def test_a_press_outside_the_window_is_recorded_but_not_scored(
    config: Any, db: Database, session: int, speaker: Any, planned: list[Any]
) -> None:
    """850 ms after a tone is past the 800 ms window: kept, so a participant
    pressing at random is visible, but outside every rate."""
    offsets = _onset_offsets(config, planned)
    _run(config, db, session, speaker, planned, [offsets[1] + 0.85])

    rows = db.flat_rows(session)
    answered = [row for row in rows if row["response_id"] is not None]
    assert len(answered) == 1
    assert answered[0]["trial_index"] == 1
    assert answered[0]["category"] == OUTSIDE_WINDOW
    assert answered[0]["is_correct"] is None

    # It changes no detection outcome, and it is counted.
    measures = measures_from_rows(rows)
    assert measures.counts.outside_window == 1
    assert measures.counts.hits == 0
    assert measures.counts.false_alarms == 0
