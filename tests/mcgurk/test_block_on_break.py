"""The between-block break hook (Adım 8b-i).

``run_blocks`` splits a module into blocks at ``break_every_n_trials`` (§A.5) and
calls ``on_break`` between them.  The trial loop itself needs hardware, so it is
stubbed out here — what is under test is that the hook fires at the block
boundaries and nowhere else, which is where the session flow shows its break
screen.
"""

from __future__ import annotations

from typing import Any, cast

import mcgurk.modules.block as block_module
from mcgurk.config import load_config
from mcgurk.modules.block import TrialPolicy, run_blocks


def _policy() -> TrialPolicy:
    # grid_for/evaluate are never invoked here — _run_one_trial is stubbed — so
    # they can be no-ops cast to the expected callable types.
    return TrialPolicy(
        module="mcgurk",
        fixation_s=0.0,
        post_response_s=0.0,
        timeout_s=1.0,
        timeout_message="",
        free_text_label=None,
        free_text_prompt=None,
        grid_for=cast(Any, lambda _trial: None),
        evaluate=cast(Any, lambda _label, _trial: None),
    )


class _FakeDB:
    """Just the block bookkeeping run_blocks touches — no trials are written."""

    def __init__(self) -> None:
        self._index = -1
        self.finished: list[tuple[int, str]] = []

    def next_block_index(self, _session_id: int) -> int:
        self._index += 1
        return self._index

    def add_block(self, block: Any) -> int:
        return 100 + block.block_index

    def finish_block(self, block_id: int, status: str) -> None:
        self.finished.append((block_id, status))


def _run(config: Any, planned: list[Any], on_break: Any) -> _FakeDB:
    db = _FakeDB()
    run_blocks(
        config=config,
        db=cast(Any, db),
        session_id=1,
        presenter=cast(Any, None),
        win=None,
        kb=None,
        planned=planned,
        policy=_policy(),
        on_break=on_break,
    )
    return db


def test_break_fires_between_blocks(monkeypatch, write_config, config_dict) -> None:
    monkeypatch.setattr(block_module, "_run_one_trial", lambda **_kwargs: None)
    config_dict["session"]["break_every_n_trials"] = 2
    config = load_config(write_config(config_dict), check_filesystem=False)

    calls: list[tuple[int, int]] = []
    db = _run(config, [object()] * 5, lambda done, total: calls.append((done, total)))

    # 5 trials, blocks of 2 -> 3 blocks -> a break after the first two.
    assert calls == [(1, 3), (2, 3)]
    assert len(db.finished) == 3  # every block still closes


def test_no_break_for_a_single_block(monkeypatch, write_config, config_dict) -> None:
    monkeypatch.setattr(block_module, "_run_one_trial", lambda **_kwargs: None)
    config = load_config(write_config(config_dict), check_filesystem=False)  # 60

    calls: list[Any] = []
    _run(config, [object()] * 5, lambda done, total: calls.append((done, total)))
    assert calls == []
