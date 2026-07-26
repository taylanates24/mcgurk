"""Loopback analysis, tested against recordings with a known jitter.

The point of level 2 is to catch a timing chain that only *looks* right, so
its analysis has to be checked the same way: synthesise a recording whose
answer is known, and see whether the detector reports it.  Testing it against
a real recording would only show that it agrees with itself.
"""

from __future__ import annotations

import numpy as np
import pytest

from mcgurk.engine.loopback import (
    LoopbackError,
    analyse_click_train,
    detect_onsets,
    envelope,
    make_click,
)

SAMPLE_RATE = 48000


def synth_recording(
    onsets_s: np.ndarray,
    *,
    duration_s: float = 12.0,
    noise_amplitude: float = 0.001,
    click_ms: float = 3.0,
    seed: int = 7,
) -> np.ndarray:
    """A quiet recording with a tone burst at each of *onsets_s*."""
    rng = np.random.default_rng(seed)
    n = int(duration_s * SAMPLE_RATE)
    signal = rng.normal(0.0, noise_amplitude, n)
    click = make_click(SAMPLE_RATE, duration_ms=click_ms)[:, 0]
    for onset in onsets_s:
        start = int(round(onset * SAMPLE_RATE))
        signal[start : start + click.size] += click
    return signal


def test_envelope_is_positive_and_smooth() -> None:
    t = np.arange(SAMPLE_RATE) / SAMPLE_RATE
    wave = np.sin(2 * np.pi * 1000.0 * t)
    result = envelope(wave, SAMPLE_RATE)
    assert result.min() >= 0.0
    # A raw sine crosses zero 2000 times a second; its envelope must not.
    assert np.count_nonzero(result < 1e-3) < 100


def test_onsets_are_found_where_they_were_put() -> None:
    expected = np.array([1.0, 1.5, 2.0, 2.5, 3.0])
    detected = detect_onsets(synth_recording(expected), SAMPLE_RATE)
    assert detected.size == expected.size
    assert detected == pytest.approx(expected, abs=0.001)


def test_silence_yields_no_onsets() -> None:
    assert detect_onsets(np.zeros(SAMPLE_RATE), SAMPLE_RATE).size == 0


def test_a_perfect_chain_reports_no_jitter() -> None:
    scheduled = np.arange(20) * 0.5
    recording = synth_recording(scheduled + 1.0, duration_s=14.0)
    report = analyse_click_train(recording, SAMPLE_RATE, scheduled)

    assert report.n_detected == 20
    # The constant is the recorder's own head start, not a timing problem.
    assert report.offset_mean_ms == pytest.approx(1000.0, abs=1.0)
    assert report.jitter_sd_ms < 0.2
    assert report.acceptable
    assert "İYİ" in report.verdict


def test_injected_jitter_is_recovered() -> None:
    """3 ms of scatter has to read as ~3 ms, not as a clean chain."""
    rng = np.random.default_rng(3)
    scheduled = np.arange(20) * 0.5
    jitter_s = rng.normal(0.0, 0.003, scheduled.size)
    recording = synth_recording(scheduled + 1.0 + jitter_s, duration_s=14.0)

    report = analyse_click_train(recording, SAMPLE_RATE, scheduled)
    assert report.jitter_sd_ms == pytest.approx(3.0, abs=1.0)


def test_bad_jitter_fails_the_verdict() -> None:
    rng = np.random.default_rng(11)
    scheduled = np.arange(20) * 0.5
    recording = synth_recording(
        scheduled + 1.0 + rng.normal(0.0, 0.010, scheduled.size), duration_s=14.0
    )
    report = analyse_click_train(recording, SAMPLE_RATE, scheduled)
    assert not report.acceptable
    assert "SORUNLU" in report.verdict


def test_a_missing_click_is_reported_not_absorbed() -> None:
    """A dropped sound must not be re-paired into a plausible jitter figure."""
    scheduled = np.arange(20) * 0.5
    played = np.delete(scheduled, 7) + 1.0
    with pytest.raises(LoopbackError, match="bulundu"):
        analyse_click_train(synth_recording(played, duration_s=14.0), SAMPLE_RATE, scheduled)


def test_two_clicks_are_the_minimum() -> None:
    with pytest.raises(LoopbackError):
        analyse_click_train(np.zeros(SAMPLE_RATE), SAMPLE_RATE, np.array([0.0]))


def test_click_is_stereo_and_starts_abruptly() -> None:
    click = make_click(SAMPLE_RATE)
    assert click.shape == (int(0.003 * SAMPLE_RATE), 2)
    assert np.array_equal(click[:, 0], click[:, 1])
    # No ramp: the first cycle is already at full amplitude, which is what
    # makes the onset locatable to a sample.
    assert np.max(np.abs(click[: int(0.001 * SAMPLE_RATE)])) > 0.4
