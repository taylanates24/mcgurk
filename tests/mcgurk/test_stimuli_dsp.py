"""Measurement functions, checked against signals with known answers.

These are the functions that decide what the experiment presents: where the
burst is (and therefore what "SOA = 0" means), what "equal level" means, and
what SNR a noisy trial actually has.  Checking them against the corpus would
only say the corpus is self-consistent, so everything here is synthetic.
"""

from __future__ import annotations

import numpy as np
import pytest

from mcgurk.stimuli import dsp

SR = 48000


def _quiet(n: int, rng: np.random.Generator, level: float = 1e-3) -> np.ndarray:
    """Recording-noise-like floor — never digital silence."""
    return rng.standard_normal(n) * level


def _token(rng: np.random.Generator, burst_s: float, total_s: float = 2.0) -> np.ndarray:
    """Silence, then an abrupt 300 ms burst, then silence."""
    signal = _quiet(int(total_s * SR), rng)
    start = int(burst_s * SR)
    length = int(0.3 * SR)
    time = np.arange(length) / SR
    signal[start : start + length] += 0.3 * np.sin(2 * np.pi * 500 * time)
    return signal


# ------------------------------------------------------------------- levels


def test_active_level_ignores_the_silent_part() -> None:
    rng = np.random.default_rng(0)
    # One second of tone in four seconds of file: whole-file RMS is 6 dB below
    # the speech level, which is exactly the error this replaces.
    signal = np.concatenate(
        [0.5 * np.sin(2 * np.pi * 500 * np.arange(SR) / SR), _quiet(3 * SR, rng)]
    )
    active = dsp.active_speech_level_dbfs(signal, SR, 30.0)
    whole_file = dsp.to_db(dsp.rms(signal))

    assert active == pytest.approx(dsp.to_db(0.5 / np.sqrt(2)), abs=0.3)
    assert active - whole_file > 5.0


