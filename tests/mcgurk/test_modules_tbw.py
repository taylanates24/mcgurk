"""Modül 3 — the design it generates, and what a response means.

The fit itself lives in ``test_tbw_fit.py``; this file covers the acceptance
criteria of steps.md §C Adım 6 that concern the trial list: the SOA grid is
presented as configured, the order is reproducible from the seed, every trial
records its nominal SOA, and a design the engine could not schedule is refused
before anyone sits down.
"""

from __future__ import annotations

import copy
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from mcgurk.config.loader import ConfigError, load_config
from mcgurk.db.design import validate_design_extra
from mcgurk.modules.base import QUIET, ModuleError
from mcgurk.modules.tbw import (
    DIFFERENT,
    SAME,
    cell_counts,
    check_soa_is_schedulable,
    design_cells,
    judge,
    plan_trials,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STIMULI = Path("stimuli")
SEED = 20260727


@pytest.fixture
def config(write_config: Any, config_dict: dict[str, Any]) -> Any:
    return load_config(write_config(config_dict), check_filesystem=False)


@pytest.fixture
def manifest(config: Any, manifest_factory: Any) -> Any:
    return manifest_factory(config)


def _plan(config: Any, manifest: Any, seed: int = SEED) -> list:
    return plan_trials(config, manifest, seed=seed, stimuli_root=STIMULI)


def _load(write_config: Any, data: dict[str, Any]) -> Any:
    return load_config(write_config(data), check_filesystem=False)


# ---------------------------------------------------------------- the design


def test_the_generator_produces_exactly_what_the_config_estimated(
    config: Any, manifest: Any
) -> None:
    assert len(_plan(config, manifest)) == config.trial_counts()["tbw"]


def test_every_soa_is_presented_the_configured_number_of_times(
    config: Any, manifest: Any
) -> None:
    module = config.modules.tbw
    counts = Counter(item.trial.nominal_soa_ms for item in _plan(config, manifest))
    assert set(counts) == set(module.soa_values_ms)
    assert set(counts.values()) == {module.reps_per_soa * len(module.ears)}


def test_the_spec_and_the_row_carry_the_same_soa(config: Any, manifest: Any) -> None:
    """The presenter reads the spec and the analysis reads the row; a trial
    presented at one SOA and recorded at another would be undetectable."""
    for item in _plan(config, manifest):
        assert item.spec.nominal_soa_ms == item.trial.nominal_soa_ms
        assert item.spec.mode == "AV"


def test_every_trial_is_audiovisual_quiet_and_congruent(
    config: Any, manifest: Any
) -> None:
    stimulus = config.modules.tbw.stimulus
    for item in _plan(config, manifest):
        trial = item.trial
        assert trial.module == "tbw"
        assert trial.visual_token == stimulus.visual
        assert trial.audio_token == stimulus.audio
        assert trial.snr_db is None
        assert trial.noise_condition == QUIET
        assert item.spec.video_path is not None
        assert item.spec.audio_path is not None


def test_the_design_extra_is_valid_and_names_the_speaker(
    config: Any, manifest: Any
) -> None:
    for item in _plan(config, manifest):
        validate_design_extra("tbw", item.trial.design_extra)
        assert item.trial.design_extra["speaker_id"] == config.modules.tbw.speaker_id
        assert item.trial.design_extra["noise_instance"] is None


def test_the_speaker_can_be_chosen_per_participant(config: Any, manifest: Any) -> None:
    """§F.4 — Adım 8 may pick the speaker; the module has no opinion."""
    planned = plan_trials(
        config, manifest, seed=SEED, stimuli_root=STIMULI, speaker_id=2
    )
    assert {item.trial.design_extra["speaker_id"] for item in planned} == {2}
    assert all("speaker_2" in str(item.spec.video_path) for item in planned)


def test_the_same_seed_gives_the_same_order(config: Any, manifest: Any) -> None:
    first = [item.trial.condition_label for item in _plan(config, manifest)]
    second = [item.trial.condition_label for item in _plan(config, manifest)]
    assert first == second


def test_a_different_seed_gives_a_different_order(config: Any, manifest: Any) -> None:
    first = [item.trial.nominal_soa_ms for item in _plan(config, manifest, seed=1)]
    second = [item.trial.nominal_soa_ms for item in _plan(config, manifest, seed=2)]
    assert first != second
    assert Counter(first) == Counter(second)


def test_block_shuffle_spreads_the_soas_over_the_module(
    config: Any, manifest: Any
) -> None:
    """One round holds one presentation of every SOA, so the whole grid is
    sampled early and a participant who tires late affects every SOA equally."""
    module = config.modules.tbw
    n_soa = len(module.soa_values_ms)
    planned = _plan(config, manifest)
    first_round = [item.trial.nominal_soa_ms for item in planned[:n_soa]]
    assert sorted(first_round) == sorted(module.soa_values_ms)


def test_cell_counts_reports_one_row_per_soa(config: Any, manifest: Any) -> None:
    counts = cell_counts(_plan(config, manifest))
    module = config.modules.tbw
    assert len(counts) == len(module.soa_values_ms) * len(module.ears)
    assert set(counts.values()) == {module.reps_per_soa}


def test_design_cells_crosses_soa_with_ear(config: Any) -> None:
    module = config.modules.tbw
    module.ears = ["left", "right"]
    cells, reps = design_cells(module)
    assert len(cells) == len(module.soa_values_ms) * 2
    assert set(reps) == {module.reps_per_soa}


# ------------------------------------------------------------------- refusals


def test_a_disabled_module_refuses_to_generate(config: Any, manifest: Any) -> None:
    config.modules.tbw.enabled = False
    with pytest.raises(ModuleError, match="enabled"):
        _plan(config, manifest)


def test_a_missing_stimulus_names_the_preparation_step(
    config: Any, manifest: Any
) -> None:
    manifest.videos = [
        entry for entry in manifest.videos if entry.token != config.modules.tbw.stimulus.visual
    ]
    with pytest.raises(ModuleError, match="prepare_stimuli"):
        _plan(config, manifest)


def test_an_soa_the_engine_could_not_schedule_is_refused(config: Any) -> None:
    """A negative SOA is paid for with presentation lead, and the engine caps
    that at a second.  Finding out mid-session is finding out too late."""
    config.modules.tbw.soa_values_ms = [-5000.0, 0.0, 5000.0]
    with pytest.raises(ModuleError, match="pay"):
        check_soa_is_schedulable(config)


def test_the_shipped_soa_grid_is_schedulable(config: Any) -> None:
    lead_s = check_soa_is_schedulable(config)
    assert 0.3 < lead_s < 0.4  # -300 ms plus PTB's arming margin


# ----------------------------------------------------------------- judgement


def test_a_response_maps_onto_the_judgement_it_names(config: Any) -> None:
    module = config.modules.tbw
    assert judge(module.response_labels["same"], module) == SAME
    assert judge(module.response_labels["different"], module) == DIFFERENT


def test_a_timeout_is_no_judgement_at_all(config: Any) -> None:
    module = config.modules.tbw
    assert judge(None, module) is None
    assert judge("   ", module) is None


def test_an_unknown_response_is_an_error_rather_than_a_silent_other(
    config: Any,
) -> None:
    """Modül 1 has an OTHER category; here a response that is neither judgement
    would quietly disappear from the psychometric function."""
    with pytest.raises(ModuleError, match="response_labels"):
        judge("BA", config.modules.tbw)


# -------------------------------------------------------------- config gates


def test_a_third_response_option_is_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["tbw"]["response_set"] = ["Aynı anda", "Farklı zamanda", "Emin değilim"]
    data["modules"]["tbw"]["response_keys"] = ["1", "2", "3"]
    with pytest.raises(ConfigError, match="iki seçenek"):
        _load(write_config, data)


def test_labels_that_do_not_match_the_screen_are_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    """The grid comes from response_set and the meaning from response_labels;
    a mismatch would invert the curve, and an inverted curve still fits."""
    data = copy.deepcopy(config_dict)
    data["modules"]["tbw"]["response_labels"] = {
        "same": "Eszamanli",
        "different": "Farklı zamanda",
    }
    with pytest.raises(ConfigError, match="eşleşmiyor"):
        _load(write_config, data)


def test_a_free_text_option_is_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["tbw"]["free_text_response"] = "Aynı anda"
    with pytest.raises(ConfigError, match="free_text_response"):
        _load(write_config, data)


def test_a_bootstrap_too_small_to_have_tails_is_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["tbw"]["bootstrap_samples"] = 50
    with pytest.raises(ConfigError, match="bootstrap_samples"):
        _load(write_config, data)


def test_bootstrap_can_be_switched_off(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["tbw"]["bootstrap_samples"] = 0
    assert _load(write_config, data).modules.tbw.bootstrap_samples == 0


def test_a_repeated_ear_is_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["tbw"]["ears"] = ["left", "left"]
    with pytest.raises(ConfigError, match="ears"):
        _load(write_config, data)


def test_a_free_text_option_without_its_prompt_is_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    """The other direction of the same rule, on the module that does have one."""
    data = copy.deepcopy(config_dict)
    del data["modules"]["mcgurk"]["prompts"]["other"]
    with pytest.raises(ConfigError, match="prompts.other"):
        _load(write_config, data)
