"""Signal processing for stimulus preparation.

Pure numpy/scipy: every function takes and returns arrays, touches no files and
imports nothing from the rest of the package.  That is what makes the parts
that actually decide the experiment — where the burst is, what "equal level"
means, what SNR a mixture has — testable against synthetic signals with known
answers instead of against the corpus.
"""

from __future__ import annotations

import numpy as np
from scipy import signal

from . import StimulusError

#: Amplitude below which dB conversion saturates, so digital silence produces
#: a very negative number instead of -inf.
_FLOOR = 1e-12


class DSPError(StimulusError):
    """A measurement could not be made on the signal it was given."""


# ------------------------------------------------------------------- levels


def to_mono(x: np.ndarray) -> np.ndarray:
    """Average multi-channel input down to one channel."""
    if x.ndim == 1:
        return x
    return np.asarray(np.asarray(x, dtype=np.float64).mean(axis=1))


def rms(x: np.ndarray) -> float:
    if x.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(x, dtype=np.float64))))


def to_db(amplitude: float) -> float:
    """Amplitude ratio to dB, floored so silence is finite."""
    return 20.0 * float(np.log10(max(abs(amplitude), _FLOOR)))


def peak_dbfs(x: np.ndarray) -> float:
    if x.size == 0:
        return to_db(0.0)
    return to_db(float(np.max(np.abs(x))))


def frame_rms(
    x: np.ndarray,
    sample_rate: int,
    frame_ms: float,
    hop_ms: float | None = None,
) -> np.ndarray:
    """RMS of successive frames of *x*.

    Frames run forwards from their index (``frame i`` covers
    ``[i*hop, i*hop+frame)``), so the frame index of a rising edge is the frame
    the edge falls in — which is what the burst detector needs.
    """
    mono = to_mono(x)
    frame = max(1, int(round(frame_ms * sample_rate / 1000.0)))
    hop = frame if hop_ms is None else max(1, int(round(hop_ms * sample_rate / 1000.0)))
    if mono.size < frame:
        return np.array([rms(mono)])
    n_frames = 1 + (mono.size - frame) // hop
    indices = np.arange(n_frames)[:, None] * hop + np.arange(frame)[None, :]
    windows = mono[indices]
    return np.asarray(np.sqrt(np.mean(np.square(windows), axis=1)))


def rms_envelope(x: np.ndarray, sample_rate: int, frame_ms: float) -> np.ndarray:
    """RMS of a *frame_ms* window at **every sample position** of *x*.

    ``frame_rms`` steps the window by whole frames (or by a hop), which makes
    every measurement built on it depend on where the grid happens to fall.
    Shifting the same waveform by a fraction of a frame — which alignment does
    on every trial — then changes the answer: on this corpus that moved the
    measured burst by up to 13 ms and the measured speech level by up to 1 dB,
    the second one large enough to fail the set's own level tolerance.  Both
    numbers decide what the participant is presented with, so neither may
    depend on the grid (Adım 12a).

    Computed from a cumulative sum of squares: O(n) rather than the n x frame
    matrix a sample-hop ``frame_rms`` would build, which for a 2.6 s token at a
    20 ms window would be ~400 MB.
    """
    mono = np.asarray(to_mono(x), dtype=np.float64)
    frame = max(1, int(round(frame_ms * sample_rate / 1000.0)))
    if mono.size < frame:
        return np.array([rms(mono)])
    cumulative = np.concatenate([[0.0], np.cumsum(np.square(mono))])
    sums = cumulative[frame:] - cumulative[:-frame]
    return np.asarray(np.sqrt(np.maximum(sums, 0.0) / frame))


def active_speech_level_dbfs(
    x: np.ndarray,
    sample_rate: int,
    threshold_db: float,
    *,
    frame_ms: float = 20.0,
) -> float:
    """RMS level of the speech-active part of *x*, in dBFS.

    Whole-file RMS is the wrong measure for this corpus: the tokens are
    roughly 43% silence and the silent fraction differs between them, so
    equalising whole-file RMS leaves the speech itself several dB apart
    (steps.md §C Adım 2).  A window counts as active when it is within
    *threshold_db* of the loudest window.

    The envelope is sampled every sample rather than every half frame: which
    windows fall inside the activity threshold used to depend on the grid
    phase, and on the noisier speakers that moved the measured level by up to
    1 dB — twice the tolerance the prepared set is checked against.
    """
    frames = rms_envelope(x, sample_rate, frame_ms)
    loudest = float(np.max(frames)) if frames.size else 0.0
    if loudest <= _FLOOR:
        raise DSPError("Sinyal sessiz — aktif konuşma seviyesi ölçülemez")
    active = frames[frames >= loudest * 10.0 ** (-threshold_db / 20.0)]
    return to_db(float(np.sqrt(np.mean(np.square(active)))))