def test_active_level_is_unchanged_by_added_silence() -> None:
    """Two takes with different amounts of lead-in must measure the same."""
    rng = np.random.default_rng(1)
    speech = 0.4 * np.sin(2 * np.pi * 400 * np.arange(SR) / SR)
    short = np.concatenate([_quiet(SR // 10, rng), speech])
    long = np.concatenate([_quiet(2 * SR, rng), speech])

    assert dsp.active_speech_level_dbfs(short, SR, 30.0) == pytest.approx(
        dsp.active_speech_level_dbfs(long, SR, 30.0), abs=0.2
    )


def test_normalise_hits_the_target_level() -> None:
    rng = np.random.default_rng(2)
    scaled, gain = dsp.normalise_to_level(_token(rng, 0.5), SR, -23.0, 30.0)
    assert dsp.active_speech_level_dbfs(scaled, SR, 30.0) == pytest.approx(-23.0, abs=0.01)
    assert gain != 0.0


def test_silent_signal_has_no_measurable_level() -> None:
    with pytest.raises(dsp.DSPError):
        dsp.active_speech_level_dbfs(np.zeros(SR), SR, 30.0)


# -------------------------------------------------------------------- burst


@pytest.mark.parametrize("burst_s", [0.2, 0.5, 1.1])
def test_burst_is_found_within_a_millisecond(burst_s: float) -> None:
    rng = np.random.default_rng(3)
    measured = dsp.detect_burst(
        _token(rng, burst_s), SR, threshold_db=12.0, min_duration_ms=10.0
    )
    assert measured == pytest.approx(burst_s, abs=0.002)


def test_leading_digital_silence_does_not_move_the_burst() -> None:
    """Alignment pads with zeros, and the result gets measured again.

    A floor estimated over the padding would sit at nothing, and the first
    sample of real hiss would read as the onset — 800 ms early.
    """
    rng = np.random.default_rng(4)
    token = _token(rng, 0.5)
    padded = np.concatenate([np.zeros(int(0.3 * SR)), token])
    measured = dsp.detect_burst(
        padded, SR, threshold_db=12.0, min_duration_ms=10.0
    )
    assert measured == pytest.approx(0.8, abs=0.002)


def _token_with_a_gradual_lead_in(
    rng: np.random.Generator, burst_s: float, total_s: float = 2.0
) -> np.ndarray:
    """A token whose level creeps up before the burst, as real speech does.

    Breath and lip noise put the 200 ms before the burst near the walk-back's
    floor+3 dB line, which is where the frame grid used to decide the answer.
    An abruptly starting synthetic token cannot show that.
    """
    signal = _quiet(int(total_s * SR), rng)
    start = int(burst_s * SR)
    lead = int(0.2 * SR)
    ramp = np.linspace(1.0, 4.0, lead)
    signal[start - lead : start] *= ramp
    length = int(0.3 * SR)
    time = np.arange(length) / SR
    signal[start : start + length] += 0.3 * np.sin(2 * np.pi * 500 * time)
    return signal


def test_the_burst_moves_with_the_signal_and_nothing_else() -> None:
    """Shifting the same waveform must move the reading by exactly the shift.

    It did not: with abutting frames the reading depended on where the frame
    grid fell, by up to 13 ms on the real corpus (Adım 12a).  Both the
    alignment target and the token's own burst come from this function, so that
    instability landed in the A/V offset the participant is presented with —
    differently for each token.

    The shifts step by **one sample**, covering every phase of the window.  A
    coarser step is how this was nearly missed: stepping by the envelope's own
    hop only ever samples one phase, and the measurement looks perfect.
    """
    rng = np.random.default_rng(7)
    token = _token_with_a_gradual_lead_in(rng, 1.0)

    readings = []
    for shift in range(48):  # every phase of the 1 ms window
        padded = np.concatenate([np.zeros(shift), token])
        measured = dsp.detect_burst(
            padded, SR, threshold_db=12.0, min_duration_ms=10.0
        )
        readings.append(measured - shift / SR)

    assert max(readings) - min(readings) == pytest.approx(0.0, abs=1e-9)


def test_the_active_level_does_not_depend_on_the_window_phase() -> None:
    """Same waveform, same level — whatever the alignment shift happened to be.

    Aligning a token trims a few samples off the front, which used to move the
    measured level by up to 1 dB on the noisier speakers: enough to fail the
    prepared set's own 0.5 dB tolerance while the audio was in fact identical.
    """
    rng = np.random.default_rng(8)
    token = _token_with_a_gradual_lead_in(rng, 1.0)

    levels = [
        dsp.active_speech_level_dbfs(token[shift:], SR, 30.0)
        for shift in range(48)
    ]
    assert max(levels) - min(levels) == pytest.approx(0.0, abs=0.01)


def test_a_signal_with_no_onset_is_an_error() -> None:
    """Uniform noise has no burst; guessing one would misalign every trial."""
    rng = np.random.default_rng(5)
    with pytest.raises(dsp.DSPError, match="Patlama tespit edilemedi"):
        dsp.detect_burst(
            rng.standard_normal(2 * SR) * 0.1, SR,
            threshold_db=12.0, min_duration_ms=10.0,
        )


def test_a_click_shorter_than_the_sustain_is_not_a_burst() -> None:
    rng = np.random.default_rng(6)
    signal = _quiet(SR, rng)
    signal[SR // 2 : SR // 2 + 20] += 0.5  # 0.4 ms spike
    with pytest.raises(dsp.DSPError):
        dsp.detect_burst(signal, SR, threshold_db=12.0, min_duration_ms=10.0)


def test_noise_floor_ignores_padding() -> None:
    rng = np.random.default_rng(7)
    token = _quiet(SR, rng, level=1e-2)
    padded = np.concatenate([np.zeros(SR), token])
    assert dsp.noise_floor_dbfs(padded, SR) == pytest.approx(
        dsp.noise_floor_dbfs(token, SR), abs=1.0
    )


# ------------------------------------------------------------- time shifting


def test_shift_moves_the_event_and_reports_what_it_cut() -> None:
    rng = np.random.default_rng(8)
    token = _token(rng, 0.5)

    later, cut = dsp.shift_to(token, SR, 0.5, 0.7)
    assert cut.size == 0
    assert dsp.detect_burst(
        later, SR, threshold_db=12.0, min_duration_ms=10.0
    ) == pytest.approx(0.7, abs=0.002)

    earlier, cut = dsp.shift_to(token, SR, 0.5, 0.3)
    assert cut.size == int(0.2 * SR)
    assert dsp.detect_burst(
        earlier, SR, threshold_db=12.0, min_duration_ms=10.0
    ) == pytest.approx(0.3, abs=0.002)


def test_fit_length_pads_and_trims() -> None:
    signal = np.ones(100)
    padded, cut = dsp.fit_length(signal, 150)
    assert padded.size == 150 and cut.size == 0 and padded[-1] == 0.0
    trimmed, cut = dsp.fit_length(signal, 60)
    assert trimmed.size == 60 and cut.size == 40


def test_fade_starts_and_ends_at_zero() -> None:
    faded = dsp.cosine_fade(np.ones(SR), SR, 50.0)
    assert faded[0] == pytest.approx(0.0, abs=1e-12)
    assert faded[-1] == pytest.approx(0.0, abs=1e-12)
    assert faded[SR // 2] == pytest.approx(1.0)


def test_fade_treats_a_stereo_file_as_two_channels() -> None:
    """Dichotic files are stereo; fading them per channel keeps the ears aligned."""
    stereo = np.ones((SR, 2))
    faded = dsp.cosine_fade(stereo, SR, 50.0)
    assert faded.shape == stereo.shape
    assert faded[0].tolist() == pytest.approx([0.0, 0.0], abs=1e-12)
    assert faded[-1].tolist() == pytest.approx([0.0, 0.0], abs=1e-12)
    assert np.array_equal(faded[:, 0], faded[:, 1])


# -------------------------------------------------------------------- noise


@pytest.mark.parametrize("snr_db", [0.0, 5.0, 10.0])
def test_mixture_has_the_requested_snr(snr_db: float) -> None:
    rng = np.random.default_rng(9)
    speech = _token(rng, 0.5)
    noise = rng.standard_normal(speech.size)

    mixed, reported = dsp.mix_at_snr(speech, noise, SR, snr_db, 30.0)
    # Measured independently of what mix_at_snr says: the noise it added is
    # whatever the mixture has beyond the speech.
    added = mixed - speech
    realised = dsp.active_speech_level_dbfs(speech, SR, 30.0) - dsp.to_db(dsp.rms(added))

    assert reported == pytest.approx(snr_db, abs=0.01)
    assert realised == pytest.approx(snr_db, abs=0.01)


def test_snr_does_not_depend_on_how_much_silence_the_token_carries() -> None:
    """The Adım 0 bug: whole-file RMS made the effective SNR token-dependent."""
    rng = np.random.default_rng(10)
    speech = _token(rng, 0.5, total_s=2.0)
    padded = np.concatenate([speech, _quiet(2 * SR, rng)])
    noise = rng.standard_normal(speech.size)

    _, short = dsp.mix_at_snr(speech, noise, SR, 5.0, 30.0)
    _, long = dsp.mix_at_snr(
        padded, rng.standard_normal(padded.size), SR, 5.0, 30.0
    )
    assert short == pytest.approx(long, abs=0.05)


def _tilted_spectrum(rng: np.random.Generator, n: int) -> np.ndarray:
    """A speech-like target: energy in every band, ~20 dB of tilt across them."""
    return (
        1.0 * dsp.bandlimited_noise(n, SR, 110.0, 800.0, rng)
        + 0.3 * dsp.bandlimited_noise(n, SR, 800.0, 3000.0, rng)
        + 0.1 * dsp.bandlimited_noise(n, SR, 3000.0, 9000.0, rng)
    )


def test_shaped_noise_follows_the_target_spectrum() -> None:
    rng = np.random.default_rng(11)
    target = dsp.ltas(_tilted_spectrum(rng, 4 * SR), SR)
    noise = dsp.speech_shaped_noise(target, SR, 5 * SR, rng)

    _, deviations = dsp.ltas_deviation_db(dsp.ltas(noise, SR), target, SR)
    assert float(np.max(np.abs(deviations))) < 1.5
    assert dsp.rms(noise) == pytest.approx(1.0, abs=1e-6)


def test_white_noise_does_not_pass_as_speech_shaped() -> None:
    """Guard the guard: the comparison has to be able to fail."""
    rng = np.random.default_rng(12)
    target = dsp.ltas(_tilted_spectrum(rng, 4 * SR), SR)
    white = rng.standard_normal(5 * SR)

    _, deviations = dsp.ltas_deviation_db(dsp.ltas(white, SR), target, SR)
    assert float(np.max(np.abs(deviations))) > 5.0


def test_ltas_comparison_is_about_shape_not_level() -> None:
    rng = np.random.default_rng(13)
    signal = dsp.bandlimited_noise(2 * SR, SR, 200.0, 4000.0, rng)
    quiet = dsp.ltas(signal * 0.01, SR)
    loud = dsp.ltas(signal * 1.0, SR)

    _, deviations = dsp.ltas_deviation_db(quiet, loud, SR)
    assert float(np.max(np.abs(deviations))) < 1e-6


def test_bandlimited_noise_keeps_its_energy_in_the_band() -> None:
    rng = np.random.default_rng(14)
    noise = dsp.bandlimited_noise(4 * SR, SR, 500.0, 2000.0, rng)
    power = dsp.ltas(noise, SR)
    freqs = np.fft.rfftfreq(2 * (power.size - 1), 1.0 / SR)

    inside = power[(freqs >= 600) & (freqs <= 1800)].mean()
    outside = power[(freqs > 4000) & (freqs < 8000)].mean()
    assert dsp.to_db(np.sqrt(inside / outside)) > 30.0


def test_bandlimited_noise_rejects_an_impossible_band() -> None:
    rng = np.random.default_rng(15)
    with pytest.raises(dsp.DSPError):
        dsp.bandlimited_noise(SR, SR, 8000.0, 100.0, rng)
