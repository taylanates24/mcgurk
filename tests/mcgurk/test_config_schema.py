"""Schema validation: the shipped config is valid and bad ones fail loudly."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from mcgurk.config import ConfigError, load_config


def _load(write_config, data: dict[str, Any]):
    return load_config(write_config(data), check_filesystem=False)


def test_shipped_config_is_valid() -> None:
    config = load_config(check_filesystem=False)
    assert config.experiment.name == "mcgurk_ssd"
    assert config.experiment.mode == "development"


def test_unknown_field_is_rejected(write_config, config_dict) -> None:
    config_dict["experiment"]["oda_sicakligi"] = 21
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "oda_sicakligi" in str(exc.value)


def test_unknown_module_field_is_rejected(write_config, config_dict) -> None:
    config_dict["modules"]["gin"]["gap_duration_ms"] = [2, 3]  # missing 's'
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "gap_duration_ms" in str(exc.value)


def test_missing_required_field_is_rejected(write_config, config_dict) -> None:
    del config_dict["modules"]["oddball"]["n_trials"]
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "n_trials" in str(exc.value)


def test_missing_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as exc:
        load_config(tmp_path / "yok.yaml")
    assert "okunamadı" in str(exc.value)


def test_invalid_yaml_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "bozuk.yaml"
    path.write_text("experiment: [unclosed\n", encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        load_config(path)
    assert "YAML" in str(exc.value)


# ---------------------------------------------------------------- display


def test_video_must_stay_centred(write_config, config_dict) -> None:
    # §A.13 — off-centre presentation contradicts the method document.
    config_dict["display"]["video_position"] = [100, 0]
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "video_position" in str(exc.value)


# ----------------------------------------------------------------- timing


def test_offset_without_a_measurement_date_is_rejected(
    write_config, config_dict
) -> None:
    config_dict["timing"]["system_av_offset_ms"] = 12.5
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "measured_on" in str(exc.value)


# ----------------------------------------------------------------- mcgurk


def test_fusion_map_key_must_be_a_real_pair(write_config, config_dict) -> None:
    config_dict["modules"]["mcgurk"]["fusion_map"]["ga|pa"] = ["ta"]
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "ga|pa" in str(exc.value)


def test_fusion_map_value_must_be_in_response_set(write_config, config_dict) -> None:
    config_dict["modules"]["mcgurk"]["fusion_map"]["ga|ba"] = ["da", "zzz"]
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "zzz" in str(exc.value)


def test_duplicate_ears_are_rejected(write_config, config_dict) -> None:
    config_dict["modules"]["mcgurk"]["ears"] = ["left", "left"]
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "ears" in str(exc.value)


# ------------------------------------------------------------------- avsr


def test_syllable_set_needs_tokens(write_config, config_dict) -> None:
    config_dict["modules"]["avsr"]["stimulus_sets"][0].pop("tokens")
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "tokens" in str(exc.value)


def test_word_set_needs_a_list(write_config, config_dict) -> None:
    config_dict["modules"]["avsr"]["stimulus_sets"][1].pop("list")
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "list" in str(exc.value)


def test_enabled_word_set_is_not_supported_yet(write_config, config_dict) -> None:
    # §F.2: the recording session has not happened.  Counting the trials of a
    # word set we cannot read would be a guess, so it is an explicit error.
    config_dict["modules"]["avsr"]["stimulus_sets"][1]["enabled"] = True
    config = _load(write_config, config_dict)
    with pytest.raises(ValueError, match="Adım 5"):
        config.modules.avsr.total_trials()


# -------------------------------------------------------------------- tbw


def test_soa_values_must_be_sorted(write_config, config_dict) -> None:
    config_dict["modules"]["tbw"]["soa_values_ms"] = [0, -50, 50]
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "artan" in str(exc.value)


def test_response_labels_keys_are_fixed(write_config, config_dict) -> None:
    config_dict["modules"]["tbw"]["response_labels"] = {"ayni": "Aynı"}
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "response_labels" in str(exc.value)


# ---------------------------------------------------------------- oddball


def test_ramp_longer_than_tone_is_rejected(write_config, config_dict) -> None:
    config_dict["modules"]["oddball"]["tone_ramp_ms"] = 30  # 2 × 30 > 50
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "rampa" in str(exc.value)


def test_impossible_target_spacing_is_rejected(write_config, config_dict) -> None:
    config_dict["modules"]["oddball"]["min_standards_between_targets"] = 10
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "standart" in str(exc.value)


def test_identical_tone_frequencies_are_rejected(write_config, config_dict) -> None:
    config_dict["modules"]["oddball"]["target_hz"] = 1000
    with pytest.raises(ConfigError):
        _load(write_config, config_dict)


# --------------------------------------------------------------- dichotic


def test_dichotic_pair_must_differ(write_config, config_dict) -> None:
    config_dict["modules"]["dichotic"]["pairs"][0] = {"left": "ba", "right": "ba"}
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "dikotik" in str(exc.value)


def test_duplicate_dichotic_pair_is_rejected(write_config, config_dict) -> None:
    config_dict["modules"]["dichotic"]["pairs"][1] = {"left": "ba", "right": "da"}
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "tekrarlı" in str(exc.value)


# -------------------------------------------------------------------- gin


def test_threshold_criterion_format(write_config, config_dict) -> None:
    config_dict["modules"]["gin"]["threshold_criterion"] = "dörtte altı"
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "threshold_criterion" in str(exc.value)


def test_threshold_criterion_must_match_reps(write_config, config_dict) -> None:
    config_dict["modules"]["gin"]["threshold_criterion"] = "4_of_8"
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "reps_per_gap" in str(exc.value)


def test_gaps_must_fit_into_the_segments(write_config, config_dict) -> None:
    config_dict["modules"]["gin"]["n_segments"] = 10  # 10 × 3 = 30 < 60 gaps
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "sığmıyor" in str(exc.value)


def test_gap_separation_must_fit_the_segment_duration(
    write_config, config_dict
) -> None:
    config_dict["modules"]["gin"]["min_gap_separation_s"] = 3.0
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "segment" in str(exc.value)


def test_fixed_ear_selection_needs_an_ear(write_config, config_dict) -> None:
    config_dict["modules"]["gin"]["ear_selection"] = "fixed"
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "fixed_ear" in str(exc.value)


def test_fixed_ear_without_fixed_selection_is_rejected(
    write_config, config_dict
) -> None:
    config_dict["modules"]["gin"]["fixed_ear"] = "right"
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "fixed_ear" in str(exc.value)


# ------------------------------------------------------- cross-section rules


def test_enabled_module_must_be_in_module_order(write_config, config_dict) -> None:
    config_dict["session"]["module_order"].remove("gin")
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "gin" in str(exc.value)


def test_module_order_cannot_name_a_disabled_module(
    write_config, config_dict
) -> None:
    config_dict["modules"]["gin"]["enabled"] = False
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "enabled false" in str(exc.value)


def test_disabled_module_removed_from_order_is_fine(
    write_config, config_dict
) -> None:
    config_dict["modules"]["gin"]["enabled"] = False
    config_dict["session"]["module_order"].remove("gin")
    config = _load(write_config, config_dict)
    assert "gin" not in config.enabled_modules()


def test_duplicate_module_in_order_is_rejected(write_config, config_dict) -> None:
    config_dict["session"]["module_order"].append("gin")
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "tekrarlı" in str(exc.value)


def test_fixed_speaker_strategy_needs_an_id(write_config, config_dict) -> None:
    config_dict["speaker_selection"].pop("fixed_id")
    with pytest.raises(ConfigError) as exc:
        _load(write_config, config_dict)
    assert "fixed_id" in str(exc.value)
