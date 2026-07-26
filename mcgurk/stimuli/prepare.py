"""Build the prepared stimulus set from the raw recordings.

The pipeline, per speaker (steps.md §C Adım 2):

1. Only the three congruent recordings are read.  They are the natural takes;
   the six incongruent files in ``assets/`` are an older re-mux of the same
   tokens with the audio pasted to t=0, and their alignment is exactly what
   this step exists to redo.
2. The video is re-encoded silent and at a constant frame rate.
3. The audio is extracted, its acoustic burst measured, and its level
   normalised over the speech-active part only.
4. Each audio token is then aligned to the burst time of *the video it will be
   shown with* — not to a single global target.  The source recordings are
   already in sync, so a video's own audio channel says where its visual
   gesture is; forcing every token to one instant would destroy that.
5. Noise, dichotic pairs and GIN segments are derived from the normalised
   tokens.

Every measurement is made again on the written file.  Anything outside
tolerance raises: a stimulus set that is a little bit wrong produces data that
looks fine and means nothing.
"""

from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ..config.loader import resolve_path
from ..config.schema import ExperimentConfig
from ..provenance import collect as collect_provenance
from . import StimulusError, dsp, ffmpeg, manifest, wavfile

logger = logging.getLogger(__name__)

#: Length of the speech-shaped noise master.  Long enough that every noisy
#: token can be cut from a different place in it.
SSN_MASTER_DURATION_S = 30.0

#: Peak level a written stimulus may not reach.  Leaves headroom for the
#: playback path's own gain trim (02_kalibrasyon.md).
MAX_PEAK_DBFS = -1.0

#: How far above its own noise floor a region may sit and still be treated as
#: silence that alignment may trim away.  These recordings have floors only
#: ~30 dB below the speech peak, so a rule stated relative to the speech level
#: cannot separate "quiet speech" from "this take's hiss"; stated relative to
#: the floor it can — speech sits 25 dB or more above it.
TRIM_MARGIN_DB = 10.0

#: The noise has to be steady, not merely finished fading, by the time the
#: token starts.
NOISE_STEADY_MARGIN_S = 0.05

_SUBDIRS = {
    "video": "video",
    "audio": "audio",
    "noisy": "audio_noisy",
    "dichotic": "dichotic",
    "gin": "gin",
    "noise": "noise",
}


@dataclass(frozen=True)
class _Token:
    """A normalised audio token on its own, original timeline."""

    speaker_id: int
    name: str
    samples: np.ndarray
    burst_s: float
    gain_db: float
    #: This take's own noise floor, which is what "silence" means for it.
    floor_dbfs: float
    source: manifest.SourceRef


def prepare(
    config: ExperimentConfig,
    project_root: Path,
    *,
    force: bool = False,
) -> manifest.StimulusManifest:
    """Prepare the whole stimulus set and write ``manifest.json``.

    Raises:
        StimulusError: on any missing source, failed measurement or tolerance
            violation.  There is no partial success mode — a half-prepared set
            would still look complete from the outside.
    """
    prep = config.stimulus_prep
    root = resolve_path(project_root, config.paths.stimuli)
    manifest_path = root / manifest.MANIFEST_NAME
    if manifest_path.exists() and not force:
        raise StimulusError(
            f"Uyaran seti zaten hazır: {manifest_path}\n"
            "Yeniden üretmek için --force verin."
        )
    root.mkdir(parents=True, exist_ok=True)

    sample_rate = config.audio.sample_rate
    seeds = np.random.SeedSequence(prep.seed).spawn(3)
    logger.info(
        "Uyaran hazırlığı başlıyor: %d konuşmacı, %d token, seed %d",
        len(prep.speakers), len(prep.tokens), prep.seed,
    )

    result = manifest.StimulusManifest(
        created_at=datetime.now(timezone.utc),
        provenance=collect_provenance(project_root).as_dict(),
        config={
            "stimulus_prep": prep.model_dump(mode="json"),
            "sample_rate": sample_rate,
            "required_snrs_db": config.required_snrs(),
        },
    )

    tokens: dict[tuple[int, str], _Token] = {}
    with tempfile.TemporaryDirectory(prefix="mcgurk_prep_") as tmp:
        work = Path(tmp)
        for speaker in prep.speakers:
            _prepare_speaker(
                config, project_root, root, work, speaker.id, result, tokens
            )

    _prepare_noise_and_derivatives(config, root, result, tokens, seeds)

    path = result.save(root)
    logger.info("Manifest yazıldı: %s (%d dosya)", path, len(result.files()))
    return result


