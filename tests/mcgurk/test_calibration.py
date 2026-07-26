"""Reading the calibration file written by 02_kalibrasyon.md."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from mcgurk.config import CalibrationError, load_calibration


def test_turkish_keys_map_onto_english_fields(calibration_file: Path) -> None:
    calibration = load_calibration(calibration_file)
    assert calibration.k_mean_db == 80.9
    assert calibration.trim_left_db == -0.3
    assert calibration.trim_right_db == 0.3
    assert calibration.target_spl_db == 65.0
    assert calibration.measured_on == datetime(2026, 7, 20, 14, 30, 0)


def test_age_in_days(calibration_file: Path) -> None:
    calibration = load_calibration(calibration_file)
    # The 30-day rule lives in the Adım 8 checklist; this only reports the age.
    assert calibration.age_days(datetime(2026, 7, 30, 14, 30, 0)) == pytest.approx(10.0)


def test_unknown_key_is_rejected(tmp_path: Path, calibration_data: dict) -> None:
    # An unrecognised shape means figures we cannot vouch for, and every
    # stimulus level in the study is derived from them.
    data = dict(calibration_data, ekstra_alan=1)
    path = tmp_path / "kalibrasyon.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CalibrationError) as exc:
        load_calibration(path)
    assert "ekstra_alan" in str(exc.value)


def test_missing_key_is_rejected(tmp_path: Path, calibration_data: dict) -> None:
    data = calibration_data
    del data["K_ortalama"]
    path = tmp_path / "kalibrasyon.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CalibrationError) as exc:
        load_calibration(path)
    assert "K_ortalama" in str(exc.value)


def test_invalid_json_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "kalibrasyon.json"
    path.write_text("{bu json degil", encoding="utf-8")
    with pytest.raises(CalibrationError) as exc:
        load_calibration(path)
    assert "JSON" in str(exc.value)


def test_json_array_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "kalibrasyon.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(CalibrationError):
        load_calibration(path)


def test_missing_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(CalibrationError) as exc:
        load_calibration(tmp_path / "yok.json")
    assert "okunamadı" in str(exc.value)
