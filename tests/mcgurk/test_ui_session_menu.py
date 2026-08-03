"""How the session flow drives the menu (ADIM 12c).

``_ask_selection`` is the part of the flow that decides *whether* to warn and
what to do with the answer.  The dialogs themselves are monkeypatched here, so
the loop is testable without a screen — which matters because its failure mode
is silent: a participant measured with two different faces still produces data
that looks fine.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from mcgurk.config.schema import ExperimentConfig
from mcgurk.config.selection import SessionSelection
from mcgurk.db import (
    SESSION_COMPLETED,
    Block,
    Database,
    Participant,
    SessionRecord,
    Trial,
)
from mcgurk.ui import session as session_module


@pytest.fixture
def config(config_dict: dict[str, Any]) -> ExperimentConfig:
    return ExperimentConfig.model_validate(config_dict)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Database]:
    database = Database(tmp_path / "test.sqlite")
    yield database
    database.close()


def _participant(db: Database) -> tuple[Participant, int]:
    participant = Participant(
        participant_code="T12C", group_code="CTRL", age=30, sex="F"
    )
    return participant, db.add_participant(participant)


def _earlier_session_with(db: Database, participant_id: int, speaker_id: int) -> None:
    session_id = db.start_session(
        SessionRecord(
            participant_id=participant_id,
            seed=1,
            config_snapshot="{}",
            config_mode="development",
            python_version="3.10.20",
            os_name="Windows 11",
            git_commit="abc1234",
        )
    )
    block_id = db.add_block(
        Block(session_id=session_id, module="mcgurk", block_index=0, n_trials_planned=1)
    )
    db.add_trial(
        Trial(
            block_id=block_id,
            trial_index=0,
            module="mcgurk",
            design_extra={"speaker_id": speaker_id},
        )
    )
    db.finish_block(block_id, SESSION_COMPLETED)
    db.finish_session(session_id, SESSION_COMPLETED)


def _install(monkeypatch, answers: list[SessionSelection | None], confirms: list[bool]):
    """Queue the menu's answers and the confirmation's, and record the calls."""
    seen: dict[str, list[Any]] = {"menu": [], "confirm": []}

    def fake_menu(config, default, **kwargs):
        seen["menu"].append((default, kwargs))
        return answers.pop(0)

    def fake_confirm(*, previous_id: int, chosen_id: int) -> bool:
        seen["confirm"].append((previous_id, chosen_id))
        return confirms.pop(0)

    monkeypatch.setattr(session_module, "ask_session_setup", fake_menu)
    monkeypatch.setattr(session_module, "confirm_speaker_change", fake_confirm)
    return seen


def _ask(config: ExperimentConfig, db: Database, participant_id: int, participant):
    return session_module._ask_selection(
        config,
        db=db,
        participant=participant,
        participant_id=participant_id,
        seed=7,
        prefill=None,
    )


def test_a_first_session_is_not_warned_about(
    config: ExperimentConfig, db: Database, monkeypatch
) -> None:
    participant, participant_id = _participant(db)
    chosen = SessionSelection(modules=("mcgurk",), speaker_id=3)
    seen = _install(monkeypatch, [chosen], [])

    assert _ask(config, db, participant_id, participant) == chosen
    assert seen["confirm"] == []


def test_the_same_speaker_as_last_time_is_not_warned_about(
    config: ExperimentConfig, db: Database, monkeypatch
) -> None:
    participant, participant_id = _participant(db)
    _earlier_session_with(db, participant_id, 2)
    chosen = SessionSelection(modules=("mcgurk",), speaker_id=2)
    seen = _install(monkeypatch, [chosen], [])

    assert _ask(config, db, participant_id, participant) == chosen
    assert seen["confirm"] == []


def test_the_menu_is_told_what_this_participant_saw_before(
    config: ExperimentConfig, db: Database, monkeypatch
) -> None:
    participant, participant_id = _participant(db)
    _earlier_session_with(db, participant_id, 6)
    seen = _install(
        monkeypatch, [SessionSelection(modules=("mcgurk",), speaker_id=6)], []
    )

    _ask(config, db, participant_id, participant)
    _default, kwargs = seen["menu"][0]
    assert kwargs["previous_speaker_id"] == 6
    assert kwargs["speaker_counts"] == {6: 1}
    assert kwargs["participant_code"] == "T12C"


def test_a_different_speaker_needs_confirming(
    config: ExperimentConfig, db: Database, monkeypatch
) -> None:
    participant, participant_id = _participant(db)
    _earlier_session_with(db, participant_id, 2)
    chosen = SessionSelection(modules=("mcgurk",), speaker_id=5)
    seen = _install(monkeypatch, [chosen], [True])

    assert _ask(config, db, participant_id, participant) == chosen
    assert seen["confirm"] == [(2, 5)]


def test_refusing_the_confirmation_returns_to_the_menu(
    config: ExperimentConfig, db: Database, monkeypatch
) -> None:
    """Not to the session: the operator gets to pick the previous speaker."""
    participant, participant_id = _participant(db)
    _earlier_session_with(db, participant_id, 2)
    rejected = SessionSelection(modules=("mcgurk",), speaker_id=5)
    accepted = SessionSelection(modules=("mcgurk",), speaker_id=2)
    seen = _install(monkeypatch, [rejected, accepted], [False])

    assert _ask(config, db, participant_id, participant) == accepted
    assert len(seen["menu"]) == 2
    # The second showing keeps what was typed rather than resetting the form.
    assert seen["menu"][1][0] == rejected


def test_cancelling_the_menu_starts_nothing(
    config: ExperimentConfig, db: Database, monkeypatch
) -> None:
    participant, participant_id = _participant(db)
    _install(monkeypatch, [None], [])

    assert _ask(config, db, participant_id, participant) is None


def test_the_menu_defaults_to_the_config_when_nothing_was_prefilled(
    config: ExperimentConfig, db: Database, monkeypatch
) -> None:
    participant, participant_id = _participant(db)
    seen = _install(
        monkeypatch, [SessionSelection(modules=("mcgurk",), speaker_id=1)], []
    )

    _ask(config, db, participant_id, participant)
    default, _kwargs = seen["menu"][0]
    assert default.modules == tuple(config.enabled_modules())
    assert default.speaker_id == config.speaker_selection.fixed_id
