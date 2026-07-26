"""Modül 1 — the design it generates and the categories it assigns.

The acceptance criteria of steps.md §C Adım 4 are all here: changing the AV
pairs changes the trial list, one seed gives one order, and
Vis-/ga/ + Aud-/ba/ answered "DA" is a fusion.
"""

from __future__ import annotations

import copy
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
import yaml

from mcgurk.config.loader import ConfigError, load_config
from mcgurk.db.design import validate_design_extra
from mcgurk.modules.base import ModuleError
from mcgurk.modules.mcgurk import (
    AUDITORY,
    COMBINATION,
    FUSION,
    NONE,
    OTHER,
    QUIET,
    VISUAL,
    categorise,
    categorise_for,
    cell_counts,
    design_cells,
    plan_trials,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STIMULI = Path("stimuli")
SEED = 20260726


@pytest.fixture
def config(write_config: Any, config_dict: dict[str, Any]) -> Any:
    return load_config(write_config(config_dict), check_filesystem=False)


@pytest.fixture
def manifest(config: Any, manifest_factory: Any) -> Any:
    return manifest_factory(config)


def _plan(config: Any, manifest: Any, seed: int = SEED) -> list:
    return plan_trials(config, manifest, seed=seed, stimuli_root=STIMULI)


# ---------------------------------------------------------------- the design


def test_the_generator_produces_exactly_what_the_config_estimated(
    config: Any, manifest: Any
) -> None:
    """Adım 1 put the count in the config layer so the estimate and the real
    design cannot drift apart.  This is the test that keeps that true."""
    assert len(_plan(config, manifest)) == config.trial_counts()["mcgurk"]


def test_the_crossing_is_complete(config: Any, manifest: Any) -> None:
    module = config.modules.mcgurk
    cells, reps = design_cells(module)
    assert len(cells) == len(module.av_pairs) * len(module.noise_conditions) * len(
        module.ears
    )
    assert sum(reps) == len(_plan(config, manifest))


def test_reps_are_per_cell_not_per_pair(config: Any, manifest: Any) -> None:
    """``reps: 10`` means ten presentations in *every* noise × ear cell."""
    planned = _plan(config, manifest)
    fusion = [
        item
        for item in planned
        if item.trial.condition_label == "fusion_pair"
        and item.trial.ear == "left"
        and item.trial.snr_db is None
    ]
    pair = next(p for p in config.modules.mcgurk.av_pairs if p.label == "fusion_pair")
    assert len(fusion) == pair.reps


def test_changing_the_av_pairs_changes_the_trial_list(
    write_config: Any, config_dict: dict[str, Any], manifest_factory: Any
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["mcgurk"]["av_pairs"] = [
        {"visual": "ga", "audio": "ba", "label": "fusion_pair", "reps": 2}
    ]
    data["modules"]["mcgurk"]["fusion_map"] = {"ga|ba": ["da", "ta"]}
    data["modules"]["mcgurk"]["combination_map"] = {}
    trimmed = load_config(write_config(data), check_filesystem=False)
    planned = _plan(trimmed, manifest_factory(trimmed))
    assert len(planned) == 2 * 2 * 2
    assert {item.trial.condition_label for item in planned} == {"fusion_pair"}


def test_every_trial_is_audiovisual_and_has_no_soa(config: Any, manifest: Any) -> None:
    for item in _plan(config, manifest):
        assert item.spec.mode == "AV"
        assert item.trial.presentation_mode == "AV"
        assert item.spec.nominal_soa_ms is None


def test_paths_and_bursts_come_from_the_manifest(config: Any, manifest: Any) -> None:
    item = _plan(config, manifest)[0]
    video = manifest.video(config.modules.mcgurk.speaker_id, item.trial.visual_token)
    token = manifest.token(
        config.modules.mcgurk.speaker_id, item.trial.visual_token, item.trial.audio_token
    )
    assert item.spec.video_path == video.file.resolve(STIMULI)
    assert item.spec.video_burst_s == video.burst_time_s
    # The audio is mounted on the video's own burst (Adım 2), so the two agree —
    # which is what the presenter checks before every AV trial.
    assert item.spec.audio_burst_s == token.burst_time_s
    assert item.spec.video_burst_s == pytest.approx(item.spec.audio_burst_s)


def test_the_noise_condition_names_what_was_mixed_in(config: Any, manifest: Any) -> None:
    planned = _plan(config, manifest)
    quiet = {item.trial.noise_condition for item in planned if item.trial.snr_db is None}
    noisy = {
        item.trial.noise_condition for item in planned if item.trial.snr_db is not None
    }
    assert quiet == {QUIET}
    assert noisy == {config.stimulus_prep.noise.type}


def test_quiet_trials_use_the_clean_file(config: Any, manifest: Any) -> None:
    for item in _plan(config, manifest):
        if item.trial.snr_db is None:
            assert "audio_noisy" not in item.spec.audio_path.as_posix()
            assert item.trial.design_extra["noise_instance"] is None


def test_noisy_trials_carry_the_instance_they_used(config: Any, manifest: Any) -> None:
    instances = config.stimulus_prep.noise.instances
    for item in _plan(config, manifest):
        if item.trial.snr_db is not None:
            used = item.trial.design_extra["noise_instance"]
            assert used in range(1, instances + 1)
            assert f"_{used}.wav" in item.spec.audio_path.name


def test_noise_instances_are_spread_over_the_repetitions_of_a_cell(
    config: Any, manifest: Any
) -> None:
    """Ten repetitions of one noise waveform can be learned; that is why Adım 2
    prepared three."""
    counts: Counter[int] = Counter()
    for item in _plan(config, manifest):
        if (
            item.trial.condition_label == "fusion_pair"
            and item.trial.ear == "left"
            and item.trial.snr_db is not None
        ):
            counts[item.trial.design_extra["noise_instance"]] += 1
    assert len(counts) == config.stimulus_prep.noise.instances
    assert max(counts.values()) - min(counts.values()) <= 1


def test_every_trial_records_the_speaker(config: Any, manifest: Any) -> None:
    speakers = {item.trial.design_extra["speaker_id"] for item in _plan(config, manifest)}
    assert speakers == {config.modules.mcgurk.speaker_id}


def test_the_speaker_can_be_overridden_for_the_session(config: Any, manifest: Any) -> None:
    """§F.4 leaves ``balanced``/``random`` open; the module must not decide."""
    planned = plan_trials(
        config, manifest, seed=SEED, stimuli_root=STIMULI, speaker_id=2
    )
    assert {item.trial.design_extra["speaker_id"] for item in planned} == {2}
    assert all("speaker_2" in str(item.spec.video_path) for item in planned)


def test_the_design_extra_of_every_trial_is_storable(config: Any, manifest: Any) -> None:
    for item in _plan(config, manifest):
        validate_design_extra("mcgurk", item.trial.design_extra)


# ------------------------------------------------------------ reproducibility


def test_same_seed_same_order(config: Any, manifest: Any) -> None:
    first = [item.spec for item in _plan(config, manifest, seed=7)]
    second = [item.spec for item in _plan(config, manifest, seed=7)]
    assert first == second


def test_different_seed_different_order(config: Any, manifest: Any) -> None:
    first = [item.spec.label for item in _plan(config, manifest, seed=7)]
    second = [item.spec.label for item in _plan(config, manifest, seed=8)]
    assert first != second


def test_the_seed_also_fixes_the_noise_instances(config: Any, manifest: Any) -> None:
    first = [item.trial.design_extra["noise_instance"] for item in _plan(config, manifest)]
    second = [item.trial.design_extra["noise_instance"] for item in _plan(config, manifest)]
    assert first == second


def test_the_module_seed_is_independent_of_the_module_order(
    write_config: Any, config_dict: dict[str, Any], manifest_factory: Any
) -> None:
    """Moving mcgurk in ``session.module_order`` must not reshuffle it."""
    data = copy.deepcopy(config_dict)
    baseline = load_config(write_config(data, "a.yaml"), check_filesystem=False)
    order = list(data["session"]["module_order"])
    order.remove("mcgurk")
    order.insert(len(order), "mcgurk")
    data["session"]["module_order"] = order
    moved = load_config(write_config(data, "b.yaml"), check_filesystem=False)

    first = [item.spec.label for item in _plan(baseline, manifest_factory(baseline))]
    second = [item.spec.label for item in _plan(moved, manifest_factory(moved))]
    assert first == second


# ------------------------------------------------------------- failure modes


def test_a_disabled_module_generates_nothing(
    write_config: Any, config_dict: dict[str, Any], manifest_factory: Any
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["mcgurk"]["enabled"] = False
    data["session"]["module_order"] = [
        name for name in data["session"]["module_order"] if name != "mcgurk"
    ]
    config = load_config(write_config(data), check_filesystem=False)
    with pytest.raises(ModuleError, match="enabled"):
        _plan(config, manifest_factory(config))


def test_a_missing_stimulus_fails_before_the_participant_sits_down(
    config: Any, manifest: Any
) -> None:
    manifest.videos = [
        entry for entry in manifest.videos if entry.token != "ga"
    ]
    with pytest.raises(ModuleError, match="prepare_stimuli"):
        _plan(config, manifest)


def test_a_missing_noise_instance_is_also_caught(config: Any, manifest: Any) -> None:
    manifest.noisy_tokens = []
    with pytest.raises(ModuleError, match="prepare_stimuli"):
        _plan(config, manifest)


# ---------------------------------------------------------- categorisation


FUSION_MAP = {"ga|ba": ["da", "ta"]}
COMBINATION_MAP = {"ba|ga": ["bga"]}


def _cat(response: str | None, *, visual: str = "ga", audio: str = "ba") -> str:
    """Categorise *response* with the maps the shipped config carries."""
    return categorise(
        response,
        visual_token=visual,
        audio_token=audio,
        fusion_map=FUSION_MAP,
        combination_map=COMBINATION_MAP,
    )


def test_the_fusion_case_from_the_acceptance_criteria() -> None:
    assert _cat("DA") == FUSION


def test_a_second_response_can_be_a_fusion_too() -> None:
    assert _cat("TA") == FUSION


def test_the_audio_token_is_an_auditory_response() -> None:
    assert _cat("BA") == AUDITORY


def test_the_visual_token_is_a_visual_response() -> None:
    assert _cat("GA") == VISUAL


def test_a_combination_needs_its_own_pair() -> None:
    assert _cat("BGA", visual="ba", audio="ga") == COMBINATION
    # The same response on the fusion pair is not a combination: the maps are
    # keyed by pair, because what counts as fused depends on what was shown.
    assert _cat("BGA") == OTHER


def test_anything_else_is_other() -> None:
    assert _cat("KA") == OTHER
    assert _cat("DIGER") == OTHER


def test_no_response_is_none() -> None:
    assert _cat(None) == NONE
    assert _cat("   ") == NONE


def test_case_and_spacing_do_not_matter() -> None:
    assert _cat(" da ") == FUSION
    assert _cat("Da") == FUSION


def test_a_congruent_control_answered_correctly_is_auditory() -> None:
    """There is no ``is_correct`` in this module (§A.10); the congruent controls
    are read through the same categories as everything else."""
    assert _cat("BA", visual="ba", audio="ba") == AUDITORY


def test_categorising_a_real_trial_uses_the_config_maps(
    config: Any, manifest: Any
) -> None:
    item = next(
        item
        for item in _plan(config, manifest)
        if item.trial.condition_label == "fusion_pair"
    )
    assert categorise_for(config.modules.mcgurk, "DA", item.trial) == FUSION
    assert categorise_for(config.modules.mcgurk, "BA", item.trial) == AUDITORY


def test_categorisation_needs_both_tokens(config: Any, manifest: Any) -> None:
    item = _plan(config, manifest)[0]
    item.trial.visual_token = None
    with pytest.raises(ModuleError):
        categorise_for(config.modules.mcgurk, "DA", item.trial)


# ------------------------------------------------------- config-side guards


def _write(write_config: Any, data: dict[str, Any]) -> None:
    load_config(write_config(data), check_filesystem=False)


def test_a_map_that_repeats_the_pairs_own_token_is_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    """Ordered categorisation makes such a rule unreachable, and whoever wrote
    it expected it to fire."""
    data = copy.deepcopy(config_dict)
    data["modules"]["mcgurk"]["fusion_map"] = {"ga|ba": ["ba"]}
    with pytest.raises(ConfigError, match="kendi"):
        _write(write_config, data)


def test_response_keys_must_cover_the_response_set(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["mcgurk"]["response_keys"] = ["1", "2"]
    with pytest.raises(ConfigError, match="aynı uzunlukta"):
        _write(write_config, data)


def test_duplicate_response_keys_are_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    data = copy.deepcopy(config_dict)
    keys = list(data["modules"]["mcgurk"]["response_keys"])
    keys[1] = keys[0]
    data["modules"]["mcgurk"]["response_keys"] = keys
    with pytest.raises(ConfigError, match="tekrarlı tuş"):
        _write(write_config, data)


def test_the_free_text_option_has_to_be_offered(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["mcgurk"]["free_text_response"] = "BASKA"
    with pytest.raises(ConfigError, match="free_text_response"):
        _write(write_config, data)


def test_the_prompts_are_required(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    """§A.9 — a participant-facing string has nowhere else to live."""
    data = copy.deepcopy(config_dict)
    del data["modules"]["mcgurk"]["prompts"]
    with pytest.raises(ConfigError, match="prompts"):
        _write(write_config, data)


def test_an_empty_prompt_is_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["mcgurk"]["prompts"]["question"] = ""
    with pytest.raises(ConfigError):
        _write(write_config, data)


# ------------------------------------------------------------- design summary


def test_the_cell_table_is_built_from_the_plan_that_will_run(
    config: Any, manifest: Any
) -> None:
    planned = _plan(config, manifest)
    counts = cell_counts(planned)
    assert sum(counts.values()) == len(planned)
    assert len(counts) == len(design_cells(config.modules.mcgurk)[0])


def test_the_shipped_config_is_still_readable_as_yaml() -> None:
    """The prompts carry Turkish text and quoted digits; a broken quote in the
    shipped file would only surface at run time otherwise."""
    shipped = PROJECT_ROOT / "config" / "experiment.yaml"
    raw = yaml.safe_load(shipped.read_text(encoding="utf-8"))
    keys = raw["modules"]["mcgurk"]["response_keys"]
    assert all(isinstance(key, str) for key in keys)