def _floor_amplitude(envelope: np.ndarray, percentile: float = 10.0) -> float:
    """Noise-floor amplitude of a frame envelope.

    Frames that are *exactly* zero are excluded.  They are not a quiet part of
    the recording, they are padding this pipeline added while aligning, and
    counting them would drag the floor down to nothing — after which the first
    sample of real hiss looks like an onset.  Decoded audio is never exactly
    zero, so the distinction is unambiguous.
    """
    audible = envelope[envelope > 0.0]
    if audible.size == 0:
        raise DSPError("Sinyal tamamen sessiz — gürültü tabanı ölçülemez")
    return float(np.percentile(audible, percentile))


def noise_floor_dbfs(
    x: np.ndarray, sample_rate: int, *, frame_ms: float = 20.0, percentile: float = 10.0
) -> float:
    """Level of the quiet part of *x*, in dBFS.

    A low percentile of the frame levels rather than a fixed threshold: these
    recordings differ by several dB in how quiet their silence is, and any
    absolute floor would be wrong for one of them.
    """
    frames = frame_rms(x, sample_rate, frame_ms)
    if frames.size == 0:
        raise DSPError("Sinyal boş — gürültü tabanı ölçülemez")
    return to_db(_floor_amplitude(frames, percentile))


def normalise_to_level(
    x: np.ndarray,
    sample_rate: int,
    target_dbfs: float,
    threshold_db: float,
) -> tuple[np.ndarray, float]:
    """Scale *x* so its active-speech level is *target_dbfs*.

    Returns the scaled signal and the gain applied, in dB.
    """
    current = active_speech_level_dbfs(x, sample_rate, threshold_db)
    gain_db = target_dbfs - current
    return x * 10.0 ** (gain_db / 20.0), gain_db


# -------------------------------------------------------------------- burst


def detect_burst(
    x: np.ndarray,
    sample_rate: int,
    *,
    threshold_db: float,
    min_duration_ms: float,
    frame_ms: float = 1.0,
) -> float:
    """Time of the acoustic burst in *x*, in seconds.

    Envelope based, at *frame_ms* resolution: find the first position that
    rises *threshold_db* above the signal's own noise floor and stays there for
    *min_duration_ms*, then walk back to where it left the floor.  Walking back
    matters because the threshold crossing happens partway up the onset, and
    the alignment target is the onset itself.

    **The envelope is read at every sample** (``rms_envelope``), not once per
    frame.  With abutting frames the answer depended on where the grid fell:
    shifting the *same* waveform by a fraction of a frame moved the measured
    burst by up to 13 ms on this corpus, because a pre-burst frame sitting near
    the walk-back's floor+3 dB line flips sides and the walk-back then runs on
    to the next frame below it.  That is not a rounding detail — both the
    alignment target (a video's own burst) and the token's burst come from this
    function, so the instability went into the A/V offset of the presented
    stimulus, differently for each token.  A finer hop is not enough either:
    at 0.125 ms one token of speaker 4 still moved by 4.5 ms (Adım 12a).

    Raises:
        DSPError: when nothing in the signal stands out from its floor, which
            means the token is unusable rather than merely quiet.
    """
    envelope = rms_envelope(x, sample_rate, frame_ms)
    if envelope.size == 0:
        raise DSPError("Sinyal boş — patlama anı ölçülemez")

    loudest = float(np.max(envelope))
    if loudest <= _FLOOR:
        raise DSPError("Sinyal sessiz — patlama anı ölçülemez")

    # A percentile rather than the first N ms: it makes no assumption about
    # there being a silent lead-in.  The floor is clamped away from digital
    # zero so a perfectly silent lead-in still yields a usable threshold.
    floor = max(_floor_amplitude(envelope), loudest * 1e-5)
    threshold = floor * 10.0 ** (threshold_db / 20.0)
    if loudest < threshold * 10.0 ** (6.0 / 20.0):
        raise DSPError(
            f"Patlama tespit edilemedi: tepe {to_db(loudest):.1f} dB, taban "
            f"{to_db(floor):.1f} dB — aradaki fark {threshold_db:.0f} dB eşiğini "
            "anlamlı biçimde aşmıyor"
        )

    sustain = max(1, int(round(min_duration_ms * sample_rate / 1000.0)))
    above = envelope >= threshold
    onset = _first_sustained(above, sustain)
    if onset is None:
        raise DSPError(
            f"Patlama tespit edilemedi: eşiği {min_duration_ms:.0f} ms boyunca "
            "aşan bir bölge yok"
        )

    # Back off to the last position that was still at the floor (+3 dB), capped
    # so a noisy recording cannot drag the onset arbitrarily early.
    quiet = floor * 10.0 ** (3.0 / 20.0)
    limit = max(0, onset - int(round(0.050 * sample_rate)))
    window = envelope[limit:onset]
    at_floor = np.flatnonzero(window <= quiet)
    index = limit if at_floor.size == 0 else limit + int(at_floor[-1]) + 1
    return index / sample_rate