# ------------------------------------------------------------------- speaker


def _prepare_speaker(
    config: ExperimentConfig,
    project_root: Path,
    root: Path,
    work: Path,
    speaker_id: int,
    result: manifest.StimulusManifest,
    tokens: dict[tuple[int, str], _Token],
) -> None:
    prep = config.stimulus_prep
    sample_rate = config.audio.sample_rate
    source_dir = resolve_path(project_root, prep.source_for(speaker_id))
    if not source_dir.is_dir():
        raise StimulusError(
            f"Konuşmacı {speaker_id} kaynak klasörü yok: {source_dir}"
        )

    logger.info("Konuşmacı %d: %s", speaker_id, source_dir)

    # -- read the congruent recordings ------------------------------------
    for name in prep.tokens:
        source = source_dir / f"Vis-{name}_Aud-{name}.mp4"
        if not source.is_file():
            raise StimulusError(
                f"Uyumlu kayıt yok: {source}\n"
                "Hazırlık yalnızca Vis-<t>_Aud-<t>.mp4 dosyalarını kullanır."
            )
        info = ffmpeg.probe(source)
        video_stream = info.require_video()
        audio_stream = info.require_audio()

        extracted = work / f"{speaker_id}_{name}.wav"
        ffmpeg.extract_audio(source, extracted, sample_rate=sample_rate)
        samples, rate = wavfile.read(extracted)
        if rate != sample_rate:
            raise StimulusError(
                f"{extracted} {rate} Hz çıktı, {sample_rate} Hz bekleniyordu"
            )
        samples = dsp.to_mono(samples)

        burst = dsp.detect_burst(
            samples,
            sample_rate,
            threshold_db=prep.burst.threshold_db,
            min_duration_ms=prep.burst.min_duration_ms,
        )
        normalised, gain_db = dsp.normalise_to_level(
            samples, sample_rate, prep.audio.target_level_dbfs,
            prep.audio.active_speech_threshold_db,
        )
        floor_dbfs = dsp.noise_floor_dbfs(normalised, sample_rate)
        logger.info(
            "  %s: patlama %.1f ms, kazanç %+.1f dB, gürültü tabanı %.1f dBFS",
            name, burst * 1000, gain_db, floor_dbfs,
        )
        tokens[(speaker_id, name)] = _Token(
            speaker_id=speaker_id,
            name=name,
            samples=normalised,
            burst_s=burst,
            gain_db=gain_db,
            floor_dbfs=floor_dbfs,
            source=manifest.SourceRef(
                path=source.relative_to(project_root).as_posix(),
                sha256=manifest.sha256(source),
                codec=audio_stream.codec,
                sample_rate=audio_stream.sample_rate,
                fps=video_stream.fps,
            ),
        )

    # -- silent video, then everything aligned to it ----------------------
    for name in prep.tokens:
        token = tokens[(speaker_id, name)]
        source = source_dir / f"Vis-{name}_Aud-{name}.mp4"
        video_entry = _write_video(
            config, root, source, speaker_id, name, token, project_root
        )
        result.videos.append(video_entry)

        n_samples = int(round(video_entry.duration_s * sample_rate))
        for audio_name in prep.tokens:
            result.tokens.append(
                _write_aligned_audio(
                    config,
                    root,
                    visual=name,
                    target_burst_s=video_entry.burst_time_s,
                    n_samples=n_samples,
                    token=tokens[(speaker_id, audio_name)],
                )
            )


