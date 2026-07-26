"""End-to-end preparation and verification on a synthetic corpus.

A real ``assets/`` tree is not assumed: the recordings are not in the
repository and CI has none.  Three tiny recordings are built with ffmpeg, each
with its burst at a different, known instant, which is also the only way to
check that alignment actually moved the audio — with the real corpus the
answer would be whatever the pipeline produced.

Marked ``ffmpeg``: skipped where the binary is missing.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml

from mcgurk.config.schema import ExperimentConfig
from mcgurk.stimuli import StimulusError, dsp, ffmpeg, manifest, wavfile
from mcgurk.stimuli.prepare import prepare
from mcgurk.stimuli.verify import verify

pytestmark = pytest.mark.ffmpeg

SR = 48000
#: Burst instants of the synthetic tokens, spread the way the real corpus is.
BURSTS = {"ba": 0.30, "da": 0.36, "ga": 0.33}
TOKEN_DURATION_S = 1.2
#: More than one, so "the instances differ" is something a test can see.
NOISE_INSTANCES = 2


def _token_audio(name: str, rng: np.random.Generator) -> np.ndarray:
    """Quiet lead-in, an abrupt broadband onset, a decaying token, quiet tail.

    The token is band-shaped noise rather than a tone: the speech-shaped noise
    is derived from this corpus's own spectrum, so a corpus of discrete
    spectral lines would produce narrowband noise whose envelope swings by
    several dB and whose third-octave levels are dominated by which bin a
    harmonic landed in.  Every level measurement in these tests would then be
    a coin toss for reasons that have nothing to do with the pipeline.
    """
    samples = rng.standard_normal(int(TOKEN_DURATION_S * SR)) * 1e-3
    start = int(BURSTS[name] * SR)
    length = int(0.25 * SR)
    time = np.arange(length) / SR

    token = (
        1.00 * dsp.bandlimited_noise(length, SR, 200.0, 900.0, rng)
        + 0.40 * dsp.bandlimited_noise(length, SR, 900.0, 2500.0, rng)
        + 0.15 * dsp.bandlimited_noise(length, SR, 2500.0, 6000.0, rng)
    ) * np.exp(-time * 3)

    samples[start : start + length] += token
    # Scaled rather than left as-is so a stray random draw cannot clip the
    # 16-bit source file; the pipeline normalises the level anyway.
    return samples * (0.5 / float(np.max(np.abs(samples))))


def _write_corpus(directory: Path, *, silent_video: bool = False) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(0)
    for name in BURSTS:
        audio = directory / f"{name}.wav"
        wavfile.write(audio, _token_audio(name, rng), SR, bit_depth=16)
        args = [
            "-y",
            "-f", "lavfi",
            "-i", f"testsrc=size=64x64:rate=30000/1001:duration={TOKEN_DURATION_S}",
        ]
        if not silent_video:
            args += ["-i", str(audio), "-c:a", "aac", "-shortest"]
        args += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
        args.append(str(directory / f"Vis-{name}_Aud-{name}.mp4"))
        ffmpeg.run(*args)
        audio.unlink()


def _config(config_dict: dict[str, Any], tmp_path: Path) -> ExperimentConfig:
    """The shipped design, shrunk to something that builds in seconds."""
    data = yaml.safe_load(yaml.safe_dump(config_dict))
    data["paths"]["stimuli"] = "stimuli"
    data["stimulus_prep"]["speakers"] = [{"id": 1, "source": "corpus"}]
    data["stimulus_prep"]["noise"]["instances"] = NOISE_INSTANCES
    # The synthetic tokens burst at ~300 ms, so the shipped 250 ms noise fade
    # would (correctly) be refused for reaching into the token.
    data["stimulus_prep"]["noise"]["ramp_ms"] = 100.0

    for module in ("mcgurk", "avsr", "tbw", "dichotic"):
        data["modules"][module]["speaker_id"] = 1
    data["speaker_selection"]["fixed_id"] = 1
    data["modules"]["gin"].update(
        gap_durations_ms=[5.0, 10.0],
        reps_per_gap=2,
        threshold_criterion="2_of_2",
        n_segments=3,
        segment_duration_s=2.0,
        max_gaps_per_segment=2,
        min_gap_separation_s=0.4,
    )
    return ExperimentConfig.model_validate(data)


@pytest.fixture
def prepared(config_dict: dict[str, Any], tmp_path: Path):
    _write_corpus(tmp_path / "corpus")
    config = _config(config_dict, tmp_path)
    return config, prepare(config, tmp_path), tmp_path


# ------------------------------------------------------------------- outputs


def test_the_whole_set_is_produced(prepared) -> None:
    config, result, _ = prepared
    assert len(result.videos) == 3            # one per visual token
    assert len(result.tokens) == 9            # every visual × audio pairing
    assert len(result.noisy_tokens) == 9 * NOISE_INSTANCES   # × one SNR
    assert len(result.dichotic) == len(config.modules.dichotic.pairs)
    assert len(result.gin_segments) == 3
    assert result.noise is not None


def test_the_video_is_silent_and_constant_rate(prepared) -> None:
    _, result, root = prepared
    for entry in result.videos:
        path = entry.file.resolve(root / "stimuli")
        assert not ffmpeg.has_audio_stream(path)
        assert entry.fps == 30.0
        assert ffmpeg.count_frames(path) == entry.frame_count


def test_the_frame_count_survives_the_rate_conversion(prepared) -> None:
    """29.97 → 30 may only relabel timestamps at this clip length."""
    _, result, root = prepared
    for entry in result.videos:
        source = root / entry.source.path if not Path(entry.source.path).is_absolute() \
            else Path(entry.source.path)
        assert ffmpeg.count_frames(source) == entry.frame_count


def test_every_audio_file_is_aligned_to_its_video(prepared) -> None:
    config, result, root = prepared
    tolerance_s = config.stimulus_prep.burst.alignment_tolerance_ms / 1000.0
    for entry in result.tokens:
        video = result.video(entry.speaker_id, entry.visual_token)
        samples, rate = wavfile.read(entry.file.resolve(root / "stimuli"))
        measured = dsp.detect_burst(
            samples, rate,
            threshold_db=config.stimulus_prep.burst.threshold_db,
            min_duration_ms=config.stimulus_prep.burst.min_duration_ms,
        )
        assert measured == pytest.approx(video.burst_time_s, abs=tolerance_s)


def test_alignment_actually_moves_the_audio(prepared) -> None:
    """Guard the guard: leaving the audio alone would also pass the check above.

    One audio token mounted on two videos has to end up as far apart as those
    videos' own bursts are — and those are ~60 ms apart by construction, so a
    pipeline that did nothing would fail this.
    """
    _, result, _ = prepared
    videos = result.video(1, "da").burst_time_s - result.video(1, "ba").burst_time_s
    audio = (
        result.token(1, "da", "ba").burst_time_s
        - result.token(1, "ba", "ba").burst_time_s
    )
    assert audio == pytest.approx(videos, abs=0.003)
    # Measured rather than nominal: an AAC round trip moves an onset by a few
    # milliseconds, which is why the pipeline re-measures instead of trusting
    # the numbers the corpus was built with.
    assert videos == pytest.approx(BURSTS["da"] - BURSTS["ba"], abs=0.01)


def test_every_token_ends_up_at_the_same_level(prepared) -> None:
    """Equality between tokens is the point: level must not be a confound."""
    config, result, _ = prepared
    levels = [entry.active_level_dbfs for entry in result.tokens]
    assert max(levels) - min(levels) < 0.05
    assert levels[0] == pytest.approx(
        config.stimulus_prep.audio.target_level_dbfs, abs=0.5
    )


def test_the_noisy_variants_have_the_configured_snr(prepared) -> None:
    config, result, root = prepared
    threshold = config.stimulus_prep.audio.active_speech_threshold_db
    for entry in result.noisy_tokens:
        clean, _ = wavfile.read(
            result.token(
                entry.speaker_id, entry.visual_token, entry.audio_token
            ).file.resolve(root / "stimuli")
        )
        mixed, rate = wavfile.read(entry.file.resolve(root / "stimuli"))
        realised = dsp.active_speech_level_dbfs(clean, rate, threshold) - dsp.to_db(
            dsp.rms(mixed - clean)
        )
        assert realised == pytest.approx(entry.snr_db, abs=0.5)
        assert entry.peak_dbfs < -1.0


def test_the_dichotic_ears_carry_different_tokens_at_one_onset(prepared) -> None:
    _, result, root = prepared
    entry = result.dichotic[0]
    stereo, rate = wavfile.read(entry.file.resolve(root / "stimuli"))

    assert stereo.ndim == 2 and stereo.shape[1] == 2
    left = dsp.detect_burst(stereo[:, 0], rate, threshold_db=12.0, min_duration_ms=10.0)
    right = dsp.detect_burst(stereo[:, 1], rate, threshold_db=12.0, min_duration_ms=10.0)
    assert left == pytest.approx(right, abs=0.005)
    assert not np.array_equal(stereo[:, 0], stereo[:, 1])


def test_the_gin_gaps_are_where_the_manifest_says(prepared) -> None:
    _, result, root = prepared
    for entry in result.gin_segments:
        samples, rate = wavfile.read(entry.file.resolve(root / "stimuli"))
        for onset, duration_ms in zip(
            entry.gap_onsets_s, entry.gap_durations_ms, strict=True
        ):
            middle = int((onset + duration_ms / 2000.0) * rate)
            assert abs(samples[middle]) < 1e-6


def test_the_gin_segment_fades_in_over_its_own_ramp(prepared) -> None:
    """The segment edge uses ``gin.segment_ramp_ms``, not the noise ramp.

    They used to share one 50 ms value, which is right for noise mixed into a
    2.6 s speech token and abrupt for a six-second noise burst.
    """
    config, result, root = prepared
    ramp_s = config.stimulus_prep.gin.segment_ramp_ms / 1000.0
    samples, rate = wavfile.read(result.gin_segments[0].file.resolve(root / "stimuli"))

    steady = dsp.rms(samples[int(ramp_s * rate) : int(2 * ramp_s * rate)])
    quarter = dsp.rms(samples[: int(ramp_s / 4 * rate)])
    middle = dsp.rms(
        samples[int(0.45 * ramp_s * rate) : int(0.55 * ramp_s * rate)]
    )

    assert samples[0] == pytest.approx(0.0, abs=1e-6)
    assert dsp.to_db(quarter / steady) < -10.0
    # Half way through a raised-cosine fade is the -6 dB point.
    assert dsp.to_db(middle / steady) == pytest.approx(-6.0, abs=2.0)


def test_the_noise_fades_in_before_the_token(prepared) -> None:
    """The fade has to be over before the speech, or the SNR is not the one asked for."""
    config, result, root = prepared
    stimuli = root / "stimuli"
    ramp_s = config.stimulus_prep.noise.ramp_ms / 1000.0
    entry = result.noisy_tokens[0]
    clean, rate = wavfile.read(
        result.token(
            entry.speaker_id, entry.visual_token, entry.audio_token
        ).file.resolve(stimuli)
    )
    mixed, _ = wavfile.read(entry.file.resolve(stimuli))
    noise = mixed - clean

    steady = dsp.rms(noise[int(ramp_s * rate) : int(2 * ramp_s * rate)])
    quarter = dsp.rms(noise[: int(ramp_s / 4 * rate)])
    assert dsp.to_db(quarter / steady) < -10.0
    assert dsp.to_db(dsp.rms(noise[int(0.45 * ramp_s * rate):
                                   int(0.55 * ramp_s * rate)]) / steady) == pytest.approx(
        -6.0, abs=2.0
    )


def test_every_audio_file_starts_and_ends_in_silence(prepared) -> None:
    """Otherwise the trial onset clicks on some trials and not others.

    Alignment trims up to ~250 ms off the front of a token, leaving that file
    beginning in the middle of the recording's hiss while its neighbours begin
    in digital silence.
    """
    _, result, root = prepared
    stimuli = root / "stimuli"
    files = [entry.file for entry in result.tokens]
    files += [entry.file for entry in result.dichotic]
    files += [entry.file for entry in result.noisy_tokens]
    files += [entry.file for entry in result.gin_segments]
    assert result.noise is not None
    files.append(result.noise.file)

    for media in files:
        mono = dsp.to_mono(wavfile.read(media.resolve(stimuli))[0])
        assert abs(float(mono[0])) < 1e-4, media.path
        assert abs(float(mono[-1])) < 1e-4, media.path


def test_an_edge_ramp_that_could_touch_the_speech_is_refused(
    config_dict: dict[str, Any], tmp_path: Path
) -> None:
    _write_corpus(tmp_path / "corpus")
    config = _config(config_dict, tmp_path)
    config.stimulus_prep.audio.edge_ramp_ms = 400.0   # tokens burst at ~300 ms
    with pytest.raises(StimulusError, match="edge_ramp_ms"):
        prepare(config, tmp_path)


def test_a_noise_ramp_reaching_into_the_token_is_refused(
    config_dict: dict[str, Any], tmp_path: Path
) -> None:
    """A fade still rising when the burst arrives raises the effective SNR."""
    _write_corpus(tmp_path / "corpus")
    config = _config(config_dict, tmp_path)
    config.stimulus_prep.noise.ramp_ms = 400.0   # tokens burst at ~300 ms
    with pytest.raises(StimulusError, match="gürültü rampası"):
        prepare(config, tmp_path)


def test_the_noise_instances_are_different_waveforms(prepared) -> None:
    """They are meant to sound identical — stationary noise does.

    What must not repeat is the waveform: the same one across the repetitions
    of a cell could be learned, and "listening in the dips" of a known noise
    is not the ability being measured.
    """
    config, result, root = prepared
    stimuli = root / "stimuli"
    clean, _ = wavfile.read(result.token(1, "ba", "ba").file.resolve(stimuli))
    noises = []
    for entry in result.noisy(1, "ba", "ba", config.required_snrs()[0]):
        mixed, _ = wavfile.read(entry.file.resolve(stimuli))
        noises.append(mixed - clean)

    for first in range(len(noises)):
        for second in range(first + 1, len(noises)):
            correlation = float(np.corrcoef(noises[first], noises[second])[0, 1])
            assert abs(correlation) < 0.2
            # …while carrying the same level, as a stationary process should.
            assert dsp.to_db(dsp.rms(noises[first])) == pytest.approx(
                dsp.to_db(dsp.rms(noises[second])), abs=0.5
            )


def test_preparing_twice_needs_force(prepared) -> None:
    config, _, root = prepared
    with pytest.raises(StimulusError, match="--force"):
        prepare(config, root)


def test_the_same_seed_gives_the_same_set(config_dict: dict[str, Any], tmp_path: Path) -> None:
    _write_corpus(tmp_path / "corpus")
    config = _config(config_dict, tmp_path)
    first = prepare(config, tmp_path)
    second = prepare(config, tmp_path, force=True)

    # Video is re-encoded, so only the derived audio is compared — that is
    # where the RNG lives (noise waveforms, gap positions).
    assert [entry.file.sha256 for entry in first.noisy_tokens] == [
        entry.file.sha256 for entry in second.noisy_tokens
    ]
    assert [entry.gap_onsets_s for entry in first.gin_segments] == [
        entry.gap_onsets_s for entry in second.gin_segments
    ]


# ------------------------------------------------------------- failure paths


def test_a_missing_recording_is_reported(
    config_dict: dict[str, Any], tmp_path: Path
) -> None:
    _write_corpus(tmp_path / "corpus")
    (tmp_path / "corpus" / "Vis-da_Aud-da.mp4").unlink()
    with pytest.raises(StimulusError, match="Uyumlu kayıt yok"):
        prepare(_config(config_dict, tmp_path), tmp_path)


def test_a_missing_source_folder_is_reported(
    config_dict: dict[str, Any], tmp_path: Path
) -> None:
    with pytest.raises(StimulusError, match="kaynak klasörü yok"):
        prepare(_config(config_dict, tmp_path), tmp_path)


def test_a_recording_with_no_audio_is_reported(
    config_dict: dict[str, Any], tmp_path: Path
) -> None:
    """A silent source cannot be aligned, and silence is not an alignment."""
    _write_corpus(tmp_path / "corpus", silent_video=True)
    with pytest.raises(StimulusError, match="Ses akışı yok"):
        prepare(_config(config_dict, tmp_path), tmp_path)


def test_a_token_with_no_burst_is_reported(
    config_dict: dict[str, Any], tmp_path: Path
) -> None:
    corpus = tmp_path / "corpus"
    _write_corpus(corpus)
    flat = corpus / "flat.wav"
    rng = np.random.default_rng(1)
    wavfile.write(
        flat, rng.standard_normal(int(TOKEN_DURATION_S * SR)) * 0.1, SR, bit_depth=16
    )
    ffmpeg.run(
        "-y",
        "-f", "lavfi",
        "-i", f"testsrc=size=64x64:rate=30000/1001:duration={TOKEN_DURATION_S}",
        "-i", str(flat), "-c:a", "aac", "-shortest",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(corpus / "Vis-ba_Aud-ba.mp4"),
    )
    with pytest.raises(StimulusError, match="Patlama tespit edilemedi"):
        prepare(_config(config_dict, tmp_path), tmp_path)


# ------------------------------------------------------------- verification


def test_a_prepared_set_verifies(prepared) -> None:
    config, _, root = prepared
    report = verify(config, root)
    assert report.failures == 0, report.text()


def test_a_deleted_file_is_caught(prepared) -> None:
    config, result, root = prepared
    result.gin_segments[0].file.resolve(root / "stimuli").unlink()
    report = verify(config, root)
    assert report.failures >= 1
    assert "eksik" in report.text()


def test_an_edited_file_is_caught(prepared) -> None:
    """Checksums exist because "the file is there" is not the same as intact."""
    config, result, root = prepared
    path = result.tokens[0].file.resolve(root / "stimuli")
    samples, rate = wavfile.read(path)
    wavfile.write(path, samples * 0.5, rate, bit_depth=24)

    report = verify(config, root)
    assert report.failures >= 1
    assert "farklı" in report.text()


def test_a_video_that_regained_audio_is_caught(prepared) -> None:
    """The one failure that would still play, and silently break A/V sync."""
    config, result, root = prepared
    stimuli = root / "stimuli"
    entry = result.videos[0]
    path = entry.file.resolve(stimuli)
    with_audio = path.with_name("with_audio.mp4")
    ffmpeg.run(
        "-y", "-i", str(path),
        "-f", "lavfi", "-i", "sine=frequency=440",
        "-c:v", "copy", "-c:a", "aac", "-shortest", str(with_audio),
    )
    with_audio.replace(path)
    # The checksum changes too; this asserts the audio-stream check itself.
    entry.file.sha256 = manifest.sha256(path)
    entry.file.bytes = path.stat().st_size
    result.save(stimuli)

    report = verify(config, root)
    assert report.failures >= 1
    assert "ses akışı var" in report.text()


def test_a_missing_manifest_is_a_verdict_not_a_crash(
    config_dict: dict[str, Any], tmp_path: Path
) -> None:
    report = verify(_config(config_dict, tmp_path), tmp_path)
    assert report.failures == 1
    assert "prepare_stimuli" in report.text()


def test_ffmpeg_reports_what_it_was_asked_to_do() -> None:
    with pytest.raises(ffmpeg.FFmpegError, match="ffmpeg başarısız"):
        ffmpeg.run("-i", "definitely-not-a-file.mp4", "-f", "null", "-")


def test_probing_a_missing_file_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ffmpeg.FFmpegError, match="Dosya yok"):
        ffmpeg.probe(tmp_path / "nope.mp4")


def test_ffmpeg_is_the_one_on_path_when_there_is_one() -> None:
    assert Path(ffmpeg.find_ffmpeg()).exists()
    subprocess.run([ffmpeg.find_ffmpeg(), "-version"], capture_output=True, check=True)
