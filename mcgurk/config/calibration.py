"""Reader for the calibration file produced by ``02_kalibrasyon.md``.

That script is an external tool and writes Turkish keys, so the field names
here carry aliases instead of the file being rewritten to match the code.

Unknown keys are rejected.  A calibration file whose shape we do not recognise
is a file whose sound-pressure figures we cannot vouch for, and every stimulus
level in the study is derived from them — failing loudly beats guessing.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class CalibrationError(RuntimeError):
    """Raised when the calibration file is missing, unreadable or malformed."""


class Calibration(BaseModel):
    """One calibration run: ``python kalibrasyon.py hesap`` output."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    measured_on: datetime = Field(alias="tarih")
    measurement_dbfs: float = Field(alias="olcum_dbfs")
    spl_left_db: float = Field(alias="spl_sol")
    spl_right_db: float = Field(alias="spl_sag")
    k_left_db: float = Field(alias="K_sol")
    k_right_db: float = Field(alias="K_sag")
    k_mean_db: float = Field(alias="K_ortalama")
    channel_difference_db: float = Field(alias="kanal_farki_db")
    target_spl_db: float = Field(alias="hedef_spl")
    required_dbfs: float = Field(alias="gereken_dbfs")
    trim_left_db: float = Field(alias="trim_sol_db")
    trim_right_db: float = Field(alias="trim_sag_db")

    def age_days(self, now: datetime | None = None) -> float:
        """Days since the measurement.

        The session checklist (Adım 8) turns RED past 30 days; this only
        reports the number.
        """
        reference = now if now is not None else datetime.now()
        return (reference - self.measured_on).total_seconds() / 86400.0


def load_calibration(path: Path | str) -> Calibration:
    """Read and validate a calibration JSON file."""
    calibration_path = Path(path)
    try:
        raw_text = calibration_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CalibrationError(
            f"Kalibrasyon dosyası okunamadı: {calibration_path} ({exc})"
        ) from exc

    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise CalibrationError(
            f"Kalibrasyon dosyası geçerli JSON değil: {calibration_path} ({exc})"
        ) from exc

    if not isinstance(raw, dict):
        raise CalibrationError(
            f"Kalibrasyon dosyası bir nesne (sözlük) olmalı: {calibration_path}"
        )

    try:
        return Calibration.model_validate(raw)
    except ValidationError as exc:
        raise CalibrationError(
            f"Kalibrasyon dosyası beklenen alanları taşımıyor: {calibration_path}\n"
            f"{exc}"
        ) from exc
