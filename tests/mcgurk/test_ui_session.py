"""Per-participant decisions and module import safety (Adım 8b-i).

The orchestration needs a screen and a sound card, but the decisions it makes —
which speaker, which ear — are pure and tested here.  A wrong ear turns GIN into
a monaural test of a deaf ear; that has to be caught without hardware.
"""

from __future__ import annotations

import importlib
from typing import Any

from mcgurk.config import load_config
from mcgurk.db.models import (
    GROUP_CONTROL,
    GROUP_SSD_LEFT,
    GROUP_SSD_RIGHT,
    Participant,
)
from mcgurk.ui.session import good_ear_for, select_speaker


def _load(config_dict: dict[str, Any], write_config):
    return load_config(write_config(config_dict), check_filesystem=False)


def _participant(group: str, *, left: float | None = None, right: float | None = None):
    return Participant(
        participant_code="X",
        group_code=group,
        age=30,
        sex="UNDISCLOSED",
        pta_left_db=left,
        pta_right_db=right,
    )


# ------------------------------------------------------------ speaker choice


def test_fixed_speaker_uses_the_configured_id() -> None:
    config = load_config(check_filesystem=False)  # shipped: fixed, id 1
    assert select_speaker(config, session_count=0, seed=7) == 1
    assert select_speaker(config, session_count=9, seed=7) == 1


def test_balanced_speaker_rotates_by_session_count(write_config, config_dict) -> None:
    config_dict["speaker_selection"]["strategy"] = "balanced"
    config = _load(config_dict, write_config)
    # Derived, not written out: the shipped set went from two speakers to
    # eight in Adım 12a, and a hard-coded pair would have said "wraps" about
    # the third speaker.
    ids = config.stimulus_prep.speaker_ids()
    for count, expected in enumerate(ids):
        assert select_speaker(config, session_count=count, seed=1) == expected
    assert select_speaker(config, session_count=len(ids), seed=1) == ids[0]  # wraps


def test_random_speaker_is_in_range_and_reproducible(write_config, config_dict) -> None:
    config_dict["speaker_selection"]["strategy"] = "random"
    config = _load(config_dict, write_config)
    ids = set(config.stimulus_prep.speaker_ids())
    first = select_speaker(config, session_count=0, seed=123)
    assert first in ids
    # Same seed -> same speaker, so the choice is recoverable from the stored data.
    assert select_speaker(config, session_count=0, seed=123) == first


# ------------------------------------------------------------------ good ear


def test_good_ear_from_pta_when_both_known() -> None:
    # Better ear = lower PTA, regardless of group.
    assert good_ear_for(_participant(GROUP_CONTROL, left=5, right=40)) == "left"
    assert good_ear_for(_participant(GROUP_CONTROL, left=40, right=5)) == "right"


def test_good_ear_from_group_when_pta_missing() -> None:
    assert good_ear_for(_participant(GROUP_SSD_RIGHT)) == "left"
    assert good_ear_for(_participant(GROUP_SSD_LEFT)) == "right"


def test_good_ear_group_breaks_a_pta_tie() -> None:
    # Equal PTA falls through to the group rule rather than picking arbitrarily.
    assert good_ear_for(_participant(GROUP_SSD_RIGHT, left=20, right=20)) == "left"


def test_good_ear_control_without_pta_defaults_right() -> None:
    assert good_ear_for(_participant(GROUP_CONTROL)) == "right"


# --------------------------------------------------------- import safety (CI)


def test_ui_modules_import_without_psychopy() -> None:
    # CI has no PsychoPy; a stray top-level `from psychopy import ...` in any of
    # these would fail here rather than at run time on the rig.
    for name in (
        "mcgurk.ui.login",
        "mcgurk.ui.runtime",
        "mcgurk.ui.screens",
        "mcgurk.ui.session",
    ):
        importlib.import_module(name)
