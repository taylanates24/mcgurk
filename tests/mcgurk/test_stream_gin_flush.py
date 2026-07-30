"""Where a GIN press ends up in the database — without hardware.

``stream.py`` imports PsychoPy only inside its loops, so the part that turns a
buffer of press timestamps into ``responses`` rows is reachable in CI.  That is
the part worth testing here: it decides which *segment* a press belongs to and
then which *gap* inside it, and both decisions are invisible in a hardware test
that can only check the row that came out.

The loop itself (scheduling, holding the screen, reading the backend) is in
``tests/test_modules_stream_gin.py``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from mcgurk.config.loader import load_config
from mcgurk.db.database import Database
from mcgurk.db.models import Block, Participant, SessionRecord, Trial
from mcgurk.engine.av_presenter import TrialSpec
from mcgurk.modules.base import PlannedTrial
from mcgurk.modules.block import BlockOutcome
from mcgurk.modules.gin import FALSE_ALARM, HIT
from mcgurk.modules.stream import _flush_gin, _FlushState

SEGMENT_S = 6.0
INTERVAL_S = 2.0
STEP_S = SEGMENT_S + INTERVAL_S
START_S = 100.0


@pytest.fixture
def config(write_config: Any, config_dict: dict[str, Any]) -> Any:
    return load_config(write_config(config_dict), check_filesystem=False)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "gin.sqlite")
    yield database
    database.close()


def _segment(index: int, onsets: list[float], durations: list[float]) -> PlannedTrial:
    return PlannedTrial(
        spec=TrialSpec(label=f"segment {index}", audio_path=Path("x.wav"), ear="right"),
        trial=Trial(
            block_id=0,
            trial_index=0,
            module="gin",
            condition_label=f"segment {index}",
            ear="right",
            presentation_mode="A",
            design_extra={
                "segment_index": index,
                "gap_onsets_s": onsets,
                "gap_durations_ms": durations,
            },
        ),
    )


@pytest.fixture
def planned() -> list[PlannedTrial]:
    """Two segments with gaps and one catch segment."""
    return [
        _segment(1, [1.5, 3.0, 4.5], [4.0, 10.0, 20.0]),
        _segment(2, [2.0], [6.0]),
        _segment(3, [], []),
    ]


def _write(db: Database, planned: list[PlannedTrial]) -> tuple[int, list[int]]:
    participant_id = db.add_participant(
        Participant(
            participant_code="FLUSH", group_code="CTRL", age=30, sex="UNDISCLOSED"
        )
    )
    session_id = db.start_session(
        SessionRecord(
            participant_id=participant_id,
            seed=1,
            config_snapshot="{}",
            config_mode="development",
            python_version="3.10",
            os_name="test",
        )
    )
    block_id = db.add_block(
        Block(
            session_id=session_id,
            module="gin",
            block_index=0,
            n_trials_planned=len(planned),
        )
    )
    trial_ids = [
        db.add_trial(item.for_block(block_id, index))
        for index, item in enumerate(planned)
    ]
    return session_id, trial_ids


def _flush(
    db: Database,
    config: Any,
    planned: list[PlannedTrial],
    trial_ids: list[int],
    presses: list[float],
) -> tuple[BlockOutcome, _FlushState]:
    onsets = [START_S + index * STEP_S for index in range(len(planned))]
    outcome = BlockOutcome(block_id=1, block_index=0, n_planned=len(planned), module="gin")
    state = _FlushState()
    _flush_gin(
        db,
        config.modules.gin,
        planned,
        onsets,
        trial_ids,
        presses,
        Counter(),
        state,
        outcome,
    )
    return outcome, state


def _rows(db: Database, session_id: int) -> list[Any]:
    return [
        row for row in db.flat_rows(session_id) if row["response_id"] is not None
    ]


def test_a_press_inside_a_gaps_window_is_a_hit_naming_that_gap(
    db: Database, config: Any, planned: list[PlannedTrial]
) -> None:
    session_id, trial_ids = _write(db, planned)
    # Segment 1's second gap is at 3.0 s; press 400 ms after it.
    outcome, _ = _flush(db, config, planned, trial_ids, [START_S + 3.4])
    db.conn.commit()

    rows = _rows(db, session_id)
    assert len(rows) == 1
    assert rows[0]["category"] == HIT
    assert rows[0]["event_index"] == 1
    assert rows[0]["rt_from_burst_ms"] == pytest.approx(400.0)
    assert rows[0]["rt_from_prompt_ms"] is None
    # One fact in one column: the category already says it was a detection.
    assert rows[0]["is_correct"] is None
    assert outcome.categories[HIT] == 1


def test_a_press_in_the_interval_is_a_false_alarm_on_that_segment(
    db: Database, config: Any, planned: list[PlannedTrial]
) -> None:
    """The next segment has not started; the participant pressed while there was
    nothing to detect."""
    session_id, trial_ids = _write(db, planned)
    _flush(db, config, planned, trial_ids, [START_S + 7.0])
    db.conn.commit()

    rows = _rows(db, session_id)
    assert len(rows) == 1
    assert rows[0]["category"] == FALSE_ALARM
    assert rows[0]["event_index"] is None
    assert rows[0]["rt_from_burst_ms"] is None
    assert rows[0]["gin_segment_index"] == 1


def test_every_press_of_a_catch_segment_is_a_false_alarm(
    db: Database, config: Any, planned: list[PlannedTrial]
) -> None:
    session_id, trial_ids = _write(db, planned)
    catch_start = START_S + 2 * STEP_S
    _flush(db, config, planned, trial_ids, [catch_start + 1.0, catch_start + 4.0])
    db.conn.commit()

    rows = _rows(db, session_id)
    assert [row["category"] for row in rows] == [FALSE_ALARM, FALSE_ALARM]
    assert [row["event_index"] for row in rows] == [None, None]
    assert [row["gin_segment_index"] for row in rows] == [3, 3]
    # Several responses on one trial, indexed in the order they arrived.
    assert [row["response_index"] for row in rows] == [0, 1]


def test_a_press_before_the_first_segment_belongs_to_nothing(
    db: Database, config: Any, planned: list[PlannedTrial]
) -> None:
    session_id, trial_ids = _write(db, planned)
    _, state = _flush(db, config, planned, trial_ids, [START_S - 0.5])
    db.conn.commit()

    assert _rows(db, session_id) == []
    assert state.before_first == 1


def test_a_press_just_before_the_next_segment_still_lands_on_the_current_one(
    db: Database, config: Any, planned: list[PlannedTrial]
) -> None:
    """The runner stops holding a quarter second before the next segment so it
    can be scheduled in time; presses from that quarter second are collected by
    the next iteration and have to be bucketed by onset, not by which hold saw
    them."""
    session_id, trial_ids = _write(db, planned)
    _flush(db, config, planned, trial_ids, [START_S + STEP_S - 0.1])
    db.conn.commit()

    rows = _rows(db, session_id)
    assert len(rows) == 1
    assert rows[0]["gin_segment_index"] == 1
    assert rows[0]["category"] == FALSE_ALARM


def test_flushing_twice_does_not_write_a_press_twice(
    db: Database, config: Any, planned: list[PlannedTrial]
) -> None:
    """A block boundary flushes mid-run; the buffer is shared across blocks."""
    session_id, trial_ids = _write(db, planned)
    presses = [START_S + 1.7]
    onsets = [START_S + index * STEP_S for index in range(len(planned))]
    outcome = BlockOutcome(block_id=1, block_index=0, n_planned=3, module="gin")
    state = _FlushState()
    counts: Counter[int] = Counter()

    def flush() -> None:
        _flush_gin(
            db,
            config.modules.gin,
            planned,
            onsets,
            trial_ids,
            presses,
            counts,
            state,
            outcome,
        )

    for _ in range(2):
        flush()
    # A second press on the same segment, arriving after that block's commit:
    # its response_index has to continue from the one already written.
    presses.append(START_S + 3.2)
    flush()
    db.conn.commit()

    rows = _rows(db, session_id)
    assert len(rows) == 2
    assert [row["event_index"] for row in rows] == [0, 1]


def test_only_the_trials_already_written_receive_presses(
    db: Database, config: Any, planned: list[PlannedTrial]
) -> None:
    """Attribution runs against the onsets of the segments presented so far; a
    press cannot be assigned to a trial that has no row yet."""
    session_id, trial_ids = _write(db, planned)
    _, state = _flush(db, config, planned, trial_ids[:1], [START_S + STEP_S + 2.3])
    db.conn.commit()

    rows = _rows(db, session_id)
    assert len(rows) == 1
    # It followed segment 1 as far as the flush can tell — segment 2 is not
    # known to it yet — and it is a false alarm there.
    assert rows[0]["gin_segment_index"] == 1
    assert rows[0]["category"] == FALSE_ALARM
    assert state.before_first == 0
