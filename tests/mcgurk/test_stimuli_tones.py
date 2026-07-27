"""The oddball tones: what makes a 50 ms sinusoid a tone and not a click.

steps.md §C Adım 7 asks for exactly this — "ton dosyalarında klik yok
(onset/offset rampası doğrulanmış)".  It matters more than it looks: an
un-ramped tone is distinguishable from another un-ramped tone by its click
alone, so a participant could do the whole detection task without ever hearing
a pitch difference, and the attention control would be measuring something else.
"""

from __future__ import annotations

import numpy as np
import pytest

from mcgurk.stimuli.dsp import DSPError, dominant_frequency_hz, peak_dbfs, rms, to_db, tone

RATE = 48000


def _tone(frequency: float = 1000.0, duration_ms: float = 50.0, ramp_ms: float = 10.0):
    return tone(frequency, duration_ms, RATE, ramp_ms=ramp_ms, level_dbfs=-23.0)


def test_the_tone_has_the_length_it_was_asked_for() -> None:
    assert _tone(duration_ms=50.0).size == int(round(0.050 * RATE))


def test_the_tone_carries_the_frequency_it_is_named_after() -> None:
    for frequency in (1000.0, 1500.0):
        measured = dominant_frequency_hz(_tone(frequency), RATE)
        assert measured == pytest.approx(frequency, abs=RATE / (0.050 * RATE) * 2)


def test_the_level_is_the_rms_of_the_whole_file() -> None:
    assert to_db(rms(_tone())) == pytest.approx(-23.0, abs=0.01)


def test_the_tone_starts_and_ends_at_silence() -> None:
    samples = _tone()
    assert abs(float(samples[0])) < 1e-9
    assert abs(float(samples[-1])) < 1e-3


def test_the_ramp_is_actually_a_ramp() -> None:
    """A quarter of the way into a 10 ms raised-cosine fade the envelope is at
    ~15% of full scale.  An un-ramped tone is already at 100% there, which is
    the failure this is looking for."""
    samples = _tone(ramp_ms=10.0)
    ramp_samples = int(round(0.010 * RATE))
    quarter = float(np.max(np.abs(samples[: ramp_samples // 4])))
    plateau = float(np.max(np.abs(samples)))
    assert quarter < 0.5 * plateau


def test_a_ramped_tone_splatters_far_less_than_a_gated_one() -> None:
    """The click is spectral splatter, so it is measurable — but only in the
    silence the tone is presented in.

    Measured on the tone alone, a gated 1 kHz tone of exactly 50 ms looks
    perfectly clean: 50 whole cycles fit the window, so the DFT sees one bin and
    no leakage at all.  What the listener hears is the step against the silence
    on either side, which is why the tone is padded here before it is measured.
    """
    silence = np.zeros(int(0.05 * RATE))

    def out_of_band_energy(samples: np.ndarray) -> float:
        padded = np.concatenate([silence, samples, silence])
        spectrum = np.abs(np.fft.rfft(padded))
        freqs = np.fft.rfftfreq(padded.size, 1.0 / RATE)
        far = spectrum[np.abs(freqs - 1000.0) > 500.0]
        return float(np.sum(far**2) / np.sum(spectrum**2))

    ramped = _tone(ramp_ms=10.0)
    gated = _tone(ramp_ms=0.0)
    assert out_of_band_energy(ramped) < 0.01 * out_of_band_energy(gated)


def test_the_peak_leaves_headroom_for_the_calibration_trim() -> None:
    assert peak_dbfs(_tone()) < -1.0


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"duration_ms": 0.0}, "pozitif"),
        ({"duration_ms": 10.0, "ramp_ms": 20.0}, "rampa"),
        ({"frequency": 30000.0}, "Nyquist"),
        ({"frequency": 0.0}, "Nyquist"),
    ],
)
def test_an_impossible_tone_is_refused(kwargs: dict, match: str) -> None:
    with pytest.raises(DSPError, match=match):
        _tone(**kwargs)


def test_the_dominant_frequency_of_a_two_tone_mixture_is_the_louder_one() -> None:
    """The measurement has to be a measurement, not a lucky argmax on a pure
    sine: it is what verify_stimuli.py checks a written file against."""
    n = int(0.2 * RATE)
    t = np.arange(n) / RATE
    mixture = np.sin(2 * np.pi * 1500 * t) + 0.2 * np.sin(2 * np.pi * 1000 * t)
    assert dominant_frequency_hz(mixture, RATE) == pytest.approx(1500.0, abs=10.0)


def test_a_signal_too_short_to_have_a_spectrum_is_refused() -> None:
    with pytest.raises(DSPError, match="çok kısa"):
        dominant_frequency_hz(np.zeros(1), RATE)
