"""Fixtures for the mcgurk package tests.

The shipped ``config/experiment.yaml`` is the starting point for every config
test.  Building a synthetic config here instead would let the real one rot
without a single test noticing.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SHIPPED_CONFIG = PROJECT_ROOT / "config" / "experiment.yaml"


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip ``ffmpeg``-marked tests where no ffmpeg binary exists.

    Stimulus preparation is not something CI has to be able to run — it is an
    offline step done once per corpus — but the DSP it is built on is, so only
    the tests that actually shell out are skipped.
    """
    if "ffmpeg" not in item.keywords:
        return
    from mcgurk.stimuli.ffmpeg import FFmpegError, find_ffmpeg

    try:
        find_ffmpeg()
    except FFmpegError as exc:
        pytest.skip(str(exc))

#: Exactly the shape ``kalibrasyon.py hesap`` writes (02_kalibrasyon.md).
CALIBRATION_JSON: dict[str, Any] = {
    "tarih": "2026-07-20T14:30:00",
    "olcum_dbfs": -23.0,
    "spl_sol": 58.2,
    "spl_sag": 57.6,
    "K_sol": 81.2,
    "K_sag": 80.6,
    "K_ortalama": 80.9,
    "kanal_farki_db": 0.6,
    "hedef_spl": 65.0,
    "gereken_dbfs": -15.9,
    "trim_sol_db": -0.3,
    "trim_sag_db": 0.3,
}


@pytest.fixture
def config_dict() -> dict[str, Any]:
    """The shipped configuration as a mutable dictionary."""
    raw = yaml.safe_load(SHIPPED_CONFIG.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return copy.deepcopy(raw)


@pytest.fixture
def write_config(tmp_path: Path):
    """Write a config dictionary to disk and return its path."""

    def _write(data: dict[str, Any], name: str = "experiment.yaml") -> Path:
        path = tmp_path / name
        path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return path

    return _write


@pytest.fixture
def calibration_data() -> dict[str, Any]:
    return copy.deepcopy(CALIBRATION_JSON)


@pytest.fixture
def calibration_file(tmp_path: Path) -> Path:
    path = tmp_path / "kalibrasyon.json"
    path.write_text(
        json.dumps(CALIBRATION_JSON, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path