def _first_sustained(above: np.ndarray, sustain: int) -> int | None:
    """First index where *above* is true for *sustain* consecutive positions.

    A run-length scan rather than a Python loop over samples: at sample
    resolution the loop would run over a hundred thousand positions per token.
    """
    if above.size < sustain:
        return None
    # Cumulative count of false positions: a window is all-true when the count
    # does not increase across it.
    blocked = np.concatenate([[0], np.cumsum(~above)])
    starts = np.flatnonzero(blocked[sustain:] - blocked[:-sustain] == 0)
    return int(starts[0]) if starts.size else None


# ------------------------------------------------------------- time shifting


def shift_to(
    x: np.ndarray, sample_rate: int, current_s: float, target_s: float
) -> tuple[np.ndarray, np.ndarray]:
    """Move the event at *current_s* in *x* to *target_s*.

    Returns the shifted signal and whatever was cut from the front (empty when
    the signal was padded instead).  The caller checks the removed part is
    silence — trimming into speech would change the token, not align it.
    """
    delta = int(round((target_s - current_s) * sample_rate))
    if delta >= 0:
        return np.concatenate([np.zeros(delta, dtype=x.dtype), x]), x[:0]
    cut = -delta
    if cut >= x.size:
        raise DSPError("Hizalama sinyalin tamamını kırpardı")
    return x[cut:], x[:cut]


def fit_length(x: np.ndarray, n_samples: int) -> tuple[np.ndarray, np.ndarray]:
    """Pad or trim the end of *x* to exactly *n_samples*.

    Returns the result and whatever was cut from the end.
    """
    if x.size == n_samples:
        return x, x[:0]
    if x.size < n_samples:
        pad = np.zeros(n_samples - x.size, dtype=x.dtype)
        return np.concatenate([x, pad]), x[:0]
    return x[:n_samples], x[n_samples:]


def cosine_fade(x: np.ndarray, sample_rate: int, ramp_ms: float) -> np.ndarray:
    """Raised-cosine fade in and out, applied to a copy of *x*.

    Multi-channel input is faded per channel, so a stereo file's two ears stay
    identical in timing.
    """
    faded = np.array(x, dtype=np.float64, copy=True)
    length = int(round(ramp_ms * sample_rate / 1000.0))
    if length <= 0 or faded.shape[0] < 2 * length:
        return faded
    ramp = 0.5 * (1.0 - np.cos(np.pi * np.arange(length) / length))
    if faded.ndim > 1:
        ramp = ramp[:, None]
    faded[:length] *= ramp
    faded[-length:] *= ramp[::-1]
    return faded


# --------------------------------------------------------------------- tones


