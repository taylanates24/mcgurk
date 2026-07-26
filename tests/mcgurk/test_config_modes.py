"""``data_collection`` gates: what development tolerates, data collection does not."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from mcgurk.config import ConfigError, load_config


def _data_collection(config_dict: dict[str, Any]) -> dict[str, Any]:
    """Turn the shipped development config into a complete data_collection one."""
    config_dict["experiment"]["mode"] = "data_collection"
    config_dict["timing"]["system_av_offset_ms"] = 12.5
    config_dict["timing"]["measured_on"] = "2026-07-20"
    config_dict["audio"]["calibration_file"] = "config/kalibrasyon.json"
    config_dict["audio"]["device"] = "Speakers (Realtek)"
    config_dict["display"]["fullscreen"] = True
    return config_dict


def test_development_tolerates_missing_measurements(write_config, config_dict) -> None:
    config = load_config(write_config(config_dict))
    assert config.timing.system_av_offset_ms is None
    assert config.audio.calibration_file is None


def test_data_collection_needs_the_av_offset(write_config, config_dict) -> None:
    _data_collection(config_dict)
    config_dict["timing"]["system_av_offset_ms"] = None
    config_dict["timing"]["measured_on"] = None
    with pytest.raises(ConfigError) as exc:
        load_config(write_config(config_dict), check_filesystem=False)
    assert "system_av_offset_ms" in str(exc.value)


def test_data_collection_needs_a_calibration_file(write_config, config_dict) -> None:
    _data_collection(config_dict)
    config_dict["audio"]["calibration_file"] = None
    with pytest.raises(ConfigError) as exc:
        load_config(write_config(config_dict), check_filesystem=False)
    assert "calibration_file" in str(exc.value)


def test_data_collection_requires_fullscreen(write_config, config_dict) -> None:
    # §A.8 — windowed data collection changes the timing silently.
    _data_collection(config_dict)
    config_dict["display"]["fullscreen"] = False
    with pytest.raises(ConfigError) as exc:
        load_config(write_config(config_dict), check_filesystem=False)
    assert "fullscreen" in str(exc.value)


def test_data_collection_requires_an_explicit_audio_device(
    write_config, config_dict
) -> None:
    _data_collection(config_dict)
    config_dict["audio"]["device"] = None
    with pytest.raises(ConfigError) as exc:
        load_config(write_config(config_dict), check_filesystem=False)
    assert "audio.device" in str(exc.value)


def test_all_problems_are_reported_at_once(write_config, config_dict) -> None:
    # The operator should not have to fix one gate, rerun, and find the next.
    #
    # Every gated field is emptied explicitly rather than left as the shipped
    # config happens to have it: the point of the shipped file is that these get
    # filled in — audio.device once the headphones are decided,
    # system_av_offset_ms after the photodiode measurement — and a test that
    # depends on them being empty fails the day the project makes progress.
    config_dict["experiment"]["mode"] = "data_collection"
    config_dict["timing"]["system_av_offset_ms"] = None
    config_dict["timing"]["measured_on"] = None
    config_dict["audio"]["calibration_file"] = None
    config_dict["audio"]["device"] = None
    config_dict["display"]["fullscreen"] = False
    with pytest.raises(ConfigError) as exc:
        load_config(write_config(config_dict), check_filesystem=False)
    message = str(exc.value)
    assert "system_av_offset_ms" in message
    assert "calibration_file" in message
    assert "audio.device" in message
    assert "fullscreen" in message


def test_missing_calibration_file_on_disk_is_caught(
    write_config, config_dict, tmp_path: Path
) -> None:
    _data_collection(config_dict)
    (tmp_path / "stimuli").mkdir()
    path = write_config(config_dict)
    with pytest.raises(ConfigError) as exc:
        load_config(path, project_root=tmp_path)
    assert "Kalibrasyon dosyası okunamadı" in str(exc.value)


def test_missing_stimuli_directory_is_caught(
    write_config, config_dict, tmp_path: Path, calibration_file: Path
) -> None:
    _data_collection(config_dict)
    config_dict["audio"]["calibration_file"] = str(calibration_file)
    path = write_config(config_dict)
    with pytest.raises(ConfigError) as exc:
        load_config(path, project_root=tmp_path)
    assert "paths.stimuli" in str(exc.value)


def test_complete_data_collection_config_loads(
    write_config, config_dict, tmp_path: Path, calibration_file: Path
) -> None:
    _data_collection(config_dict)
    config_dict["audio"]["calibration_file"] = str(calibration_file)
    (tmp_path / "stimuli").mkdir()
    config = load_config(write_config(config_dict), project_root=tmp_path)
    assert config.experiment.mode == "data_collection"
    assert config.timing.system_av_offset_ms == 12.5


def test_filesystem_check_can_be_skipped(write_config, config_dict) -> None:
    _data_collection(config_dict)
    config = load_config(write_config(config_dict), check_filesystem=False)
    assert config.experiment.mode == "data_collection"


def test_malformed_calibration_file_blocks_data_collection(
    write_config, config_dict, tmp_path: Path
) -> None:
    broken = tmp_path / "kalibrasyon.json"
    broken.write_text(json.dumps({"tarih": "2026-07-20T14:30:00"}), encoding="utf-8")
    _data_collection(config_dict)
    config_dict["audio"]["calibration_file"] = str(broken)
    (tmp_path / "stimuli").mkdir()
    with pytest.raises(ConfigError) as exc:
        load_config(write_config(config_dict), project_root=tmp_path)
    assert "beklenen alanları taşımıyor" in str(exc.value)
