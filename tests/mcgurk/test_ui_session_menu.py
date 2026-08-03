"""How the session flow drives the menu and the speaker warning (ADIM 12c).

Since 12c-ii the speaker is the panel's decision, so what the flow still has to
get right is the *warning*: this participant was measured with one face before
and the config now names another.  Its failure mode is silent — a participant
measured with two faces produces data that looks fine — so the dialogs are
monkeypatched here and the decision is tested without a screen.
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


def _install(monkeypatch, answer: SessionSelection | None, confirms: list[bool]):
    """Queue the menu's answer and the confirmation's, and record the calls."""
    seen: dict[str, list[Any]] = {"menu": [], "confirm": []}

    def fake_menu(config, default, **kwargs):
        seen["menu"].append((default, kwargs))
        return answer

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
    chosen = SessionSelection(modules=("mcgurk",))
    seen = _install(monkeypatch, chosen, [])

    assert _ask(config, db, participant_id, participant) == chosen
    assert seen["confirm"] == []


def test_the_same_speaker_as_last_time_is_not_warned_about(
    config: ExperimentConfig, db: Database, monkeypatch
) -> None:
    participant, participant_id = _participant(db)
    _earlier_session_with(db, participant_id, config.speaker_selection.fixed_id or 1)
    chosen = SessionSelection(modules=("mcgurk",))
    seen = _install(monkeypatch, chosen, [])

    assert _ask(config, db, participant_id, participant) == chosen
    assert seen["confirm"] == []


def test_a_different_speaker_in_the_config_needs_confirming(
    config: ExperimentConfig, db: Database, monkeypatch
) -> None:
    participant, participant_id = _participant(db)
    _earlier_session_with(db, participant_id, 6)
    chosen = SessionSelection(modules=("mcgurk",))
    seen = _install(monkeypatch, chosen, [True])

    assert _ask(config, db, participant_id, participant) == chosen
    assert seen["confirm"] == [(6, config.speaker_selection.fixed_id)]


def test_refusing_the_warning_cancels_the_session(
    config: ExperimentConfig, db: Database, monkeypatch
) -> None:
    """The fix is in the panel, so there is nothing useful to re-ask here."""
    participant, participant_id = _participant(db)
    _earlier_session_with(db, participant_id, 6)
    seen = _install(monkeypatch, SessionSelection(modules=("mcgurk",)), [False])

    assert _ask(config, db, participant_id, participant) is None
    assert seen["menu"] == []


def test_cancelling_the_menu_starts_nothing(
    config: ExperimentConfig, db: Database, monkeypatch
) -> None:
    participant, participant_id = _participant(db)
    _install(monkeypatch, None, [])

    assert _ask(config, db, participant_id, participant) is None


def test_the_menu_is_told_which_speaker_the_session_will_use(
    config: ExperimentConfig, db: Database, monkeypatch
) -> None:
    participant, participant_id = _participant(db)
    seen = _install(monkeypatch, SessionSelection(modules=("mcgurk",)), [])

    _ask(config, db, participant_id, participant)
    default, kwargs = seen["menu"][0]
    assert kwargs["participant_code"] == "T12C"
    assert kwargs["speaker_label"] == session_module.speaker_label_for(
        config, config.speaker_selection.fixed_id or 1
    )
    assert default.modules == tuple(config.enabled_modules())