def _write_video(
    config: ExperimentConfig,
    root: Path,
    source: Path,
    speaker_id: int,
    name: str,
    token: _Token,
    project_root: Path,
) -> manifest.VideoEntry:
    prep = config.stimulus_prep
    source_info = ffmpeg.probe(source)
    source_fps = source_info.require_video().fps
    source_frames = ffmpeg.count_frames(source)

    destination = root / _SUBDIRS["video"] / f"speaker_{speaker_id}" / f"Vis-{name}.mp4"
    ffmpeg.write_silent_video(
        source, destination,
        fps=prep.video.target_fps, crf=prep.video.crf, all_intra=prep.video.all_intra,
    )

    if ffmpeg.has_audio_stream(destination):
        raise StimulusError(
            f"Üretilen videoda ses akışı var: {destination} (§A.1). "
            "MovieStim gömülü sesi SDL2 üzerinden çalar ve A/V senkronu bozulur."
        )
    frames = ffmpeg.count_frames(destination)
    if frames != source_frames:
        raise StimulusError(
            f"{destination}: kare sayısı {source_frames} → {frames} değişti. "
            f"{source_fps:g} → {prep.video.target_fps:g} fps dönüşümü bu klip "
            "uzunluğunda kare eklememeli/atmamalı."
        )
    info = ffmpeg.probe(destination)
    stream = info.require_video()

    # The conversion relabels timestamps, so a visual event at t in the source
    # appears at t * (source_fps / target_fps) here.  The audio burst target
    # moves with it, otherwise the alignment would be off by the same factor.
    scale = source_fps / prep.video.target_fps
    duration_s = frames / prep.video.target_fps

    return manifest.VideoEntry(
        speaker_id=speaker_id,
        token=name,
        file=manifest.describe(destination, root),
        duration_s=duration_s,
        fps=stream.fps,
        frame_count=frames,
        width=stream.width,
        height=stream.height,
        burst_time_s=token.burst_s * scale,
        source=manifest.SourceRef(
            path=source.relative_to(project_root).as_posix(),
            sha256=token.source.sha256,
            codec=source_info.require_video().codec,
            sample_rate=token.source.sample_rate,
            fps=source_fps,
        ),
    )


def _write_aligned_audio(
    config: ExperimentConfig,
    root: Path,
    *,
    visual: str,
    target_burst_s: float,
    n_samples: int,
    token: _Token,
) -> manifest.TokenEntry:
    prep = config.stimulus_prep
    sample_rate = config.audio.sample_rate

    shifted, head = dsp.shift_to(
        token.samples, sample_rate, token.burst_s, target_burst_s
    )
    fitted, tail = dsp.fit_length(shifted, n_samples)
    _refuse_to_cut_speech(head, tail, sample_rate, visual, token)
    faded = _fade_edges(config, fitted, target_burst_s)

    destination = (
        root / _SUBDIRS["audio"] / f"speaker_{token.speaker_id}"
        / f"Vis-{visual}_Aud-{token.name}.wav"
    )
    wavfile.write(destination, faded, sample_rate, bit_depth=prep.audio.bit_depth)

    written, _ = wavfile.read(destination)
    measured = dsp.detect_burst(
        written, sample_rate,
        threshold_db=prep.burst.threshold_db,
        min_duration_ms=prep.burst.min_duration_ms,
    )
    error_ms = abs(measured - target_burst_s) * 1000.0
    if error_ms > prep.burst.alignment_tolerance_ms:
        raise StimulusError(
            f"{destination.name}: hizalama hatası {error_ms:.1f} ms, tolerans "
            f"{prep.burst.alignment_tolerance_ms:.1f} ms "
            f"(hedef {target_burst_s * 1000:.1f} ms, ölçülen {measured * 1000:.1f} ms)"
        )

    return manifest.TokenEntry(
        speaker_id=token.speaker_id,
        visual_token=visual,
        audio_token=token.name,
        file=manifest.describe(destination, root),
        duration_s=written.size / sample_rate,
        sample_rate=sample_rate,
        burst_time_s=measured,
        active_level_dbfs=dsp.active_speech_level_dbfs(
            written, sample_rate, prep.audio.active_speech_threshold_db
        ),
        peak_dbfs=dsp.peak_dbfs(written),
        gain_db=token.gain_db,
        source=token.source,
    )


def _fade_edges(
    config: ExperimentConfig, samples: np.ndarray, burst_s: float
) -> np.ndarray:
    """Fade the edges of a written speech file.

    Alignment leaves some files starting mid-hiss (the front was trimmed) and
    others starting in digital silence, so without this the trial onset would
    click on some trials and not others — a cue that has nothing to do with
    the stimulus.  The fade is refused rather than shortened if it could reach
    the burst, since that would change the token itself.
    """
    ramp_ms = config.stimulus_prep.audio.edge_ramp_ms
    if ramp_ms / 1000.0 + NOISE_STEADY_MARGIN_S > burst_s:
        raise StimulusError(
            f"stimulus_prep.audio.edge_ramp_ms ({ramp_ms:.0f} ms) patlamaya "
            f"({burst_s * 1000:.0f} ms) çok yakın — rampa konuşmaya değerdi"
        )
    return dsp.cosine_fade(samples, config.audio.sample_rate, ramp_ms)


