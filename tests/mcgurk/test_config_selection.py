"""The operator's session selection (ADIM 12b).

The decision is pure so it can be tested without a screen (§A12.4), and what it
produces is not a side-channel but a **config**: the subset is applied to the
design that the session then starts with, which is the design that lands in
``sessions.config_snapshot``.  Everything downstream — resume, analysis, QC —
already reads that snapshot, so the tests here are mostly about one question:
is the derived config a config the schema still accepts?
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from mcgurk.config.loader import config_from_snapshot
from mcgurk.config.schema import ExperimentConfig
from mcgurk.config.selection import (
    SPEAKER_MODULES,
    SelectionError,
    SessionSelection,
    apply,
    available_modules,
    available_speakers,
    default_selection,
    select_speaker,
)


@pytest.fixture
def config(config_dict: dict[str, Any]) -> ExperimentConfig:
    return ExperimentConfig.model_validate(config_dict)


def _snapshot(config: ExperimentConfig) -> str:
    """Exactly what ``Database.snapshot_config`` writes."""
    return json.dumps(
        config.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, default=str
    )


# ------------------------------------------------------------------ choices


def test_the_speaker_list_is_the_prepared_set_with_readable_names(
    config: ExperimentConfig,
) -> None:
    speakers = available_speakers(config)
    assert [s.speaker_id for s in speakers] == config.stimulus_prep.speaker_ids()
    assert all(s.label for s in speakers)


def test_a_speaker_without_a_label_still_gets_a_row(
    config_dict: dict[str, Any]
) -> None:
    """An unnamed line is one the operator cannot choose between."""
    config_dict["stimulus_prep"]["speakers"][0].pop("label")
    speakers = available_speakers(ExperimentConfig.model_validate(config_dict))
    assert speakers[0].label == "Konuşmacı 1"


def test_the_module_list_carries_what_each_one_costs(
    config: ExperimentConfig,
) -> None:
    counts = config.trial_counts()
    modules = available_modules(config)
    assert [m.name for m in modules] == config.enabled_modules()
    assert all(m.label and m.label != m.name for m in modules)
    assert {m.name: m.n_trials for m in modules} == {
        name: counts[name] for name in config.enabled_modules()
    }


def test_a_module_the_config_disables_is_not_offered(
    config_dict: dict[str, Any]
) -> None:
    """The menu chooses within the config, never around it."""
    config_dict["modules"]["gin"]["enabled"] = False
    config_dict["session"]["module_order"].remove("gin")
    config = ExperimentConfig.model_validate(config_dict)
    assert "gin" not in [m.name for m in available_modules(config)]


# ------------------------------------------------------------------ default


def test_the_default_is_todays_session(config: ExperimentConfig) -> None:
    """Confirming without touching anything must run the Adım 8 design (§A12.3)."""
    selection = default_selection(config, session_count=0, seed=1)

    assert selection.modules == tuple(config.enabled_modules())
    assert selection.practice and selection.cross_hearing
    assert selection.speaker_id == select_speaker(config, session_count=0, seed=1)
    assert apply(config, selection).trial_counts() == config.trial_counts()


# -------------------------------------------------------------------- apply


def test_a_subset_only_counts_what_it_runs(config: ExperimentConfig) -> None:
    applied = apply(config, SessionSelection(modules=("mcgurk",), speaker_id=2))

    assert applied.enabled_modules() == ["mcgurk"]
    assert set(applied.trial_counts()) == {"practice", "mcgurk", "cross_hearing"}
    assert applied.trial_counts()["mcgurk"] == config.trial_counts()["mcgurk"]
    assert applied.session.module_order == ["practice", "mcgurk"]


def test_the_derived_config_survives_the_snapshot_round_trip(
    config: ExperimentConfig,
) -> None:
    """Every validator still has to be satisfied — this is what §A12.1 rests on.

    If a shortened ``module_order`` or a disabled module ever stopped
    round-tripping, resume would fail on a session that had already collected
    trials, which is the worst possible moment to find out.
    """
    applied = apply(
        config, SessionSelection(modules=("dichotic", "gin"), speaker_id=5)
    )
    restored = config_from_snapshot(_snapshot(applied))

    assert restored.enabled_modules() == applied.enabled_modules()
    assert restored.trial_counts() == applied.trial_counts()
    assert restored.speaker_selection.fixed_id == 5


def test_the_chosen_speaker_is_written_everywhere_it_is_read(
    config: ExperimentConfig,
) -> None:
    applied = apply(config, SessionSelection(modules=("mcgurk",), speaker_id=5))

    assert applied.speaker_selection.strategy == "fixed"
    assert applied.speaker_selection.fixed_id == 5
    # The constant is the set of modules that actually carry a speaker, not a
    # list kept in step by hand: oddball's tones and gin's noise have no face.
    assert {
        name
        for name, module in applied.modules.by_name().items()
        if hasattr(module, "speaker_id")
    } == set(SPEAKER_MODULES)
    assert applied.modules.mcgurk.speaker_id == 5
    assert applied.modules.avsr.speaker_id == 5
    assert applied.modules.tbw.speaker_id == 5
    assert applied.modules.dichotic.speaker_id == 5
    assert 5 in applied.required_speaker_ids()
    # The selection is what select_speaker now returns: the session flow needs
    # no separate path for "the operator picked one".
    assert select_speaker(applied, session_count=3, seed=9) == 5


def test_not_choosing_a_speaker_leaves_the_strategy_alone(
    config: ExperimentConfig,
) -> None:
    """``--modules`` alone must change only what it says it changes."""
    applied = apply(config, SessionSelection(modules=("mcgurk",)))
    assert applied.speaker_selection == config.speaker_selection


def test_practice_and_the_cross_hearing_check_can_be_dropped(
    config: ExperimentConfig,
) -> None:
    applied = apply(
        config,
        SessionSelection(modules=("tbw",), practice=False, cross_hearing=False),
    )

    assert applied.session.module_order == ["tbw"]
    assert not applied.cross_hearing_check.enabled
    assert set(applied.trial_counts()) == {"tbw"}


def test_apply_does_not_touch_the_config_it_was_given(
    config: ExperimentConfig,
) -> None:
    """The loaded config outlives the session; a later one reads it again."""
    before = _snapshot(config)
    apply(config, SessionSelection(modules=("mcgurk",), speaker_id=8))
    assert _snapshot(config) == before


# ------------------------------------------------------------------- refusal


def test_a_session_with_no_measurement_module_is_refused(
    config: ExperimentConfig,
) -> None:
    with pytest.raises(SelectionError, match="Hiç ölçüm modülü"):
        apply(config, SessionSelection(modules=()))


def test_an_unknown_module_name_is_refused(config: ExperimentConfig) -> None:
    with pytest.raises(SelectionError, match="Bilinmeyen modül: mcgruk"):
        apply(config, SessionSelection(modules=("mcgruk",)))


def test_a_module_the_config_switched_off_is_refused(
    config_dict: dict[str, Any]
) -> None:
    """Re-enabling a module is a config edit, not a checkbox (§A.9)."""
    config_dict["modules"]["gin"]["enabled"] = False
    config_dict["session"]["module_order"].remove("gin")
    config = ExperimentConfig.model_validate(config_dict)

    with pytest.raises(SelectionError, match="Config'te kapalı modül"):
        apply(config, SessionSelection(modules=("gin",)))


def test_a_speaker_that_was_never_prepared_is_refused(
    config: ExperimentConfig,
) -> None:
    with pytest.raises(SelectionError, match="Hazır sette olmayan konuşmacı: 99"):
        apply(config, SessionSelection(modules=("mcgurk",), speaker_id=99))


# ---------------------------------------------------------------- reporting


def test_the_selection_describes_itself_for_the_log(config: ExperimentConfig) -> None:
    line = SessionSelection(
        modules=("mcgurk", "tbw"), speaker_id=3, cross_hearing=False
    ).describe()
    assert "konuşmacı=3" in line
    assert "mcgurk, tbw" in line
    assert "alıştırma" in line and "çapraz" not in line

    assert "konuşmacı=(config)" in SessionSelection(modules=("gin",)).describe()
