"""Verify the timing architecture before trusting it with data (steps.md §C Adım 3).

Three levels, each answering a different question:

    python tools/timing_selftest.py --level 1
        No hardware.  Is the backend really PTB, does the window keep the
        refresh grid, and does a sound scheduled for a future time actually
        start then?  Runs on any machine.

    python tools/timing_selftest.py --level 2 --play
    python tools/timing_selftest.py --level 2 --analyze kayit.wav
        One cable: headphone output into an input.  Plays a click train with
        known times, then measures the jitter in a recording of it.  This is
        the test that catches a silent fallback: if PTB is not really in
        charge, or `when=` is ignored, level 1 can still look fine and this
        cannot.

    python tools/timing_selftest.py --level 3
        Photodiode.  Prints the procedure and hands over to
        docs/01_av_gecikme_olcumu.md, whose scripts are the measurement — this
        tool does not reimplement them.  Done once, after all the code is
        finished, because the absolute offset is a single number in the config
        and changes no architecture.

    python tools/timing_selftest.py --demo
        Presents a handful of real trials from the prepared set and prints the
        realised timing of each.  This is what the manual test in
        TEST_ADIM_3.md drives.

Exit code 0 = the checks that ran, passed.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcgurk.config.calibration import Calibration, load_calibration  # noqa: E402
from mcgurk.config.loader import ConfigError, load_config, resolve_path  # noqa: E402
from mcgurk.config.schema import ExperimentConfig  # noqa: E402
from mcgurk.engine import AbortSession  # noqa: E402
from mcgurk.engine.audio import (  # noqa: E402
    AudioStimulus,
    make_sound,
    open_speaker,
    playback_health,
    reported_start_time,
    require_ptb_backend,
)
from mcgurk.engine.av_presenter import AVPresenter, TrialSpec  # noqa: E402
from mcgurk.engine.loopback import LoopbackError, analyse_click_train, make_click  # noqa: E402
from mcgurk.engine.psychopy_prefs import configure_psychopy  # noqa: E402
from mcgurk.engine.scheduling import TimingParams, plan_presentation  # noqa: E402
from mcgurk.engine.window import (  # noqa: E402
    check_refresh_hz,
    make_fixation,
    measure_refresh_hz,
    open_window,
)
from mcgurk.logging_setup import setup_logging  # noqa: E402
from mcgurk.stimuli import manifest as manifest_module  # noqa: E402

DEFAULT_CLICKS = 20
DEFAULT_CLICK_INTERVAL_S = 0.5
SCHEDULE_FILE = "timing_selftest_clicks.json"


# ------------------------------------------------------------------ helpers


def _rule(title: str) -> None:
    print()
    print(title)
    print("-" * max(40, len(title)))


def _timing_params(config: ExperimentConfig, refresh_hz: float) -> TimingParams:
    return TimingParams(
        frame_period_s=1.0 / refresh_hz,
        lead_frames=config.timing.lead_frames,
        system_av_offset_ms=config.timing.system_av_offset_ms or 0.0,
        dropped_frame_tolerance=config.timing.dropped_frame_tolerance,
    )


def _calibration(config: ExperimentConfig) -> Calibration | None:
    if config.audio.calibration_file is None:
        return None
    return load_calibration(resolve_path(_PROJECT_ROOT, config.audio.calibration_file))


def _click_stimulus(sample_rate: int) -> AudioStimulus:
    return AudioStimulus(
        path=Path("<click>"),
        samples=make_click(sample_rate),
        sample_rate=sample_rate,
        burst_time_s=0.0,
        ear="both",
    )


def _open_audio(config: ExperimentConfig) -> object:
    configure_psychopy(audio_device=config.audio.device)
    require_ptb_backend()
    return open_speaker(
        device_name=config.audio.device,
        latency_class=config.timing.audio_latency_mode,
        sample_rate=config.audio.sample_rate,
    )


def list_devices(config: ExperimentConfig) -> int:
    """Print the output devices, so ``audio.device`` can be filled in.

    Leaving it null is how a session ends up on whatever device the driver
    happens to enumerate first — which on this machine is an SPDIF port with
    nothing plugged into it.  Silence is the *lucky* outcome of that; the
    unlucky one is a session collected through the monitor's speakers.
    """
    configure_psychopy()
    from psychopy.hardware.speaker import SpeakerDevice

    _rule("Ses çıkış aygıtları")
    devices = SpeakerDevice.getAvailableDevices()
    if not devices:
        print("  Hiç çıkış aygıtı bulunamadı.")
        return 1

    for device in devices:
        name = str(device.get("deviceName", "?"))
        marker = " <-- config" if name == config.audio.device else ""
        print(f"  [{int(float(device.get('index', -1)))}] {name}{marker}")

    print()
    if config.audio.device is None:
        print("  config/experiment.yaml -> audio.device: null")
        print("  PTB listedeki İLK aygıtı kullanıyor. Kullanılacak aygıtın adını")
        print("  tırnak içinde yazın, örn:")
        print(f'    audio.device: "{devices[0].get("deviceName", "")}"')
    else:
        print(f"  config/experiment.yaml -> audio.device: {config.audio.device!r}")
    print()
    print("  Tek seferlik denemek için config'i değiştirmeden:")
    print('    python tools/timing_selftest.py --demo --device "<aygıt adı>"')
    return 0


def _summarise(name: str, values: list[float], unit: str = "ms") -> None:
    if not values:
        print(f"  {name}: ölçüm yok")
        return
    spread = statistics.stdev(values) if len(values) > 1 else 0.0
    print(
        f"  {name}: ort {statistics.fmean(values):+.3f} {unit}, "
        f"SD {spread:.3f} {unit}, "
        f"maks |{max(abs(v) for v in values):.3f}| {unit}, n={len(values)}"
    )


# ------------------------------------------------------------------ level 1


def level_1(config: ExperimentConfig, n_trials: int) -> int:
    """Backend, refresh grid and audio scheduling — no hardware required."""
    problems: list[str] = []

    _rule("Kademe 1 — donanımsız kontroller")
    speaker = _open_audio(config)
    print("  Ses backend'i    : ptb (doğrulandı)")
    print(f"  Aygıt            : {getattr(speaker, 'name', '?')}")
    print(f"  Örnekleme hızı   : {int(getattr(speaker, 'sampleRateHz', 0))} Hz")
    print(f"  Kanal            : {int(getattr(speaker, 'channels', 0))}")
    print(f"  Gecikme sınıfı   : {config.timing.audio_latency_mode}")
    if config.audio.device is None:
        print("  NOT: audio.device boş — PTB bulduğu ilk aygıtı kullanıyor.")
        print("       Veri toplamadan önce config'e aygıt adı yazılmalı.")

    status = getattr(getattr(speaker, "stream", None), "status", None)
    if isinstance(status, dict):
        for key in ("PredictedLatency", "OutputDeviceLatency", "LatencyBias"):
            if key in status:
                print(f"  {key:<17}: {float(status[key]) * 1000:.3f} ms")
        if not float(status.get("PredictedLatency", 0.0)):
            print(
                "  NOT: PTB bu aygıt için çıkış gecikmesi bildirmiyor. Mutlak\n"
                "       A/V gecikmesi yalnızca fotodiyot ölçümüyle bilinebilir."
            )

    win = open_window(config.display)
    try:
        refresh_hz = measure_refresh_hz(win)
        print(f"  Ölçülen yenileme : {refresh_hz:.3f} Hz "
              f"(kare {1000.0 / refresh_hz:.3f} ms)")
        if not check_refresh_hz(refresh_hz, config.display):
            problems.append(
                "Ölçülen yenileme hızı config'teki expected_refresh_hz ile uyuşmuyor"
            )

        params = _timing_params(config, refresh_hz)
        import psychtoolbox as ptb

        _rule("Flip zamanlaması")
        flip_errors: list[float] = []
        for _ in range(n_trials):
            now = float(ptb.GetSecs())
            earliest = float(win.getFutureFlipTime(clock="ptb"))
            plan = plan_presentation(
                earliest_flip_s=earliest, now_s=now, params=params, with_audio=False
            )
            while float(win.getFutureFlipTime(clock="ptb")) < (
                plan.video_flip_s - params.frame_period_s / 2
            ):
                win.flip()
            win.flip()
            flip_errors.append((float(ptb.GetSecs()) - plan.video_flip_s) * 1000.0)
        _summarise("Hedeften sapma", flip_errors)
        if max(abs(value) for value in flip_errors) > params.frame_period_s * 1000.0:
            problems.append("Flip hedefinden bir kareden fazla sapma var (vsync?)")

        _rule("Ses planlaması")
        snd = make_sound(_click_stimulus(config.audio.sample_rate), speaker)
        audio_errors: list[float] = []
        unreported = 0
        time_failed = 0
        total_xruns = 0
        for _ in range(n_trials):
            now = float(ptb.GetSecs())
            earliest = float(win.getFutureFlipTime(clock="ptb"))
            plan = plan_presentation(
                earliest_flip_s=earliest, now_s=now, params=params, with_audio=True
            )
            assert plan.audio_start_s is not None
            snd.play(when=plan.audio_start_s)
            while float(ptb.GetSecs()) < plan.audio_start_s + 0.05:
                win.flip()
            reported = reported_start_time(snd)
            if reported is None:
                unreported += 1
            else:
                audio_errors.append((reported - plan.audio_start_s) * 1000.0)
            failed, xruns = playback_health(snd)
            time_failed += failed
            total_xruns += xruns
            snd.stop()

        _summarise("Bildirilenden sapma", audio_errors)
        print(f"  Zaman bildirmeyen: {unreported}/{n_trials}")
        print(f"  Kaçırılan zamanlama (TimeFailed): {time_failed}")
        print(f"  Buffer under-run (XRuns)        : {total_xruns}")
        print(
            "  NOT: PTB'nin bildirdiği StartTime, istenen zamanla birebir aynı\n"
            "       gelebilir (bu makinede öyle) — yani bağımsız bir ölçüm\n"
            "       değil. Onset'i gerçekten doğrulayan şey kademe 2 ve 3."
        )
        if unreported == n_trials:
            problems.append(
                "PTB hiçbir ses için başlangıç zamanı bildirmedi — kayda "
                "planlanan zaman yazılır"
            )
        if time_failed or total_xruns:
            problems.append(
                f"Ses zamanlaması bozuldu: TimeFailed {time_failed}, XRuns "
                f"{total_xruns}. Aygıt paylaşımlı modda ya da sistem yükü fazla."
            )
        if audio_errors and max(abs(value) for value in audio_errors) > 5.0:
            problems.append("Bir ses bildirilen zamandan 5 ms'ten fazla saptı")
    finally:
        win.close()

    return _verdict(problems)


# ------------------------------------------------------------------ level 2


def level_2_play(
    config: ExperimentConfig, n_clicks: int, interval_s: float, out_path: Path
) -> int:
    """Play a click train and write down when each click was scheduled.

    No window: level 2 measures the audio path alone, and a window would drag
    the display's timing into a number that is meant to be about the sound
    card.  The screen side is level 3's job.
    """
    _rule("Kademe 2 — klik dizisi")
    speaker = _open_audio(config)
    snd = make_sound(_click_stimulus(config.audio.sample_rate), speaker)

    import psychtoolbox as ptb

    print(f"  {n_clicks} klik, {interval_s * 1000:.0f} ms aralıkla.")
    print("  Kaydı ŞİMDİ başlatın, sonra Enter'a basın.")
    input()

    start = float(ptb.GetSecs()) + 2.0  # a gap at the head of the recording
    scheduled = [start + index * interval_s for index in range(n_clicks)]
    for target in scheduled:
        snd.stop()
        snd.play(when=target)
        ptb.WaitSecs(max(0.0, target + interval_s * 0.8 - float(ptb.GetSecs())))
    snd.stop()
    ptb.WaitSecs(2.0)

    # Relative times: the recorder's clock starts wherever the operator pressed
    # record, so only the pattern is comparable — and small numbers keep the
    # sub-millisecond resolution out of floating-point rounding.
    relative = [value - scheduled[0] for value in scheduled]
    out_path.write_text(
        json.dumps(
            {
                "n_clicks": n_clicks,
                "interval_s": interval_s,
                "sample_rate": config.audio.sample_rate,
                "scheduled_relative_s": relative,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n  Planlanan zamanlar yazıldı: {out_path}")
    print("  Kaydı durdurun, 24-bit PCM WAV olarak kaydedin, sonra:")
    print("    python tools/timing_selftest.py --level 2 --analyze <kayit.wav>")
    return 0


def level_2_analyze(wav_path: Path, times_path: Path, channel: int) -> int:
    """Measure the jitter of a recorded click train."""
    from mcgurk.stimuli.wavfile import read as read_wav

    _rule("Kademe 2 — jitter analizi")
    try:
        payload = json.loads(times_path.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"HATA: planlanan zamanlar okunamadı: {times_path} ({exc})")
        print("      Önce --level 2 --play çalıştırın.")
        return 1

    data, sample_rate = read_wav(wav_path)
    signal = data if data.ndim == 1 else data[:, channel]
    print(f"  Kayıt            : {wav_path.name}, {sample_rate} Hz, "
          f"{signal.size / sample_rate:.1f} s, kanal {channel}")
    peak = float(np.max(np.abs(signal))) if signal.size else 0.0
    print(f"  Tepe             : {peak:.4f}")
    if peak > 0.99:
        print("  UYARI: kayıt kırpıyor — giriş kazancını düşürün")
    if peak < 0.01:
        print("  UYARI: kayıt çok zayıf — giriş kazancını artırın")

    scheduled = np.asarray(payload["scheduled_relative_s"], dtype=np.float64)
    try:
        report = analyse_click_train(signal, sample_rate, scheduled)
    except LoopbackError as exc:
        print(f"HATA: {exc}")
        return 1

    print(f"  Klik             : {report.n_detected}/{report.n_scheduled}")
    print(f"  Sabit gecikme    : {report.offset_mean_ms:+.3f} ms "
          "(kayıt başlangıcı + çıkış/giriş gecikmesi — tek başına anlamlı değil)")
    print(f"  Jitter (SD)      : {report.jitter_sd_ms:.3f} ms")
    print(f"  Maks sapma       : {report.max_abs_deviation_ms:.3f} ms")
    print(f"  Değerlendirme    : {report.verdict}")
    return 0 if report.acceptable else 1


# ------------------------------------------------------------------ level 3


def level_3() -> int:
    """Point at the photodiode procedure; do not reimplement it."""
    _rule("Kademe 3 — fotodiyot ölçümü (kod bittikten sonra)")
    print(
        "Bu ölçüm bu araçta gerçeklenmiyor. Scriptler ve yordam\n"
        "  docs/01_av_gecikme_olcumu.md\n"
        "içinde: olcum_flash.py uyaranı üretir, analiz_gecikme.py kaydı çözer.\n"
        "\n"
        "Neden burada değil: ölçülen D tek bir sayıdır ve config'e yazılır;\n"
        "modüllerin mimarisini etkilemez. Bu yüzden tüm kod bittikten sonra,\n"
        "deneyin çalışacağı makinede bir kez yapılır (steps.md §C Adım 3).\n"
        "\n"
        "Sonuç şu iki alana yazılır:\n"
        "  timing.system_av_offset_ms: <ölçülen D>\n"
        "  timing.measured_on:         <YYYY-AA-GG>\n"
        "İkisi birlikte zorunludur — tarihi olmayan bir ölçüm doğrulanamaz,\n"
        "config bunu reddediyor.\n"
        "\n"
        "Doğrulama süpürmesini (§9) atlamayın: yalnızca SOA=0'da ölçmek,\n"
        "negatif SOA'da planlama penceresinin yetmediğini gizler.\n"
        "\n"
        "Bu projeye özel not: doğrulama koşusuna konuşmacı 2'nin bir uyumsuz\n"
        "denemesini de ekleyin. O kaydın token'ları arasında 248 ms doğal\n"
        "patlama farkı var (Adım 2) ve hizalama, kaynak kaydın kendi içinde\n"
        "senkron olduğu varsayımına dayanıyor; fotodiyot bunu doğrudan sınar."
    )
    return 0


# -------------------------------------------------------------------- demo


def demo(config: ExperimentConfig) -> int:
    """Present a few real trials and print what the engine recorded."""
    _rule("Demo — hazırlanmış uyaranlarla gerçek denemeler")
    stimuli_root = resolve_path(_PROJECT_ROOT, config.paths.stimuli)
    manifest = manifest_module.load(stimuli_root)
    speaker_id = config.modules.mcgurk.speaker_id

    video = manifest.video(speaker_id, "ga")
    fused = manifest.token(speaker_id, "ga", "ba")
    congruent_video = manifest.video(speaker_id, "ba")
    congruent = manifest.token(speaker_id, "ba", "ba")

    specs = [
        TrialSpec(
            label="AV uyumlu (SOA 0)",
            video_path=congruent_video.file.resolve(stimuli_root),
            video_burst_s=congruent_video.burst_time_s,
            audio_path=congruent.file.resolve(stimuli_root),
            audio_burst_s=congruent.burst_time_s,
            ear="both",
        ),
        TrialSpec(
            label="McGurk (Vis-ga / Aud-ba), sol kulak",
            video_path=video.file.resolve(stimuli_root),
            video_burst_s=video.burst_time_s,
            audio_path=fused.file.resolve(stimuli_root),
            audio_burst_s=fused.burst_time_s,
            ear="left",
        ),
        TrialSpec(
            label="AV, SOA -200 ms (ses önce)",
            video_path=congruent_video.file.resolve(stimuli_root),
            video_burst_s=congruent_video.burst_time_s,
            audio_path=congruent.file.resolve(stimuli_root),
            audio_burst_s=congruent.burst_time_s,
            ear="both",
            nominal_soa_ms=-200.0,
        ),
        TrialSpec(
            label="AV, SOA +200 ms (ses sonra)",
            video_path=congruent_video.file.resolve(stimuli_root),
            video_burst_s=congruent_video.burst_time_s,
            audio_path=congruent.file.resolve(stimuli_root),
            audio_burst_s=congruent.burst_time_s,
            ear="both",
            nominal_soa_ms=200.0,
        ),
        TrialSpec(
            label="A-only, sağ kulak",
            audio_path=congruent.file.resolve(stimuli_root),
            audio_burst_s=congruent.burst_time_s,
            ear="right",
        ),
        TrialSpec(
            label="V-only",
            video_path=congruent_video.file.resolve(stimuli_root),
            video_burst_s=congruent_video.burst_time_s,
        ),
    ]

    speaker = _open_audio(config)
    win = open_window(config.display)
    try:
        refresh_hz = measure_refresh_hz(win)
        check_refresh_hz(refresh_hz, config.display)
        params = _timing_params(config, refresh_hz)
        presenter = AVPresenter(
            win,
            params,
            speaker=speaker,
            calibration=_calibration(config),
            sample_rate=config.audio.sample_rate,
            alignment_tolerance_ms=config.stimulus_prep.burst.alignment_tolerance_ms,
            fixation=make_fixation(win),
        )

        rows: list[tuple[str, str, str, str, str]] = []
        for spec in specs:
            prepared = presenter.prepare(spec)
            try:
                record = presenter.present(prepared)
            finally:
                presenter.release(prepared)
            rows.append(
                (
                    spec.label,
                    spec.mode,
                    "—" if record.actual_soa_ms is None else f"{record.actual_soa_ms:+.1f}",
                    "—" if record.nominal_soa_ms is None else f"{record.nominal_soa_ms:+.1f}",
                    f"{record.dropped_frames} / {record.max_frame_interval_ms:.1f} ms",
                )
            )
            if prepared.sound is None:
                audio_state = "ses yok"
            elif record.audio_onset_reported:
                audio_state = "ses onset bildirildi"
            else:
                audio_state = "ses onset PLANLANAN"
            print(
                f"  {spec.label:<36} mod {spec.mode:<2} "
                f"pay {record.lead_frames:>2} kare  "
                f"flip sapması {record.flip_error_ms or 0.0:+.2f} ms  "
                f"{audio_state}"
            )
    except AbortSession:
        print("\n  Demo kullanıcı tarafından kesildi (ESC).")
        return 0
    finally:
        win.close()

    _rule("Özet")
    print(f"  {'Deneme':<38}{'Mod':<5}{'Gerçekleşen':>12}{'Nominal':>10}"
          f"{'Düşen kare / maks':>22}")
    for label, mode, actual, nominal, frames in rows:
        print(f"  {label:<38}{mode:<5}{actual:>12}{nominal:>10}{frames:>22}")
    return 0


# ------------------------------------------------------------------ plumbing


def _verdict(problems: list[str]) -> int:
    _rule("Sonuç")
    if not problems:
        print("  Tüm kontroller geçti.")
        return 0
    for problem in problems:
        print(f"  SORUN: {problem}")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="A/V zamanlama öz-testi (steps.md §C Adım 3)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", type=Path, default=None, help="config dosyası")
    parser.add_argument("--level", type=int, choices=(1, 2, 3), default=None)
    parser.add_argument("--demo", action="store_true", help="gerçek uyaranlarla sunum")
    parser.add_argument(
        "--devices", action="store_true", help="ses çıkış aygıtlarını listele ve çık"
    )
    parser.add_argument(
        "--device",
        default=None,
        help="bu koşu için audio.device'ı ez (config değişmez)",
    )
    parser.add_argument("--n", type=int, default=DEFAULT_CLICKS, help="deneme/klik sayısı")
    parser.add_argument("--play", action="store_true", help="kademe 2: klik dizisini çal")
    parser.add_argument("--analyze", type=Path, default=None, help="kademe 2: kaydı çöz")
    parser.add_argument(
        "--times",
        type=Path,
        default=None,
        help=f"kademe 2: planlanan zamanlar (varsayılan: <logs>/{SCHEDULE_FILE})",
    )
    parser.add_argument("--channel", type=int, default=0, help="kademe 2: analiz kanalı")
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_CLICK_INTERVAL_S,
        help="kademe 2: klik aralığı (s)",
    )
    args = parser.parse_args(argv)

    if args.level is None and not args.demo and not args.devices:
        parser.error("--level 1|2|3, --demo veya --devices verin")

    try:
        config = load_config(args.config, project_root=_PROJECT_ROOT)
    except ConfigError as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1

    setup_logging(
        resolve_path(_PROJECT_ROOT, config.paths.logs),
        console_level=config.logging.console_level,
        file_level=config.logging.file_level,
    )

    if args.device is not None:
        # Assignment goes through the schema, so a bad value fails here rather
        # than at the device layer.  The file on disk is untouched: this is for
        # trying a device out, not for recording which one the study uses.
        config.audio.device = args.device
        print(f"Aygıt bu koşu için ezildi: {args.device!r} (config değişmedi)")

    if args.devices:
        return list_devices(config)

    times_path = args.times or (
        resolve_path(_PROJECT_ROOT, config.paths.logs) / SCHEDULE_FILE
    )

    if args.level == 3:
        return level_3()
    if args.level == 2:
        if args.analyze is not None:
            return level_2_analyze(args.analyze, times_path, args.channel)
        if args.play:
            return level_2_play(config, args.n, args.interval, times_path)
        parser.error("kademe 2 için --play veya --analyze <kayit.wav> verin")

    status = 0
    if args.level == 1:
        status = level_1(config, args.n)
    if args.demo:
        status = demo(config) or status
    return status


if __name__ == "__main__":
    sys.exit(main())