def _refuse_to_cut_speech(
    head: np.ndarray,
    tail: np.ndarray,
    sample_rate: int,
    visual: str,
    token: _Token,
) -> None:
    """Alignment may only ever remove silence.

    Trimming into the token would change what the participant hears while
    still producing a file that plays and measures like a valid stimulus.
    Aligning the tokens of one speaker to each other's videos moves them by up
    to ~250 ms in this corpus, so the removed region is not always short and
    checking it is not a formality.
    """
    limit = token.floor_dbfs + TRIM_MARGIN_DB
    for part, where in ((head, "başından"), (tail, "sonundan")):
        if part.size == 0:
            continue
        loudest = dsp.to_db(float(np.max(dsp.frame_rms(part, sample_rate, 20.0))))
        if loudest > limit:
            raise StimulusError(
                f"Vis-{visual}/Aud-{token.name} (konuşmacı {token.speaker_id}): "
                f"hizalama sinyalin {where} sessiz olmayan bir bölge kırpardı "
                f"({part.size / sample_rate * 1000:.0f} ms, en yüksek çerçeve "
                f"{loudest:.1f} dBFS > taban {token.floor_dbfs:.1f} + "
                f"{TRIM_MARGIN_DB:.0f} dB)"
            )


# ------------------------------------------------- noise, dichotic and GIN


def _prepare_noise_and_derivatives(
    config: ExperimentConfig,
    root: Path,
    result: manifest.StimulusManifest,
    tokens: dict[tuple[int, str], _Token],
    seeds: list[np.random.SeedSequence],
) -> None:
    if config.required_snrs():
        master = _write_speech_shaped_noise(
            config, root, result, tokens, np.random.default_rng(seeds[0])
        )
        _write_noisy_tokens(
            config, root, result, master, np.random.default_rng(seeds[1])
        )
    else:
        logger.info("Hiçbir etkin modül gürültü istemiyor — SSN üretilmedi")

    if config.modules.dichotic.enabled:
        _write_dichotic(config, root, result, tokens)
    if config.modules.gin.enabled:
        _write_gin(config, root, result, np.random.default_rng(seeds[2]))


def _corpus_ltas(
    tokens: dict[tuple[int, str], _Token], sample_rate: int, threshold_db: float
) -> np.ndarray:
    """LTAS of every normalised token, speech-active frames only."""
    if not tokens:
        raise StimulusError("Korpus boş — LTAS hesaplanamaz")
    concatenated = np.concatenate([token.samples for token in tokens.values()])
    return dsp.ltas(concatenated, sample_rate, threshold_db=threshold_db)


def _write_speech_shaped_noise(
    config: ExperimentConfig,
    root: Path,
    result: manifest.StimulusManifest,
    tokens: dict[tuple[int, str], _Token],
    rng: np.random.Generator,
) -> np.ndarray:
    prep = config.stimulus_prep
    sample_rate = config.audio.sample_rate

    corpus = _corpus_ltas(tokens, sample_rate, prep.audio.active_speech_threshold_db)
    n_samples = int(round(SSN_MASTER_DURATION_S * sample_rate))
    noise = dsp.speech_shaped_noise(corpus, sample_rate, n_samples, rng)

    _, deviations = dsp.ltas_deviation_db(
        dsp.ltas(noise, sample_rate), corpus, sample_rate
    )
    worst = float(np.max(np.abs(deviations)))
    if worst > prep.noise.ltas_tolerance_db:
        raise StimulusError(
            f"Konuşma şekilli gürültünün LTAS'ı korpustan {worst:.1f} dB "
            f"sapıyor, tolerans {prep.noise.ltas_tolerance_db:.1f} dB"
        )
    logger.info("SSN üretildi: en büyük 1/3 oktav sapması %.2f dB", worst)

    # Faded like anything else that can be played: the master is a source
    # file, but it sits in stimuli/ and someone will audition it.  Excerpts
    # are taken from the interior only (see _write_noisy_tokens), so the fade
    # never ends up inside one.
    scaled = dsp.cosine_fade(
        np.asarray(noise * 10.0 ** (prep.audio.target_level_dbfs / 20.0)),
        sample_rate,
        prep.noise.ramp_ms,
    )
    destination = root / _SUBDIRS["noise"] / "speech_shaped_noise.wav"
    wavfile.write(destination, scaled, sample_rate, bit_depth=prep.audio.bit_depth)
    result.noise = manifest.NoiseEntry(
        file=manifest.describe(destination, root),
        duration_s=scaled.size / sample_rate,
        sample_rate=sample_rate,
        max_ltas_deviation_db=worst,
    )
    return scaled