def tone(
    frequency_hz: float,
    duration_ms: float,
    sample_rate: int,
    *,
    ramp_ms: float,
    level_dbfs: float,
) -> np.ndarray:
    """A raised-cosine ramped sinusoid, normalised to *level_dbfs* RMS.

    The ramp is the point of this function.  A 50 ms tone gated instantaneously
    is not a 1 kHz tone: the discontinuity spreads energy across the whole
    spectrum, and the click it produces is audible whatever the carrier is —
    which in an oddball task means the participant could tell standard from
    target without hearing either frequency.

    The level is the RMS of the whole written tone, ramps included, because that
    is what ``verify_stimuli.py`` measures back off the disk.

    Raises:
        DSPError: on a non-positive duration, a ramp pair longer than the tone,
            or a frequency at or above the Nyquist limit.
    """
    if duration_ms <= 0:
        raise DSPError(f"Ton süresi pozitif olmalı (verilen: {duration_ms} ms)")
    if ramp_ms < 0:
        raise DSPError(f"Ton rampası negatif olamaz (verilen: {ramp_ms} ms)")
    if 2.0 * ramp_ms > duration_ms:
        raise DSPError(
            f"İki rampa ton süresinden uzun: 2 x {ramp_ms} ms > {duration_ms} ms"
        )
    if frequency_hz <= 0 or frequency_hz >= sample_rate / 2.0:
        raise DSPError(
            f"Ton frekansı 0 ile Nyquist ({sample_rate / 2:g} Hz) arasında "
            f"olmalı (verilen: {frequency_hz} Hz)"
        )

    n_samples = int(round(duration_ms * sample_rate / 1000.0))
    if n_samples < 2:
        raise DSPError(
            f"Ton {n_samples} örnek uzunluğunda — {duration_ms} ms "
            f"{sample_rate} Hz'de bir dalga biçimi taşımıyor"
        )
    t = np.arange(n_samples, dtype=np.float64) / sample_rate
    shaped = cosine_fade(np.sin(2.0 * np.pi * frequency_hz * t), sample_rate, ramp_ms)

    current = rms(shaped)
    if current <= _FLOOR:
        raise DSPError("Ton sessiz çıktı — rampa tüm sinyali yuttu")
    return np.asarray(shaped * (10.0 ** (level_dbfs / 20.0) / current))


def dominant_frequency_hz(x: np.ndarray, sample_rate: int) -> float:
    """Frequency of the strongest spectral component of *x*.

    Resolution is ``sample_rate / len(x)`` — 20 Hz for a 50 ms tone at 48 kHz —
    which is why the caller compares with a tolerance rather than for equality.
    Used to check a written tone really carries the frequency it is named after.
    """
    mono = to_mono(x)
    if mono.size < 2:
        raise DSPError("Sinyal çok kısa — baskın frekans ölçülemez")
    spectrum = np.abs(np.fft.rfft(mono * np.hanning(mono.size)))
    return float(np.argmax(spectrum)) * sample_rate / mono.size


# -------------------------------------------------------------------- noise


#: FFT length for spectral analysis.  4096 at 48 kHz is 11.7 Hz per bin, which
#: is what the lowest third-octave band being compared (125 Hz, 111–140 Hz)
#: needs to contain any bins at all — at 1024 it contains none and the band
#: reads as silence.
LTAS_N_FFT = 4096


def ltas(
    x: np.ndarray,
    sample_rate: int,
    *,
    n_fft: int = LTAS_N_FFT,
    threshold_db: float | None = None,
) -> np.ndarray:
    """Long-term average power spectrum of *x* over ``n_fft//2 + 1`` bins.

    With *threshold_db*, only speech-active frames contribute — silent frames
    would otherwise pull the spectrum towards the recording's noise floor.
    """
    mono = to_mono(x)
    if mono.size < n_fft:
        mono = np.concatenate([mono, np.zeros(n_fft - mono.size)])
    hop = n_fft // 2
    n_frames = 1 + (mono.size - n_fft) // hop
    indices = np.arange(n_frames)[:, None] * hop + np.arange(n_fft)[None, :]
    frames = mono[indices] * np.hanning(n_fft)[None, :]
    power = np.abs(np.fft.rfft(frames, axis=1)) ** 2

    if threshold_db is not None and n_frames > 1:
        energy = power.sum(axis=1)
        loudest = float(np.max(energy))
        if loudest > 0:
            keep = energy >= loudest * 10.0 ** (-threshold_db / 10.0)
            if keep.any():
                power = power[keep]
    return np.asarray(power.mean(axis=0), dtype=np.float64)


