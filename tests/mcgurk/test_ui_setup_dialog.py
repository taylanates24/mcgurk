"""The operator's module menu, without a screen (ADIM 12c).

``build_form`` and ``build_selection`` are the whole decision; the PsychoPy
dialog only shows the fields and writes the answers back into the same dict.
So everything that could silently change a session — which modules are ticked,
what an empty answer means, whether the speaker can be changed here — is checked
here, in CI.

The speaker moved to the panel in 12c-ii and is *shown* rather than asked; the
tests below pin that it stays read-only, because a second place to change it is
a second place for the config and the panel to disagree.
"""

from __future__ import annotations

from typing import Any

import pytest

from mcgurk.config.schema import ExperimentConfig
from mcgurk.config.selection import (
    SelectionError,
    SessionSelection,
    apply,
    default_selection,
)
from mcgurk.ui.setup_dialog import (
    FIELD_CROSS,
    FIELD_PARTICIPANT,
    FIELD_PRACTICE,
    FIELD_SPEAKER,
    build_form,
    build_selection,
    selected_trial_total,
)


@pytest.fixture
def config(config_dict: dict[str, Any]) -> ExperimentConfig:
    return ExperimentConfig.model_validate(config_dict)


def _default(config: ExperimentConfig) -> SessionSelection:
    return default_selection(config, session_count=0, seed=1)


def _field_for(form, module_name: str) -> str:
    return next(key for key, name in form.module_by_field.items() if name == module_name)


# -------------------------------------------------------------- pre-filling


def test_the_menu_comes_prefilled_with_todays_session(
    config: ExperimentConfig,
) -> None:
    """Confirming without touching anything must run the Adım 8 session."""
    form = build_form(config, _default(config))
    selection = build_selection(form)

    assert selection.modules == tuple(config.enabled_modules())
    assert selection.practice and selection.cross_hearing
    assert apply(config, selection).trial_counts() == config.trial_counts()


def test_a_module_checkbox_says_what_it_costs(config: ExperimentConfig) -> None:
    form = build_form(config, _default(config))
    key = _field_for(form, "mcgurk")

    assert "McGurk" in key
    assert str(config.trial_counts()["mcgurk"]) in key
    assert form.fields[key] is True


def test_the_participant_and_the_speaker_are_shown_but_not_editable(
    config: ExperimentConfig,
) -> None:
    """The speaker is the panel's decision; this dialog only reports it."""
    form = build_form(
        config,
        _default(config),
        participant_code="SSD-R-007",
        speaker_label="Konuşmacı 2 — Erkek",
    )
    assert form.fields[FIELD_PARTICIPANT] == "SSD-R-007"
    assert form.fields[FIELD_SPEAKER] == "Konuşmacı 2 — Erkek"
    assert FIELD_PARTICIPANT in form.fixed and FIELD_SPEAKER in form.fixed


def test_only_the_modules_the_config_enables_are_offered(
    config_dict: dict[str, Any]
) -> None:
    config_dict["modules"]["gin"]["enabled"] = False
    config_dict["session"]["module_order"].remove("gin")
    config = ExperimentConfig.model_validate(config_dict)

    form = build_form(config, _default(config))
    assert "gin" not in form.module_by_field.values()


# ---------------------------------------------------------- reading it back


def test_unticking_a_module_drops_it(config: ExperimentConfig) -> None:
    form = build_form(config, _default(config))
    for name in ("avsr", "tbw", "oddball", "gin"):
        form.fields[_field_for(form, name)] = False

    selection = build_selection(form)
    assert set(selection.modules) == {"mcgurk", "dichotic"}


def test_the_menu_never_overrides_the_speaker(config: ExperimentConfig) -> None:
    """``speaker_id`` stays None, so ``speaker_selection`` still decides."""
    form = build_form(config, _default(config), speaker_label="Konuşmacı 5 — Kadın")
    selection = build_selection(form)

    assert selection.speaker_id is None
    assert apply(config, selection).speaker_selection == config.speaker_selection


def test_the_two_session_steps_are_their_own_checkboxes(
    config: ExperimentConfig,
) -> None:
    form = build_form(config, _default(config))
    form.fields[FIELD_PRACTICE] = False
    form.fields[FIELD_CROSS] = False

    selection = build_selection(form)
    assert not selection.practice and not selection.cross_hearing
    assert apply(config, selection).session.module_order == config.enabled_modules()


def test_unticking_every_module_is_refused(config: ExperimentConfig) -> None:
    """The dialog re-asks rather than starting a session that measures nothing."""
    form = build_form(config, _default(config))
    for name in list(form.module_by_field.values()):
        form.fields[_field_for(form, name)] = False

    with pytest.raises(SelectionError, match="Hiç ölçüm modülü"):
        build_selection(form)


def test_the_running_total_follows_the_ticks(config: ExperimentConfig) -> None:
    form = build_form(config, _default(config))
    counts = config.trial_counts()
    assert selected_trial_total(form) == sum(
        counts[name] for name in config.enabled_modules()
    )

    for name in config.enabled_modules():
        if name != "tbw":
            form.fields[_field_for(form, name)] = False
    assert selected_trial_total(form) == counts["tbw"]