def _check_noise_is_up_before_the_speech(
    config: ExperimentConfig, entry: manifest.TokenEntry
) -> None:
    """The noise fade must finish before the token starts.

    A long fade sounds better — broadband noise reaching full level in 50 ms
    arrives rather than starts — but if it were still rising when the token
    began, the early part of the speech would sit at a higher SNR than the
    nominal one, and by a different amount per token.

    The burst is the reference, not a speech-onset detector: these are stop
    consonants, so the closure before the burst is silent, and the burst is
    already measured to the millisecond.  An energy-based onset would not
    survive this corpus anyway — speaker 2's noise floor is only ~31 dB below
    the speech peak, so the activity threshold catches the floor itself.
    """
    prep = config.stimulus_prep
    ramp_s = prep.noise.ramp_ms / 1000.0
    if ramp_s + NOISE_STEADY_MARGIN_S > entry.burst_time_s:
        raise StimulusError(
            f"Konuşmacı {entry.speaker_id}, Vis-{entry.visual_token}/"
            f"Aud-{entry.audio_token}: gürültü rampası {ramp_s * 1000:.0f} ms "
            f"+ {NOISE_STEADY_MARGIN_S * 1000:.0f} ms pay, patlama "
            f"{entry.burst_time_s * 1000:.0f} ms'de. Rampa bitmeden konuşma "
            "başlarsa etkin SNR nominalinden yüksek olur. "
            "stimulus_prep.noise.ramp_ms düşürülmeli."
        )


def _write_noisy_tokens(
    config: ExperimentConfig,
    root: Path,
    result: manifest.StimulusManifest,
    master: np.ndarray,
    rng: np.random.Generator,
) -> None:
    prep = config.stimulus_prep
    sample_rate = config.audio.sample_rate

    for entry in list(result.tokens):
        speech, _ = wavfile.read(entry.file.resolve(root))
        _check_noise_is_up_before_the_speech(config, entry)
        # The master's own fade must not land inside an excerpt, so excerpts
        # come from its interior.
        margin = int(round(prep.noise.ramp_ms * sample_rate / 1000.0))
        latest = master.size - speech.size - margin
        if latest <= margin:
            raise StimulusError(
                f"SSN master'ı ({master.size / sample_rate:.1f} s) "
                f"{speech.size / sample_rate:.1f} s'lik kesitler için çok kısa"
            )
        for snr_db in config.required_snrs():
            for instance in range(prep.noise.instances):
                offset = int(rng.integers(margin, latest))
                excerpt = dsp.cosine_fade(
                    master[offset : offset + speech.size],
                    sample_rate,
                    prep.noise.ramp_ms,
                )
                mixed, measured = dsp.mix_at_snr(
                    speech, excerpt, sample_rate, snr_db,
                    prep.audio.active_speech_threshold_db,
                )
                peak = dsp.peak_dbfs(mixed)
                if peak > MAX_PEAK_DBFS:
                    raise StimulusError(
                        f"Gürültü karışımı tepe seviyesi {peak:.1f} dBFS "
                        f"({MAX_PEAK_DBFS:.1f} dBFS sınırı aşıldı): konuşmacı "
                        f"{entry.speaker_id}, Vis-{entry.visual_token}/"
                        f"Aud-{entry.audio_token}, SNR {snr_db} dB. "
                        "target_level_dbfs düşürülmeli."
                    )
                destination = (
                    root / _SUBDIRS["noisy"] / f"speaker_{entry.speaker_id}"
                    / f"Vis-{entry.visual_token}_Aud-{entry.audio_token}"
                      f"_ssn{snr_db:g}dB_{instance + 1}.wav"
                )
                wavfile.write(
                    destination, mixed, sample_rate, bit_depth=prep.audio.bit_depth
                )
                result.noisy_tokens.append(
                    manifest.NoisyTokenEntry(
                        speaker_id=entry.speaker_id,
                        visual_token=entry.visual_token,
                        audio_token=entry.audio_token,
                        snr_db=snr_db,
                        instance=instance + 1,
                        file=manifest.describe(destination, root),
                        duration_s=mixed.size / sample_rate,
                        sample_rate=sample_rate,
                        measured_snr_db=measured,
                        peak_dbfs=peak,
                    )
                )
    logger.info("Gürültülü uyaran: %d dosya", len(result.noisy_tokens))


