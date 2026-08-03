"""``python -m mcgurk.ui``'s selection flags (ADIM 12b).

The flags are the way a session is narrowed without a menu — "sadece dikotik",
"konuşmacı 5" — and they have to translate into exactly the same
``SessionSelection`` the dialog will produce in 12c.  PsychoPy is imported
lazily inside the engine, so this module imports in CI.
"""

from __future__ import annotations

from typing import Any

import pytest

from mcgurk.config.schema import ExperimentConfig
from mcgurk.config.selection import SelectionError
from mcgurk.ui.__main__ import _selection_from, build_parser


@pytest.fixture
def config(config_dict: dict[str, Any]) -> ExperimentConfig:
    return ExperimentConfig.model_validate(config_dict)


def _selection(argv: list[str], config: ExperimentConfig):
    return _selection_from(build_parser().parse_args(argv), config)


def test_no_flags_means_no_selection(config: ExperimentConfig) -> None:
    """The default run has to stay byte-for-byte the Adım 8 session (§A12.3)."""
    assert _selection([], config) is None
    assert _selection(["--limit", "4"], config) is None


def test_no_ask_alone_is_not_a_selection(config: ExperimentConfig) -> None:
    """``--no-ask`` skips the menu; it does not narrow anything by itself."""
    args = build_parser().parse_args(["--no-ask"])
    assert args.no_ask is True
    assert _selection_from(args, config) is None


def test_modules_are_split_on_commas(config: ExperimentConfig) -> None:
    selection = _selection(["--modules", "mcgurk, dichotic"], config)
    assert selection is not None
    assert selection.modules == ("mcgurk", "dichotic")
    assert selection.speaker_id is None
    assert selection.practice and selection.cross_hearing


def test_a_speaker_alone_keeps_the_whole_design(config: ExperimentConfig) -> None:
    selection = _selection(["--speaker", "5"], config)
    assert selection is not None
    assert selection.speaker_id == 5
    assert selection.modules == tuple(config.enabled_modules())


def test_the_two_session_steps_have_their_own_flags(
    config: ExperimentConfig,
) -> None:
    selection = _selection(["--no-practice", "--no-cross-hearing"], config)
    assert selection is not None
    assert not selection.practice and not selection.cross_hearing
    assert selection.modules == tuple(config.enabled_modules())


def test_a_mistyped_module_fails_before_the_participant_sits_down(
    config: ExperimentConfig,
) -> None:
    """Not when the flow reaches it — by then there is a participant waiting."""
    with pytest.raises(SelectionError, match="Bilinmeyen modül"):
        _selection(["--modules", "dikotik"], config)


def test_an_unprepared_speaker_fails_at_the_command_line(
    config: ExperimentConfig,
) -> None:
    with pytest.raises(SelectionError, match="Hazır sette olmayan"):
        _selection(["--speaker", "99"], config)


def test_selecting_nothing_measurable_is_refused(config: ExperimentConfig) -> None:
    with pytest.raises(SelectionError, match="Hiç ölçüm modülü"):
        _selection(["--modules", " "], config)
