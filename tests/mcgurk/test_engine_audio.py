"""Lateralisation, calibration trim and WAV loading.

No PsychoPy: everything here is the array work that happens before a sound
object exists, which is where the manipulations that carry the SSD hypothesis
(which ear) and the calibration (what level) actually get applied.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from mcgurk.config.calibration import Calibration
from mcgurk.engine.audio import (
    AudioError,
    AudioStimulus,
    apply_trim,
    db_to_gain,
    lateralise,
    load_audio,
    prepare_samples,
)
from mcgurk.stimuli.wavfile import write as write_wav

SAMPLE_RATE = 48000


@pytest.fixture
def speech() -> np.ndarray:
    """A short mono signal with a recognisable shape."""
    t = np.arange(int(0.2 * SAMPLE_RATE)) / SAMPLE_RATE
    return 0.5 * np.sin(2 * np.pi * 440.0 * t)


def calibration(left_db: float, right_db: float) -> Calibration:
    return Calibration.model_validate(
        {
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
            "trim_sol_db": left_db,
            "trim_sag_db": right_db,
        }
    )


# ------------------------------------------------------------------- gains


def test_db_to_gain() -> None:
    assert db_to_gain(0.0) == pytest.approx(1.0)
    assert db_to_gain(-6.0206) == pytest.approx(0.5, abs=1e-4)
    assert db_to_gain(6.0206) == pytest.approx(2.0, abs=1e-4)


# ----------------------------------------------------------- lateralisation


@pytest.mark.parametrize("ear", ["left", "right"])
def test_the_other_ear_gets_exactly_nothing(speech: np.ndarray, ear: str) -> None:
    """Not "attenuated" — zero.

    The manipulation only means anything if the sound card sends nothing to
    the other side; whatever reaches it then travelled through the skull, which
    is what the cross-hearing check (Adım 8) is there to measure.
    """
    stereo = lateralise(speech, ear)
    silent = stereo[:, 1] if ear == "left" else stereo[:, 0]
    assert stereo.shape == (speech.size, 2)
    assert np.count_nonzero(silent) == 0


def test_lateralised_channel_is_the_signal_unchanged(speech: np.ndarray) -> None:
    assert np.array_equal(lateralise(speech, "left")[:, 0], speech)
    assert np.array_equal(lateralise(speech, "right")[:, 1], speech)


def test_both_ears_get_identical_copies(speech: np.ndarray) -> None:
    stereo = lateralise(speech, "both")
    assert np.array_equal(stereo[:, 0], stereo[:, 1])
    assert np.array_equal(stereo[:, 0], speech)


def test_unknown_ear_is_refused(speech: np.ndarray) -> None:
    with pytest.raises(AudioError, match="Bilinmeyen kulak"):
        lateralise(speech, "middle")


def test_stereo_input_cannot_be_lateralised(speech: np.ndarray) -> None:
    with pytest.raises(AudioError):
        lateralise(np.column_stack([speech, speech]), "left")


# --------------------------------------------------------------------- trim


def test_trim_is_applied_per_channel(speech: np.ndarray) -> None:
    stereo = lateralise(speech, "both")
    trimmed = apply_trim(stereo, calibration(-6.0206, 0.0))
    assert trimmed[:, 0] == pytest.approx(speech * 0.5, abs=1e-4)
    assert trimmed[:, 1] == pytest.approx(speech)


def test_no_calibration_means_no_gain(speech: np.ndarray) -> None:
    stereo = lateralise(speech, "both")
    assert np.array_equal(apply_trim(stereo, None), stereo)


def test_clipping_trim_is_an_error_not_a_limiter(speech: np.ndarray) -> None:
    """Every level in the study derives from the calibration figures.

    A limiter here would turn a wrong trim into a quietly distorted stimulus
    that still looks like a valid one.
    """
    with pytest.raises(AudioError, match="kırpıyor"):
        prepare_samples(speech, ear="both", calibration=calibration(12.0, 12.0))


# ---------------------------------------------------------------- dichotic


def test_dichotic_file_is_passed_through_untouched(speech: np.ndarray) -> None:
    """A prepared dichotic file already has a different token in each ear."""
    left = speech
    right = np.roll(speech, 100)
    stereo = np.column_stack([left, right])
    prepared = prepare_samples(stereo, ear="both")
    assert np.array_equal(prepared[:, 0], left)
    assert np.array_equal(prepared[:, 1], right)


def test_dichotic_file_cannot_be_routed_to_one_ear(speech: np.ndarray) -> None:
    stereo = np.column_stack([speech, np.roll(speech, 100)])
    with pytest.raises(AudioError, match="dikotik"):
        prepare_samples(stereo, ear="left")


def test_dichotic_file_still_gets_the_trim(speech: np.ndarray) -> None:
    stereo = np.column_stack([speech, speech])
    prepared = prepare_samples(stereo, ear="both", calibration=calibration(-6.0206, 0.0))
    assert prepared[:, 0] == pytest.approx(speech * 0.5, abs=1e-4)
    assert prepared[:, 1] == pytest.approx(speech)


# -------------------------------------------------------------------- files


def test_load_audio_lateralises_and_reports_duration(
    tmp_path: Path, speech: np.ndarray
) -> None:
    path = tmp_path / "token.wav"
    write_wav(path, speech, SAMPLE_RATE, bit_depth=24)

    stimulus = load_audio(
        path, ear="right", burst_time_s=1.092, expected_sample_rate=SAMPLE_RATE
    )
    assert isinstance(stimulus, AudioStimulus)
    assert stimulus.samples.shape == (speech.size, 2)
    assert np.count_nonzero(stimulus.samples[:, 0]) == 0
    assert stimulus.duration_s == pytest.approx(0.2)
    assert stimulus.burst_time_s == 1.092


def test_wrong_sample_rate_is_refused_rather_than_resampled(
    tmp_path: Path, speech: np.ndarray
) -> None:
    """§A.12: resampling at run time would also move every burst time."""
    path = tmp_path / "token.wav"
    write_wav(path, speech, 44100, bit_depth=24)
    with pytest.raises(AudioError, match="örnekleme hızı"):
        load_audio(path, ear="both", expected_sample_rate=48000)


def test_missing_file_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(AudioError):
        load_audio(tmp_path / "yok.wav", ear="both")