def _write_dichotic(
    config: ExperimentConfig,
    root: Path,
    result: manifest.StimulusManifest,
    tokens: dict[tuple[int, str], _Token],
) -> None:
    """Stereo files with a different token in each ear.

    Both ears are aligned to one common burst time rather than to their own.
    The two tokens' natural bursts differ by up to ~250 ms in this corpus, and
    an ear advantage measured with asynchronous onsets would be partly an
    onset-asynchrony effect.  There is no video here, so nothing is lost by
    imposing a common instant.
    """
    prep = config.stimulus_prep
    sample_rate = config.audio.sample_rate

    for speaker in prep.speakers:
        speaker_videos = [v for v in result.videos if v.speaker_id == speaker.id]
        if not speaker_videos:
            continue
        common_burst = float(np.mean([v.burst_time_s for v in speaker_videos]))
        n_samples = int(round(
            min(video.duration_s for video in speaker_videos) * sample_rate
        ))

        for pair in config.modules.dichotic.pairs:
            channels = []
            for name in (pair.left, pair.right):
                token = tokens[(speaker.id, name)]
                shifted, head = dsp.shift_to(
                    token.samples, sample_rate, token.burst_s, common_burst
                )
                fitted, tail = dsp.fit_length(shifted, n_samples)
                _refuse_to_cut_speech(head, tail, sample_rate, "dichotic", token)
                channels.append(_fade_edges(config, fitted, common_burst))
            stereo = np.stack(channels, axis=1)

            destination = (
                root / _SUBDIRS["dichotic"] / f"speaker_{speaker.id}"
                / f"Left-{pair.left}_Right-{pair.right}.wav"
            )
            wavfile.write(
                destination, stereo, sample_rate, bit_depth=prep.audio.bit_depth
            )
            result.dichotic.append(
                manifest.DichoticEntry(
                    speaker_id=speaker.id,
                    left_token=pair.left,
                    right_token=pair.right,
                    file=manifest.describe(destination, root),
                    duration_s=n_samples / sample_rate,
                    sample_rate=sample_rate,
                    burst_time_s=common_burst,
                    peak_dbfs=dsp.peak_dbfs(stereo),
                )
            )
    logger.info("Dikotik uyaran: %d dosya", len(result.dichotic))


def _write_gin(
    config: ExperimentConfig,
    root: Path,
    result: manifest.StimulusManifest,
    rng: np.random.Generator,
) -> None:
    prep = config.stimulus_prep
    gin = config.modules.gin
    sample_rate = config.audio.sample_rate

    durations = [d for d in gin.gap_durations_ms for _ in range(gin.reps_per_gap)]
    plan = dsp.plan_gaps(
        rng,
        gap_durations_ms=durations,
        n_segments=gin.n_segments,
        max_gaps_per_segment=gin.max_gaps_per_segment,
        segment_duration_s=gin.segment_duration_s,
        min_separation_s=gin.min_gap_separation_s,
    )

    n_samples = int(round(gin.segment_duration_s * sample_rate))
    low, high = prep.gin.bandwidth_hz
    for index, gaps in enumerate(plan, start=1):
        noise = dsp.bandlimited_noise(n_samples, sample_rate, low, high, rng)
        noise = noise * 10.0 ** (prep.audio.target_level_dbfs / 20.0)
        segment = dsp.apply_gaps(noise, sample_rate, gaps, prep.gin.gap_ramp_ms)
        segment = dsp.cosine_fade(segment, sample_rate, prep.gin.segment_ramp_ms)

        peak = dsp.peak_dbfs(segment)
        if peak > MAX_PEAK_DBFS:
            raise StimulusError(
                f"GIN segmenti {index} tepe seviyesi {peak:.1f} dBFS "
                f"({MAX_PEAK_DBFS:.1f} dBFS sınırı aşıldı)"
            )

        destination = root / _SUBDIRS["gin"] / f"segment_{index:02d}.wav"
        wavfile.write(
            destination, segment, sample_rate, bit_depth=prep.audio.bit_depth
        )
        result.gin_segments.append(
            manifest.GinSegmentEntry(
                index=index,
                file=manifest.describe(destination, root),
                duration_s=segment.size / sample_rate,
                sample_rate=sample_rate,
                gap_onsets_s=[round(onset, 6) for onset, _ in gaps],
                gap_durations_ms=[duration for _, duration in gaps],
                level_dbfs=dsp.to_db(dsp.rms(segment)),
            )
        )

    placed = sum(len(entry.gap_onsets_s) for entry in result.gin_segments)
    if placed != len(durations):
        raise StimulusError(
            f"GIN: {len(durations)} boşluk planlandı, {placed} yerleştirildi"
        )
    logger.info(
        "GIN: %d segment, %d boşluk", len(result.gin_segments), placed
    )
