"""Audit a prepared stimulus set against its manifest and the design.

Preparation already checks everything it produces.  This exists because the
files outlive the run that made them: they get copied between machines, edited
by hand, half-regenerated after a config change.  Everything is therefore
measured again from disk rather than trusted from the manifest, and the design
is checked for coverage — a missing SNR or speaker shows up here rather than
mid-session.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..config.loader import resolve_path
from ..config.schema import ExperimentConfig
from . import StimulusError, dsp, ffmpeg, manifest, wavfile

logger = logging.getLogger(__name__)

#: How far a re-measured level may sit from the manifest value.  Not zero:
#: the manifest records dB computed from float samples, the file is quantised.
LEVEL_TOLERANCE_DB = 0.5

#: Every playable file has to start and end at silence.  Alignment trims up to
#: ~250 ms off the front of some tokens, so without an edge fade those files
#: would begin mid-hiss while the rest begin in digital silence — a click on
#: some trials and not others.
EDGE_LIMIT_DBFS = -80.0


@dataclass
class Report:
    """Accumulated findings, in the order they were made."""

    lines: list[str] = field(default_factory=list)
    failures: int = 0

    def ok(self, message: str) -> None:
        self.lines.append(f"YESIL    {message}")

    def fail(self, message: str) -> None:
        self.failures += 1
        self.lines.append(f"KIRMIZI  {message}")

    def note(self, message: str) -> None:
        self.lines.append(f"         {message}")

    def check(self, condition: bool, ok_message: str, fail_message: str) -> bool:
        if condition:
            self.ok(ok_message)
        else:
            self.fail(fail_message)
        return condition

    def text(self) -> str:
        return "\n".join(self.lines)


def verify(
    config: ExperimentConfig,
    project_root: Path,
    *,
    deep: bool = True,
) -> Report:
    """Check the prepared set; the report's ``failures`` is the verdict.

    Args:
        deep: Re-measure burst times, levels and spectra.  Off, only presence
            and checksums are checked — enough for a session checklist that
            has to finish in a second.
    """
    report = Report()
    root = resolve_path(project_root, config.paths.stimuli)
    report.note(f"Uyaran kökü: {root}")

    try:
        loaded = manifest.load(root)
    except StimulusError as exc:
        report.fail(str(exc))
        return report
    report.ok(f"Manifest okundu (sürüm {loaded.manifest_version})")
    report.note(f"Üretim: {loaded.created_at.isoformat(timespec='seconds')}")

    _check_files(loaded, root, report)
    _check_coverage(config, loaded, report)
    if deep and report.failures == 0:
        _check_videos(loaded, root, report)
        _check_tokens(config, loaded, root, report)
        _check_noise(config, loaded, root, report)
        _check_gin(config, loaded, root, report)
        _check_tones(config, loaded, root, report)
        _check_thumbnails(config, loaded, report)
        _check_edges(loaded, root, report)
    elif deep:
        report.note("Derin kontroller atlandı — önce yukarıdaki hatalar giderilmeli")
    return report


def _check_files(
    loaded: manifest.StimulusManifest, root: Path, report: Report
) -> None:
    missing: list[str] = []
    changed: list[str] = []
    for entry in loaded.files():
        path = entry.resolve(root)
        if not path.is_file():
            missing.append(entry.path)
            continue
        if manifest.sha256(path) != entry.sha256:
            changed.append(entry.path)

    total = len(loaded.files())
    if missing:
        report.fail(f"{len(missing)}/{total} dosya eksik: {missing[:5]}")
    if changed:
        report.fail(
            f"{len(changed)}/{total} dosyanın içeriği manifest'ten farklı: "
            f"{changed[:5]}"
        )
    if not missing and not changed:
        report.ok(f"{total} dosya yerinde, sağlama toplamları uyuşuyor")


def _check_coverage(
    config: ExperimentConfig, loaded: manifest.StimulusManifest, report: Report
) -> None:
    """Everything the enabled modules will ask for must exist."""
    problems: list[str] = []
    required = config.required_tokens()

    # The audiovisual modules need a video per visual token and an audio file
    # per (visual, audio) combination they can present.
    for name in ("mcgurk", "avsr", "tbw"):
        module = config.modules.by_name()[name]
        if not module.enabled:
            continue
        speaker_id: int = module.speaker_id  # type: ignore[attr-defined]
        tokens = required.get(name, [])
        snrs = [
            snr
            for snr in getattr(module, "noise_conditions", [])
            if snr is not None
        ]
        for visual in tokens:
            try:
                loaded.video(speaker_id, visual)
            except manifest.ManifestError as exc:
                problems.append(f"{name}: {exc}")
            for audio in tokens:
                try:
                    loaded.token(speaker_id, visual, audio)
                except manifest.ManifestError as exc:
                    problems.append(f"{name}: {exc}")
                for snr in snrs:
                    try:
                        loaded.noisy(speaker_id, visual, audio, snr)
                    except manifest.ManifestError as exc:
                        problems.append(f"{name}: {exc}")

    if config.modules.dichotic.enabled:
        for pair in config.modules.dichotic.pairs:
            try:
                loaded.dichotic_pair(
                    config.modules.dichotic.speaker_id, pair.left, pair.right
                )
            except manifest.ManifestError as exc:
                problems.append(str(exc))

    for frequency in config.required_tones():
        try:
            loaded.tone(frequency)
        except manifest.ManifestError as exc:
            problems.append(f"oddball: {exc}")

    if config.modules.gin.enabled:
        expected = config.modules.gin.n_segments
        if len(loaded.gin_segments) != expected:
            problems.append(
                f"GIN: {len(loaded.gin_segments)} segment var, config {expected} "
                "istiyor"
            )
        placed = sum(len(s.gap_onsets_s) for s in loaded.gin_segments)
        if placed != config.modules.gin.total_gaps():
            problems.append(
                f"GIN: {placed} boşluk var, config {config.modules.gin.total_gaps()} "
                "istiyor"
            )

    # Duplicates report the same missing item once per unique message.
    unique = sorted(set(problems))
    if unique:
        report.fail(f"Tasarımın istediği {len(unique)} uyaran eksik:")
        for problem in unique[:10]:
            report.note(f"  {problem}")
    else:
        report.ok("Etkin modüllerin istediği her uyaran manifest'te var")


def _check_videos(
    loaded: manifest.StimulusManifest, root: Path, report: Report
) -> None:
    problems: list[str] = []
    for entry in loaded.videos:
        path = entry.file.resolve(root)
        if ffmpeg.has_audio_stream(path):
            problems.append(f"{entry.file.path}: ses akışı var (§A.1)")
        frames = ffmpeg.count_frames(path)
        if frames != entry.frame_count:
            problems.append(
                f"{entry.file.path}: {frames} kare, manifest {entry.frame_count}"
            )
        fps = ffmpeg.probe(path).require_video().fps
        if abs(fps - entry.fps) > 0.01:
            problems.append(f"{entry.file.path}: {fps:g} fps, manifest {entry.fps:g}")

    if problems:
        report.fail(f"{len(problems)} video sorunu:")
        for problem in problems[:10]:
            report.note(f"  {problem}")
    else:
        report.ok(f"{len(loaded.videos)} video sessiz, CFR ve tam kare sayısında")


def _check_tokens(
    config: ExperimentConfig,
    loaded: manifest.StimulusManifest,
    root: Path,
    report: Report,
) -> None:
    prep = config.stimulus_prep
    problems: list[str] = []
    worst_burst_ms = 0.0

    for entry in loaded.tokens:
        samples, rate = wavfile.read(entry.file.resolve(root))
        if rate != entry.sample_rate:
            problems.append(f"{entry.file.path}: {rate} Hz, manifest {entry.sample_rate}")
            continue
        video = loaded.video(entry.speaker_id, entry.visual_token)
        burst = dsp.detect_burst(
            samples, rate,
            threshold_db=prep.burst.threshold_db,
            min_duration_ms=prep.burst.min_duration_ms,
        )
        error_ms = abs(burst - video.burst_time_s) * 1000.0
        worst_burst_ms = max(worst_burst_ms, error_ms)
        if error_ms > prep.burst.alignment_tolerance_ms:
            problems.append(
                f"{entry.file.path}: patlama hedeften {error_ms:.1f} ms sapıyor"
            )
        level = dsp.active_speech_level_dbfs(
            samples, rate, prep.audio.active_speech_threshold_db
        )
        if abs(level - prep.audio.target_level_dbfs) > LEVEL_TOLERANCE_DB:
            problems.append(
                f"{entry.file.path}: aktif konuşma seviyesi {level:.2f} dBFS, "
                f"hedef {prep.audio.target_level_dbfs:.2f} dBFS"
            )

    if problems:
        report.fail(f"{len(problems)} ses sorunu:")
        for problem in problems[:10]:
            report.note(f"  {problem}")
    else:
        report.ok(
            f"{len(loaded.tokens)} ses dosyası hizalı (en büyük sapma "
            f"{worst_burst_ms:.1f} ms) ve eşit seviyede"
        )


def _check_noise(
    config: ExperimentConfig,
    loaded: manifest.StimulusManifest,
    root: Path,
    report: Report,
) -> None:
    prep = config.stimulus_prep
    if loaded.noise is None:
        if config.required_snrs():
            report.fail("Tasarım gürültü istiyor ama manifest'te SSN yok")
        return

    noise, rate = wavfile.read(loaded.noise.file.resolve(root))
    corpus = np.concatenate(
        [wavfile.read(entry.file.resolve(root))[0] for entry in loaded.tokens]
    )
    _, deviations = dsp.ltas_deviation_db(
        dsp.ltas(noise, rate),
        dsp.ltas(corpus, rate, threshold_db=prep.audio.active_speech_threshold_db),
        rate,
    )
    worst = float(np.max(np.abs(deviations)))
    report.check(
        worst <= prep.noise.ltas_tolerance_db,
        f"SSN'in LTAS'ı korpusla uyuşuyor (en büyük sapma {worst:.2f} dB)",
        f"SSN'in LTAS'ı korpustan {worst:.2f} dB sapıyor, tolerans "
        f"{prep.noise.ltas_tolerance_db:.1f} dB",
    )

    problems: list[str] = []
    for entry in loaded.noisy_tokens:
        mixed, mix_rate = wavfile.read(entry.file.resolve(root))
        peak = dsp.peak_dbfs(mixed)
        if peak > -1.0:
            problems.append(f"{entry.file.path}: tepe {peak:.1f} dBFS")
        if mix_rate != entry.sample_rate:
            problems.append(f"{entry.file.path}: {mix_rate} Hz")
    if problems:
        report.fail(f"{len(problems)} gürültülü uyaran sorunu:")
        for problem in problems[:10]:
            report.note(f"  {problem}")
    else:
        report.ok(f"{len(loaded.noisy_tokens)} gürültülü uyaran kırpma sınırının altında")


def _check_thumbnails(
    config: ExperimentConfig, loaded: manifest.StimulusManifest, report: Report
) -> None:
    """One still per prepared speaker, for the operator's menu (Adım 12c-ii).

    The bytes are already checked by ``_check_files``; what matters here is
    *coverage*, because a missing still is not a broken picture — it is a
    speaker the operator cannot recognise in the menu, and picking the wrong
    face is a silent error in the data.
    """
    if config.stimulus_prep.thumbnail is None:
        report.note("stimulus_prep.thumbnail tanımlı değil — küçük resim yok")
        return

    prepared = set(config.stimulus_prep.speaker_ids())
    have = {entry.speaker_id for entry in loaded.thumbnails}
    missing = sorted(prepared - have)
    if missing:
        report.fail(
            f"Küçük resmi olmayan konuşmacı: {missing}. Operatör menüsü onları "
            "yüzüyle gösteremez; python tools/prepare_stimuli.py --force"
        )
        return
    report.ok(f"{len(have)} konuşmacı küçük resmi yerinde")


def _check_tones(
    config: ExperimentConfig,
    loaded: manifest.StimulusManifest,
    root: Path,
    report: Report,
) -> None:
    """The oddball tones, re-measured from disk.

    The frequency is checked because the file is named after it, and the ramp
    because it is the only thing separating a 50 ms tone from a click: a tone
    that begins abruptly can be told apart from another one without either
    frequency being heard, which would make the oddball task solvable by
    something other than pitch.
    """
    if not loaded.tones:
        return
    oddball = config.modules.oddball
    problems: list[str] = []

    for entry in loaded.tones:
        samples, rate = wavfile.read(entry.file.resolve(root))
        if rate != entry.sample_rate:
            problems.append(f"{entry.file.path}: {rate} Hz, manifest {entry.sample_rate}")
            continue

        measured = dsp.dominant_frequency_hz(samples, rate)
        resolution = rate / samples.size
        if abs(measured - entry.frequency_hz) > 2.0 * resolution:
            problems.append(
                f"{entry.file.path}: baskın frekans {measured:.0f} Hz, "
                f"manifest {entry.frequency_hz:g} Hz"
            )

        duration_ms = samples.size / rate * 1000.0
        if abs(duration_ms - oddball.tone_duration_ms) > 1.0:
            problems.append(
                f"{entry.file.path}: {duration_ms:.1f} ms, config "
                f"{oddball.tone_duration_ms:g} ms istiyor"
            )

        level = dsp.to_db(dsp.rms(samples))
        if abs(level - config.stimulus_prep.tones.level_dbfs) > LEVEL_TOLERANCE_DB:
            problems.append(
                f"{entry.file.path}: seviye {level:.2f} dBFS, hedef "
                f"{config.stimulus_prep.tones.level_dbfs:.2f} dBFS"
            )
        if dsp.peak_dbfs(samples) > -1.0:
            problems.append(f"{entry.file.path}: tepe {dsp.peak_dbfs(samples):.1f} dBFS")

        # The ramp: a quarter of the way into it the envelope must still be
        # well below the plateau.  An un-ramped tone is already at full level
        # there, and that is the failure this is looking for.
        ramp_samples = int(round(oddball.tone_ramp_ms * rate / 1000.0))
        if ramp_samples >= 4:
            quarter = float(np.max(np.abs(samples[: ramp_samples // 4])))
            plateau = float(np.max(np.abs(samples)))
            if plateau > 0 and quarter > 0.5 * plateau:
                problems.append(
                    f"{entry.file.path}: rampanın ilk çeyreği tepe seviyenin "
                    f"%{100 * quarter / plateau:.0f}'inde — rampa uygulanmamış"
                )

    if problems:
        report.fail(f"{len(problems)} ton sorunu:")
        for problem in problems[:10]:
            report.note(f"  {problem}")
    else:
        report.ok(
            f"{len(loaded.tones)} oddball tonu: frekans, süre, seviye ve rampa "
            "beklendiği gibi"
        )


def _check_edges(
    loaded: manifest.StimulusManifest, root: Path, report: Report
) -> None:
    """No audio file may start or end on a step.

    Applies to everything playable, including the speech-shaped noise master:
    it is a source file, but it sits in the stimulus tree and someone will
    audition it.
    """
    problems: list[str] = []
    entries = [entry.file for entry in loaded.tokens]
    entries += [entry.file for entry in loaded.dichotic]
    entries += [entry.file for entry in loaded.noisy_tokens]
    entries += [entry.file for entry in loaded.gin_segments]
    entries += [entry.file for entry in loaded.tones]
    if loaded.noise is not None:
        entries.append(loaded.noise.file)

    for media in entries:
        samples, _ = wavfile.read(media.resolve(root))
        mono = dsp.to_mono(samples)
        first = dsp.to_db(abs(float(mono[0])))
        last = dsp.to_db(abs(float(mono[-1])))
        if max(first, last) > EDGE_LIMIT_DBFS:
            problems.append(
                f"{media.path}: ilk {first:.0f} dBFS, son {last:.0f} dBFS "
                f"(sınır {EDGE_LIMIT_DBFS:.0f} dBFS)"
            )

    if problems:
        report.fail(f"{len(problems)} dosya sessizlikten başlamıyor/bitmiyor:")
        for problem in problems[:10]:
            report.note(f"  {problem}")
    else:
        report.ok(f"{len(entries)} ses dosyası sessizlikten başlıyor ve bitiyor")


def _check_gin(
    config: ExperimentConfig,
    loaded: manifest.StimulusManifest,
    root: Path,
    report: Report,
) -> None:
    if not loaded.gin_segments:
        return
    gin = config.modules.gin
    problems: list[str] = []
    counts: dict[float, int] = {}

    for entry in loaded.gin_segments:
        samples, rate = wavfile.read(entry.file.resolve(root))
        if len(entry.gap_onsets_s) > gin.max_gaps_per_segment:
            problems.append(
                f"segment {entry.index}: {len(entry.gap_onsets_s)} boşluk, "
                f"en fazla {gin.max_gaps_per_segment}"
            )
        previous_end = 0.0
        for onset, duration_ms in zip(
            entry.gap_onsets_s, entry.gap_durations_ms, strict=True
        ):
            counts[duration_ms] = counts.get(duration_ms, 0) + 1
            if onset - previous_end < gin.min_gap_separation_s - 1e-6:
                problems.append(
                    f"segment {entry.index}: {onset:.3f} s'deki boşluk bir "
                    "öncekine çok yakın"
                )
            previous_end = onset + duration_ms / 1000.0

            # The gap has to actually be silent in the file, not just in the
            # manifest: a mis-scored gap would look like a detection failure.
            start = int(round(onset * rate))
            end = int(round((onset + duration_ms / 1000.0) * rate))
            middle = samples[start + rate // 1000 : max(end - rate // 1000, start + 1)]
            if middle.size and dsp.peak_dbfs(middle) > entry.level_dbfs - 40.0:
                problems.append(
                    f"segment {entry.index}: {onset:.3f} s'deki boşluk sessiz değil"
                )
        if previous_end > entry.duration_s - gin.min_gap_separation_s + 1e-6:
            problems.append(f"segment {entry.index}: son boşluk kenara çok yakın")

    expected = {duration: gin.reps_per_gap for duration in gin.gap_durations_ms}
    if counts != expected:
        problems.append(f"boşluk süresi dağılımı beklenenden farklı: {counts}")

    if problems:
        report.fail(f"{len(problems)} GIN sorunu:")
        for problem in problems[:10]:
            report.note(f"  {problem}")
    else:
        report.ok(
            f"{len(loaded.gin_segments)} GIN segmenti: boşluklar sessiz, "
            f"aralık ve dağılım kısıtları sağlanıyor"
        )