def speech_shaped_noise(
    target_ltas: np.ndarray,
    sample_rate: int,
    n_samples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Gaussian noise shaped to *target_ltas*, normalised to unit RMS.

    Shaping in the frequency domain rather than with a filter design keeps the
    match to the corpus spectrum exact by construction; ``verify_stimuli``
    measures it back anyway.  The analysis length is read off *target_ltas*
    rather than passed in, so it cannot disagree with how the target was made.
    """
    white = rng.standard_normal(n_samples)
    spectrum = np.fft.rfft(white)
    source_freqs = np.fft.rfftfreq(2 * (target_ltas.size - 1), 1.0 / sample_rate)
    target_freqs = np.fft.rfftfreq(n_samples, 1.0 / sample_rate)
    magnitude = np.sqrt(np.interp(target_freqs, source_freqs, target_ltas))
    shaped = np.fft.irfft(spectrum * magnitude, n=n_samples)
    level = rms(shaped)
    if level <= _FLOOR:
        raise DSPError("Konuşma şekilli gürültü üretilemedi (sonuç sessiz)")
    return shaped / level


def third_octave_centres(low_hz: float, high_hz: float) -> np.ndarray:
    """ISO third-octave centre frequencies within [low, high]."""
    exponents = np.arange(-20, 14)  # 10 Hz … 20 kHz
    centres = 1000.0 * 2.0 ** (exponents / 3.0)
    return centres[(centres >= low_hz) & (centres <= high_hz)]


def third_octave_levels(
    power: np.ndarray, sample_rate: int, centres: np.ndarray
) -> np.ndarray:
    """Band levels in dB for the power spectrum *power*.

    A band containing no FFT bin yields NaN rather than a floor value: it is
    unmeasured, not silent, and letting it read as silence would put a 20 dB
    artefact into every comparison.
    """
    freqs = np.fft.rfftfreq(2 * (power.size - 1), 1.0 / sample_rate)
    levels = []
    for centre in centres:
        lower, upper = centre / 2.0 ** (1.0 / 6.0), centre * 2.0 ** (1.0 / 6.0)
        band = power[(freqs >= lower) & (freqs < upper)]
        levels.append(
            10.0 * np.log10(max(float(band.sum()), _FLOOR)) if band.size else np.nan
        )
    return np.asarray(levels, dtype=np.float64)


def ltas_deviation_db(
    power_a: np.ndarray,
    power_b: np.ndarray,
    sample_rate: int,
    *,
    low_hz: float = 100.0,
    high_hz: float = 8000.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Per-band shape difference between two spectra, in dB.

    Both are first referred to their own mean band level, so this compares
    spectral *shape* and not overall level — the noise is scaled to whatever
    the SNR asks for later, so its absolute level here is meaningless.
    """
    centres = third_octave_centres(low_hz, high_hz)
    levels_a = third_octave_levels(power_a, sample_rate, centres)
    levels_b = third_octave_levels(power_b, sample_rate, centres)
    measured = np.isfinite(levels_a) & np.isfinite(levels_b)
    if not measured.any():
        raise DSPError(
            f"{low_hz:.0f}–{high_hz:.0f} Hz aralığında ölçülebilir 1/3 oktav "
            "bandı yok — FFT çözünürlüğü yetersiz"
        )
    levels_a, levels_b = levels_a[measured], levels_b[measured]
    return (
        centres[measured],
        (levels_a - levels_a.mean()) - (levels_b - levels_b.mean()),
    )


def mix_at_snr(
    speech: np.ndarray,
    noise: np.ndarray,
    sample_rate: int,
    snr_db: float,
    threshold_db: float,
) -> tuple[np.ndarray, float]:
    """Add *noise* to *speech* at *snr_db*; return the mix and the realised SNR.

    SNR is defined against the *active* speech level, not the whole-file RMS —
    the definition the Adım 0 code got wrong, which made the effective SNR
    depend on how much silence a token happened to carry.
    """
    if speech.size != noise.size:
        raise DSPError(
            f"Konuşma ({speech.size}) ve gürültü ({noise.size}) uzunlukları farklı"
        )
    speech_level = active_speech_level_dbfs(speech, sample_rate, threshold_db)
    noise_level = to_db(rms(noise))
    scaled = noise * 10.0 ** ((speech_level - snr_db - noise_level) / 20.0)
    return speech + scaled, speech_level - to_db(rms(scaled))


def bandlimited_noise(
    n_samples: int,
    sample_rate: int,
    low_hz: float,
    high_hz: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Zero-phase band-limited Gaussian noise, normalised to unit RMS."""
    nyquist = sample_rate / 2.0
    if not 0 < low_hz < high_hz < nyquist:
        raise DSPError(
            f"Geçersiz bant: {low_hz}–{high_hz} Hz (Nyquist {nyquist:.0f} Hz)"
        )
    sos = signal.butter(
        4, [low_hz / nyquist, high_hz / nyquist], btype="bandpass", output="sos"
    )
    filtered = signal.sosfiltfilt(sos, rng.standard_normal(n_samples))
    level = rms(filtered)
    if level <= _FLOOR:
        raise DSPError("Bant sınırlı gürültü üretilemedi (sonuç sessiz)")
    return np.asarray(filtered / level, dtype=np.float64)


# ---------------------------------------------------------------------- GIN


def plan_gaps(
    rng: np.random.Generator,
    *,
    gap_durations_ms: list[float],
    n_segments: int,
    max_gaps_per_segment: int,
    segment_duration_s: float,
    min_separation_s: float,
) -> list[list[tuple[float, float]]]:
    """Distribute gaps over segments; return (onset_s, duration_ms) per segment.

    Segments get 0…*max_gaps_per_segment* gaps, drawn without replacement from
    the full slot pool — standard GIN includes segments with no gap at all, and
    a fixed number per segment would make the gap count predictable.

    Within a segment the constraint is that gaps are at least
    *min_separation_s* apart and that far from either edge; the free time left
    over is split randomly between the intervals, which keeps positions
    unpredictable without ever violating the spacing.
    """
    if not gap_durations_ms:
        return [[] for _ in range(n_segments)]
    capacity = n_segments * max_gaps_per_segment
    if len(gap_durations_ms) > capacity:
        raise DSPError(
            f"{len(gap_durations_ms)} boşluk {n_segments} segmente sığmıyor "
            f"(kapasite {capacity})"
        )

    durations = list(gap_durations_ms)
    rng.shuffle(durations)
    slots = rng.choice(capacity, size=len(durations), replace=False)
    counts = np.bincount(slots // max_gaps_per_segment, minlength=n_segments)

    plan: list[list[tuple[float, float]]] = []
    cursor = 0
    for count in counts:
        chosen = durations[cursor : cursor + int(count)]
        cursor += int(count)
        plan.append(_place_in_segment(rng, chosen, segment_duration_s, min_separation_s))
    return plan


def _place_in_segment(
    rng: np.random.Generator,
    durations_ms: list[float],
    segment_duration_s: float,
    min_separation_s: float,
) -> list[tuple[float, float]]:
    if not durations_ms:
        return []
    count = len(durations_ms)
    total_gap_s = sum(durations_ms) / 1000.0
    free = segment_duration_s - total_gap_s - (count + 1) * min_separation_s
    if free < 0:
        raise DSPError(
            f"{count} boşluk ({total_gap_s * 1000:.0f} ms) + ayrım süresi "
            f"{segment_duration_s} s'lik segmente sığmıyor"
        )
    spacing = rng.dirichlet(np.ones(count + 1)) * free

    placed: list[tuple[float, float]] = []
    position = 0.0
    for index, duration in enumerate(durations_ms):
        position += min_separation_s + float(spacing[index])
        placed.append((position, duration))
        position += duration / 1000.0
    return placed


def apply_gaps(
    noise: np.ndarray,
    sample_rate: int,
    gaps: list[tuple[float, float]],
    ramp_ms: float,
) -> np.ndarray:
    """Silence *gaps* in *noise* with raised-cosine edges.

    The ramp is centred on each nominal edge — half of it inside the gap, half
    outside — so the half-amplitude points sit exactly at the nominal gap
    boundaries and the gap duration the participant is scored on is the one the
    design asked for.  An instantaneous cut would add a click whose spectral
    splatter is detectable independently of the gap.
    """
    gain = np.ones(noise.size, dtype=np.float64)
    half = max(1, int(round(ramp_ms * sample_rate / 2000.0)))
    ramp = 0.5 * (1.0 - np.cos(np.pi * np.arange(2 * half) / (2 * half)))

    for onset_s, duration_ms in gaps:
        start = int(round(onset_s * sample_rate))
        end = int(round((onset_s + duration_ms / 1000.0) * sample_rate))
        if start - half < 0 or end + half > noise.size:
            raise DSPError(
                f"Boşluk ({onset_s:.3f} s, {duration_ms:.0f} ms) rampasıyla "
                "birlikte segmentin dışına taşıyor"
            )
        gain[start - half : start + half] = ramp[::-1]
        gain[start + half : end - half] = 0.0
        gain[end - half : end + half] = ramp
    return noise * gain
