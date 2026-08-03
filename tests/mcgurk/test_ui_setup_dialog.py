"""The operator's session menu, without a screen (ADIM 12c).

``build_form`` and ``build_selection`` are the whole decision; the PsychoPy
dialog only shows the fields and writes the answers back into the same dict.
So everything that could silently change a session — which speaker comes
pre-selected, which modules are ticked, what an empty answer means — is checked
here, in CI.
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
    FIELD_COUNTS,
    FIELD_CROSS,
    FIELD_PARTICIPANT,
    FIELD_PRACTICE,
    FIELD_PREVIOUS,
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

    assert selection == _default(config)
    assert apply(config, selection).trial_counts() == config.trial_counts()


def test_the_preselected_speaker_is_first_in_the_list(
    config: ExperimentConfig,
) -> None:
    """A DlgFromDict dropdown always selects its first choice.

    If the default were left in id order, the menu would quietly hand every
    session to speaker 1 whatever the config's strategy chose.
    """
    form = build_form(config, SessionSelection(modules=("mcgurk",), speaker_id=5))
    assert form.speaker_by_label[form.fields[FIELD_SPEAKER][0]] == 5


def test_every_prepared_speaker_is_offered_with_its_session_count(
    config: ExperimentConfig,
) -> None:
    form = build_form(config, _default(config), speaker_counts={2: 3})
    labels = form.fields[FIELD_SPEAKER]

    assert sorted(form.speaker_by_label.values()) == config.stimulus_prep.speaker_ids()
    assert len(labels) == len(config.stimulus_prep.speaker_ids())
    assert any("(3 oturum)" in label for label in labels)
    assert form.fields[FIELD_COUNTS] == "2: 3"


def test_the_counts_line_says_so_when_there_are_none(
    config: ExperimentConfig,
) -> None:
    form = build_form(config, _default(config))
    assert form.fields[FIELD_COUNTS] == "henüz oturum yok"


def test_a_module_checkbox_says_what_it_costs(config: ExperimentConfig) -> None:
    form = build_form(config, _default(config))
    key = _field_for(form, "mcgurk")

    assert "McGurk" in key
    assert str(config.trial_counts()["mcgurk"]) in key
    assert form.fields[key] is True


def test_the_participant_and_the_previous_speaker_are_shown_but_not_editable(
    config: ExperimentConfig,
) -> None:
    form = build_form(
        config, _default(config), participant_code="SSD-R-007", previous_speaker_id=2
    )
    assert form.fields[FIELD_PARTICIPANT] == "SSD-R-007"
    assert form.fields[FIELD_PREVIOUS] == "2"
    assert FIELD_PARTICIPANT in form.fixed and FIELD_PREVIOUS in form.fixed


def test_a_first_session_has_no_previous_speaker_row(
    config: ExperimentConfig,
) -> None:
    form = build_form(config, _default(config), participant_code="YENI")
    assert FIELD_PREVIOUS not in form.fields


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


def test_the_chosen_speaker_is_read_back_by_label(config: ExperimentConfig) -> None:
    form = build_form(config, _default(config))
    label = next(k for k, v in form.speaker_by_label.items() if v == 7)
    form.fields[FIELD_SPEAKER] = label

    assert build_selection(form).speaker_id == 7


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


def test_an_unknown_speaker_answer_is_refused(config: ExperimentConfig) -> None:
    form = build_form(config, _default(config))
    form.fields[FIELD_SPEAKER] = "Konuşmacı 42 — Kim?"

    with pytest.raises(SelectionError, match="Konuşmacı seçilmedi"):
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
