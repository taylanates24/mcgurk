"""Resume logic (Adım 8c-i).

The orchestration needs hardware, but what resume *decides* — which modules are
already done, how much of a partial module is left, and reading the session back
from the database — is pure or database-only, and tested here.  This is the
CI-testable core of "kesip devam ettirme çalışıyor, veri kaybı yok".
"""

from __future__ import annotations

import json

from mcgurk.config import load_config
from mcgurk.db.database import Database
from mcgurk.db.models import (
    SESSION_ABORTED,
    SESSION_COMPLETED,
    SESSION_RUNNING,
    Block,
    Participant,
    SessionRecord,
    Trial,
)
from mcgurk.ui.session import config_from_snapshot, remaining_plan

# ----------------------------------------------------------- remaining_plan


def test_completed_module_runs_nothing() -> None:
    assert remaining_plan([1, 2, 3], 3, is_stream=False) == []
    assert remaining_plan([1, 2, 3], 5, is_stream=False) == []  # over-count is safe
    assert remaining_plan([1, 2, 3], 3, is_stream=True) == []


def test_forced_choice_resumes_after_completed_trials() -> None:
    assert remaining_plan([1, 2, 3, 4], 2, is_stream=False) == [3, 4]
    assert remaining_plan([1, 2, 3, 4], 0, is_stream=False) == [1, 2, 3, 4]


def test_stream_reruns_in_full_when_incomplete() -> None:
    # A continuous stream cannot be resumed from its middle, so any incompleteness
    # means the whole thing runs again.
    assert remaining_plan([1, 2, 3, 4], 2, is_stream=True) == [1, 2, 3, 4]
    assert remaining_plan([1, 2, 3, 4], 0, is_stream=True) == [1, 2, 3, 4]


# --------------------------------------------------------- config snapshot


def test_config_snapshot_round_trips() -> None:
    config = load_config(check_filesystem=False)
    snapshot = json.dumps(
        config.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, default=str
    )
    rebuilt = config_from_snapshot(snapshot)
    assert rebuilt.experiment.name == config.experiment.name
    assert rebuilt.session.module_order == config.session.module_order
    # The design has to come back identical, or resume would present a different
    # set of remaining trials than the session originally planned.
    assert rebuilt.trial_counts() == config.trial_counts()


# ------------------------------------------------------------- database side


def _participant(db: Database) -> int:
    return db.add_participant(
        Participant(participant_code="R01", group_code="CTRL", age=30, sex="UNDISCLOSED")
    )


def _session(db: Database, participant_id: int, *, status: str) -> int:
    return db.start_session(
        SessionRecord(
            participant_id=participant_id,
            seed=42,
            config_snapshot="{}",
            config_mode="development",
            python_version="3.10",
            os_name="test",
            status=status,
        )
    )


def _block_with_trials(
    db: Database,
    session_id: int,
    *,
    module: str,
    n: int,
    status: str,
    design_extra: dict | None = None,
) -> None:
    block_id = db.add_block(
        Block(
            session_id=session_id,
            module=module,
            block_index=db.next_block_index(session_id),
            n_trials_planned=n,
        )
    )
    for i in range(n):
        db.add_trial(
            Trial(
                block_id=block_id,
                trial_index=i,
                module=module,
                design_extra=design_extra or {},
            )
        )
    db.finish_block(block_id, status)


def test_latest_resumable_prefers_unfinished_sessions() -> None:
    with Database(":memory:") as db:
        pid = _participant(db)
        _session(db, pid, status=SESSION_COMPLETED)
        aborted = _session(db, pid, status=SESSION_ABORTED)
        row = db.latest_resumable_session(pid)
        assert row is not None
        assert row["session_id"] == aborted


def test_running_session_is_resumable_completed_is_not() -> None:
    with Database(":memory:") as db:
        pid = _participant(db)
        running = _session(db, pid, status=SESSION_RUNNING)
        row = db.latest_resumable_session(pid)
        assert row is not None and row["session_id"] == running
        db.finish_session(running, SESSION_COMPLETED)
        assert db.latest_resumable_session(pid) is None


def test_completed_trial_counts_excludes_aborted_blocks() -> None:
    with Database(":memory:") as db:
        pid = _participant(db)
        sid = _session(db, pid, status=SESSION_ABORTED)
        _block_with_trials(db, sid, module="practice", n=12, status=SESSION_COMPLETED)
        _block_with_trials(
            db,
            sid,
            module="mcgurk",
            n=60,
            status=SESSION_COMPLETED,
            design_extra={"speaker_id": 2},
        )
        # An aborted partial block of the same module — must NOT be counted.
        _block_with_trials(
            db,
            sid,
            module="mcgurk",
            n=7,
            status=SESSION_ABORTED,
            design_extra={"speaker_id": 2},
        )
        counts = db.completed_trial_counts(sid)
        assert counts == {"practice": 12, "mcgurk": 60}


def test_session_speaker_id_read_back_from_trials() -> None:
    with Database(":memory:") as db:
        pid = _participant(db)
        sid = _session(db, pid, status=SESSION_ABORTED)
        _block_with_trials(
            db,
            sid,
            module="mcgurk",
            n=3,
            status=SESSION_COMPLETED,
            design_extra={"speaker_id": 2},
        )
        assert db.session_speaker_id(sid) == 2


def test_session_speaker_id_none_without_trials() -> None:
    with Database(":memory:") as db:
        pid = _participant(db)
        sid = _session(db, pid, status=SESSION_ABORTED)
        assert db.session_speaker_id(sid) is None


def test_set_session_status_reopens_without_completed_at() -> None:
    with Database(":memory:") as db:
        pid = _participant(db)
        sid = _session(db, pid, status=SESSION_ABORTED)
        db.set_session_status(sid, SESSION_RUNNING)
        row = db.get_session(sid)
        assert row is not None
        assert row["status"] == SESSION_RUNNING
        assert row["completed_at"] is None
