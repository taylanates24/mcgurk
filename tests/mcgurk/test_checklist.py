"""The pre-session checklist (Adım 8a).

The RED path is the acceptance criterion: a missing or stale calibration must
turn the check RED and block a data_collection session.  All of this runs
without PsychoPy — ``run_checks(probe_hardware=False)`` skips the hardware
probes, which is the whole reason the checks are split that way.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from mcgurk.checklist import Status, any_red, main, run_checks
from mcgurk.config import load_config


def _load(config_dict: dict[str, Any], write_config, tmp_path: Path):
    """Load *config_dict* without touching the disk gates."""
    return load_config(
        write_config(config_dict), project_root=tmp_path, check_filesystem=False
    )


def _data_collection(config_dict: dict[str, Any]) -> dict[str, Any]:
    """A schema-valid data_collection config, calibration_file left to caller."""
    config_dict["experiment"]["mode"] = "data_collection"
    config_dict["timing"]["system_av_offset_ms"] = 12.5
    config_dict["timing"]["measured_on"] = "2026-07-20"
    config_dict["audio"]["device"] = "Speakers (Realtek)"
    config_dict["display"]["fullscreen"] = True
    return config_dict


def _calibration_file(
    tmp_path: Path, calibration_data: dict[str, Any], *, days_old: float
) -> Path:
    when = datetime.now() - timedelta(days=days_old)
    calibration_data["tarih"] = when.isoformat(timespec="seconds")
    path = tmp_path / "kalibrasyon.json"
    path.write_text(
        json.dumps(calibration_data, ensure_ascii=False), encoding="utf-8"
    )
    return path


def _by_name(checks: list[Any], name: str) -> Any:
    for check in checks:
        if check.name == name:
            return check
    raise AssertionError(f"'{name}' adlı kontrol yok: {[c.name for c in checks]}")


# ------------------------------------------------------------------ dev path


def test_development_gates_are_warnings_not_red(
    config_dict, write_config, tmp_path
) -> None:
    # The shipped development config has no calibration and no offset; those are
    # WARN, not RED, because a development session legitimately runs without them.
    # (The stimulus check is still RED under a temp root with no manifest, so
    # this asserts on the gates the test is about, not on the whole set.)
    config = _load(config_dict, write_config, tmp_path)
    checks = run_checks(config, tmp_path, probe_hardware=False)
    assert _by_name(checks, "Mod").status is Status.WARN
    assert _by_name(checks, "A/V gecikmesi (D)").status is Status.WARN
    assert _by_name(checks, "Kalibrasyon").status is Status.WARN


# ------------------------------------------------------------ calibration RED


def test_missing_calibration_file_is_red(
    config_dict, write_config, tmp_path
) -> None:
    _data_collection(config_dict)
    config_dict["audio"]["calibration_file"] = str(tmp_path / "yok.json")
    config = _load(config_dict, write_config, tmp_path)
    checks = run_checks(config, tmp_path, probe_hardware=False)
    assert _by_name(checks, "Kalibrasyon").status is Status.RED
    assert any_red(checks)


def test_stale_calibration_is_red(
    config_dict, write_config, tmp_path, calibration_data
) -> None:
    calibration = _calibration_file(tmp_path, calibration_data, days_old=45)
    _data_collection(config_dict)
    config_dict["audio"]["calibration_file"] = str(calibration)
    config = _load(config_dict, write_config, tmp_path)
    checks = run_checks(config, tmp_path, probe_hardware=False)
    calibration_check = _by_name(checks, "Kalibrasyon")
    assert calibration_check.status is Status.RED
    assert "30" in calibration_check.detail  # the configured max age
    assert any_red(checks)


def test_fresh_calibration_is_green(
    config_dict, write_config, tmp_path, calibration_data
) -> None:
    calibration = _calibration_file(tmp_path, calibration_data, days_old=3)
    _data_collection(config_dict)
    config_dict["audio"]["calibration_file"] = str(calibration)
    config = _load(config_dict, write_config, tmp_path)
    checks = run_checks(config, tmp_path, probe_hardware=False)
    assert _by_name(checks, "Kalibrasyon").status is Status.GREEN


def test_calibration_age_threshold_comes_from_config(
    config_dict, write_config, tmp_path, calibration_data
) -> None:
    # 20 days old: RED at a 10-day limit, GREEN at 30.  The QC threshold is a
    # config parameter, not a constant in the code (§A.9).
    calibration = _calibration_file(tmp_path, calibration_data, days_old=20)
    _data_collection(config_dict)
    config_dict["audio"]["calibration_file"] = str(calibration)

    config_dict["checklist"]["calibration_max_age_days"] = 10
    strict = _load(config_dict, write_config, tmp_path)
    assert _by_name(
        run_checks(strict, tmp_path, probe_hardware=False), "Kalibrasyon"
    ).status is Status.RED

    config_dict["checklist"]["calibration_max_age_days"] = 30
    lenient = _load(config_dict, write_config, tmp_path)
    assert _by_name(
        run_checks(lenient, tmp_path, probe_hardware=False), "Kalibrasyon"
    ).status is Status.GREEN


# --------------------------------------------------------------- stimuli RED


def test_missing_stimulus_set_is_red(config_dict, write_config, tmp_path) -> None:
    # No stimuli/ under tmp_path, so the manifest cannot be read.
    config = _load(config_dict, write_config, tmp_path)
    checks = run_checks(config, tmp_path, probe_hardware=False)
    assert _by_name(checks, "Uyaran seti").status is Status.RED
    assert any_red(checks)


# ------------------------------------------------------------ disk and backup


def test_backup_is_warn_when_none_exists(
    config_dict, write_config, tmp_path
) -> None:
    config = _load(config_dict, write_config, tmp_path)
    checks = run_checks(config, tmp_path, probe_hardware=False)
    assert _by_name(checks, "Son yedek").status is Status.WARN


def test_insufficient_disk_is_red(config_dict, write_config, tmp_path) -> None:
    # An unreachable free-space threshold: no volume has an exabyte free.
    config_dict["checklist"]["min_free_disk_mb"] = 10**12
    config = _load(config_dict, write_config, tmp_path)
    checks = run_checks(config, tmp_path, probe_hardware=False)
    assert _by_name(checks, "Disk ve yedek klasörü").status is Status.RED


# ---------------------------------------------------------------------- main


def test_main_rejects_an_incomplete_data_collection_config(
    config_dict, write_config
) -> None:
    # A data_collection config with no photodiode offset does not even load —
    # the schema names the missing field — and the CLI returns non-zero.
    config_dict["experiment"]["mode"] = "data_collection"
    config_dict["timing"]["system_av_offset_ms"] = None
    config_dict["timing"]["measured_on"] = None
    config_dict["audio"]["calibration_file"] = "config/kalibrasyon.json"
    config_dict["audio"]["device"] = "Speakers (Realtek)"
    path = write_config(config_dict)
    assert main(["--config", str(path), "--no-hardware"]) == 1


def test_main_runs_the_shipped_config_end_to_end() -> None:
    # The real shipped config through the whole CLI (load, checks, render, exit),
    # hardware probes skipped.  The exit code depends on whether this machine has
    # the ~70 MB gitignored stimulus set — absent on CI, present after Adım 2 —
    # so the assertion is only that the tool ran and returned a verdict, not
    # which one.  The RED/GREEN logic itself is pinned by the tests above.
    assert main(["--no-hardware"]) in (0, 1)
