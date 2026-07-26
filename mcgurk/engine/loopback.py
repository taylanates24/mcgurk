"""Analysis for the loopback self-test (``timing_selftest.py --level 2``).

The headphone output is fed back into an input and a click train with known
scheduled times is recorded.  What comes out is the *jitter* of the audio path:
if PTB quietly fell back to another backend, or ``when=`` was ignored, the
clicks arrive at whatever spacing the software happened to produce and it shows
up here.  This is the real test of the architecture — level 1 can only ask the
software whether it thinks it is doing the right thing.

Pure numpy, no PsychoPy: the analysis is tested against synthetic recordings
with a known jitter injected, so a broken detector cannot pass itself.

The onset criterion (20% of the event's peak) is the one
``docs/01_av_gecikme_olcumu.md`` §11 settled on and measured the bias of.
Keeping the two measurements on the same criterion is what makes their numbers
comparable.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import EngineError


class LoopbackError(EngineError):
    """The recording could not be analysed against the scheduled times."""


def envelope(x: np.ndarray, sample_rate: int, smooth_ms: float = 0.5) -> np.ndarray:
    """Rectify and smooth.

    Working on the raw waveform would put every onset at the first zero
    crossing before the peak, which is a quarter of a cycle early and depends
    on the click frequency.
    """
    rectified = np.abs(np.asarray(x, dtype=np.float64))
    width = max(1, int(round(sample_rate * smooth_ms / 1000.0)))
    if width <= 1:
        return rectified
    return np.convolve(rectified, np.ones(width) / width, mode="same")


def detect_onsets(
    x: np.ndarray,
    sample_rate: int,
    *,
    threshold_factor: float = 8.0,
    refractory_ms: float = 150.0,
    onset_frac: float = 0.2,
    smooth_ms: float = 0.5,
) -> np.ndarray:
    """Times of the events in *x*, in seconds.

    The threshold is derived from the median absolute deviation rather than
    from the mean, so the events themselves — which are the loudest thing in
    the recording — cannot drag it upwards.
    """
    env = envelope(x, sample_rate, smooth_ms)
    if env.size == 0:
        raise LoopbackError("Kayıt boş")

    median = float(np.median(env))
    mad = float(np.median(np.abs(env - median))) + 1e-12
    threshold = median + threshold_factor * 1.4826 * mad

    above = np.flatnonzero(env > threshold)
    if above.size == 0:
        return np.array([], dtype=np.float64)

    refractory = max(1, int(round(sample_rate * refractory_ms / 1000.0)))
    groups = np.split(above, np.flatnonzero(np.diff(above) > refractory) + 1)

    onsets: list[float] = []
    for group in groups:
        peak = int(group[int(np.argmax(env[group]))])
        target = env[peak] * onset_frac
        index = peak
        while index > 0 and env[index] > target:
            index -= 1
        if index < peak and env[index + 1] != env[index]:
            # Linear interpolation between the two samples straddling the
            # criterion: at 48 kHz one sample is 0.02 ms, but the interpolation
            # costs nothing and removes the quantisation from the report.
            fraction = (target - env[index]) / (env[index + 1] - env[index])
            onsets.append(index + float(fraction))
        else:
            onsets.append(float(peak))
    return np.asarray(onsets, dtype=np.float64) / sample_rate


@dataclass(frozen=True)
class JitterReport:
    """How well the realised click times matched the scheduled ones."""

    n_scheduled: int
    n_detected: int
    #: Constant part: the unknown offset between the recorder's clock and the
    #: playback clock, plus the output/input latency.  Not interpretable on its
    #: own — that is what the photodiode measurement is for.
    offset_mean_ms: float
    offset_median_ms: float
    #: The number that matters: spread of the deviations around the constant.
    jitter_sd_ms: float
    max_abs_deviation_ms: float
    #: Deviations from the mean, per click, in presentation order.
    deviations_ms: np.ndarray

    @property
    def verdict(self) -> str:
        """Same thresholds as ``docs/01_av_gecikme_olcumu.md`` §7."""
        if self.jitter_sd_ms < 1.0:
            return "İYİ (< 1 ms)"
        if self.jitter_sd_ms < 3.0:
            return "KABUL EDİLEBİLİR (1–3 ms)"
        return "SORUNLU (> 3 ms) — PTB gerçekten devrede mi?"

    @property
    def acceptable(self) -> bool:
        return self.jitter_sd_ms < 3.0


def analyse_click_train(
    recording: np.ndarray,
    sample_rate: int,
    scheduled_s: np.ndarray,
    *,
    onset_frac: float = 0.2,
) -> JitterReport:
    """Compare detected click times with the times they were scheduled for.

    The recorder's clock starts wherever the operator pressed record, so the
    absolute offset is meaningless and only its *variation* is analysed.  The
    clicks are matched in order, which is why the counts have to agree: a
    missing click means one of them was never played, and silently shifting
    the pairing would turn that into a plausible-looking jitter figure.
    """
    scheduled = np.asarray(scheduled_s, dtype=np.float64)
    if scheduled.size < 2:
        raise LoopbackError("En az iki planlanmış klik gerekli")

    detected = detect_onsets(recording, sample_rate, onset_frac=onset_frac)
    if detected.size != scheduled.size:
        raise LoopbackError(
            f"{scheduled.size} klik planlanmıştı, kayıtta {detected.size} olay "
            "bulundu. Eksikse: 'when' zamanı geçmişte kalmış olabilir, ya da "
            "kayıt seviyesi düşük. Fazlaysa: eşiği aşan gürültü var."
        )

    difference_ms = (detected - scheduled) * 1000.0
    mean = float(np.mean(difference_ms))
    deviations = difference_ms - mean
    return JitterReport(
        n_scheduled=int(scheduled.size),
        n_detected=int(detected.size),
        offset_mean_ms=mean,
        offset_median_ms=float(np.median(difference_ms)),
        jitter_sd_ms=float(np.std(difference_ms, ddof=1)),
        max_abs_deviation_ms=float(np.max(np.abs(deviations))),
        deviations_ms=deviations,
    )


def make_click(
    sample_rate: int, *, duration_ms: float = 3.0, frequency_hz: float = 1000.0,
    amplitude: float = 0.5,
) -> np.ndarray:
    """A short, sharp-onset tone burst as an ``(n, 2)`` array.

    No ramp: the whole point is an onset that can be located to a sample.  It
    is never presented to a participant, only to a cable.
    """
    n = max(1, int(round(sample_rate * duration_ms / 1000.0)))
    t = np.arange(n, dtype=np.float64) / sample_rate
    wave = amplitude * np.sin(2.0 * np.pi * frequency_hz * t)
    return np.column_stack([wave, wave])
