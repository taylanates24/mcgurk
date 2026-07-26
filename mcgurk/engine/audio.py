"""Preparing a stimulus WAV for playback: lateralisation and calibration trim.

**No noise mixing happens here.**  steps.md §C Adım 3 lists SNR mixing under
this module, but that was written before Adım 2 existed; the noisy stimuli are
now produced offline and live in ``stimuli/audio_noisy/``.  Mixing at run time
would violate §A.12 and would put a full-file DSP pass inside the inter-trial
interval for no benefit.  ``mcgurk.stimuli.dsp.mix_at_snr`` stays where it is
and is used by the preparation pipeline only.  What is left for run time is
what cannot be baked into a file:

* **lateralisation** — which ear the token goes to is a design factor, so one
  prepared mono file serves both ears;
* **calibration trim** — a per-channel gain from ``02_kalibrasyon.md``, which
  belongs to the machine and the headphones, not to the stimulus.

The array work is pure numpy so it can be tested without a sound card.  Only
``open_speaker`` and ``make_sound`` touch PsychoPy, and they import it lazily.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..config.calibration import Calibration
from ..stimuli.wavfile import WavError
from ..stimuli.wavfile import read as read_wav
from . import EngineError

logger = logging.getLogger(__name__)

#: Ear labels used by ``trials.ear``.  ``both`` is diotic: the same signal in
#: both ears, which is what TBW, oddball and GIN ask for.
EARS = ("left", "right", "both")


class AudioError(EngineError):
    """A stimulus could not be prepared for playback."""


def db_to_gain(db: float) -> float:
    return float(10.0 ** (db / 20.0))


def lateralise(mono: np.ndarray, ear: str) -> np.ndarray:
    """Route a mono signal to one ear.  Returns an ``(n, 2)`` array.

    The unused channel is exactly zero rather than attenuated: the point of
    the manipulation is that the deaf ear receives nothing from the sound card,
    so whatever reaches it did so through the skull (which is what the
    cross-hearing check in Adım 8 measures).
    """
    if ear not in EARS:
        raise AudioError(f"Bilinmeyen kulak: {ear!r} (beklenen: {EARS})")
    if mono.ndim != 1:
        raise AudioError(
            f"Lateralizasyon tek kanallı sinyal bekler, şekil {mono.shape} verildi"
        )

    stereo = np.zeros((mono.size, 2), dtype=np.float64)
    if ear in ("left", "both"):
        stereo[:, 0] = mono
    if ear in ("right", "both"):
        stereo[:, 1] = mono
    return stereo


def apply_trim(stereo: np.ndarray, calibration: Calibration | None) -> np.ndarray:
    """Apply the per-channel calibration trim to an ``(n, 2)`` array.

    ``None`` means no calibration file, which is only legitimate in
    ``development``; the caller logs that once per session rather than once per
    trial.
    """
    if stereo.ndim != 2 or stereo.shape[1] != 2:
        raise AudioError(f"Trim iki kanallı sinyal bekler, şekil {stereo.shape}")
    if calibration is None:
        return stereo

    trimmed = np.empty_like(stereo)
    trimmed[:, 0] = stereo[:, 0] * db_to_gain(calibration.trim_left_db)
    trimmed[:, 1] = stereo[:, 1] * db_to_gain(calibration.trim_right_db)
    return trimmed


def prepare_samples(
    data: np.ndarray,
    *,
    ear: str,
    calibration: Calibration | None = None,
) -> np.ndarray:
    """Turn decoded WAV samples into the ``(n, 2)`` array that gets played.

    Mono input is lateralised.  Stereo input is left alone — a dichotic file
    already carries a different token in each ear, and routing it anywhere
    would destroy exactly the thing it was prepared for.

    Raises:
        AudioError: if the result clips.  A limiter would hide a wrong
            calibration trim, and every level in the study derives from it.
    """
    if ear not in EARS:
        raise AudioError(f"Bilinmeyen kulak: {ear!r} (beklenen: {EARS})")

    if data.ndim == 1:
        stereo = lateralise(data, ear)
    elif data.ndim == 2 and data.shape[1] == 2:
        if ear != "both":
            raise AudioError(
                f"Stereo dosya {ear!r} kulağa yönlendirilemez: dosya zaten iki "
                "kulağa ayrı içerik taşıyor (dikotik). ear='both' olmalı."
            )
        stereo = np.asarray(data, dtype=np.float64)
    else:
        raise AudioError(f"Desteklenmeyen ses şekli: {data.shape}")

    stereo = apply_trim(stereo, calibration)

    peak = float(np.max(np.abs(stereo))) if stereo.size else 0.0
    if peak > 1.0:
        raise AudioError(
            f"Ses kırpıyor (tepe {peak:.4f}) — kalibrasyon trim'i veya uyaran "
            "seviyesi hatalı. Limiter uygulanmıyor: sorun veriye taşınmadan "
            "görünmeli."
        )
    return stereo


@dataclass(frozen=True)
class AudioStimulus:
    """Samples ready to hand to the sound backend, plus what is known of them."""

    path: Path
    #: ``(n, 2)`` float64 in [-1, 1].
    samples: np.ndarray
    sample_rate: int
    #: Acoustic burst inside the file, from the manifest.  The RT reference and
    #: the realised SOA are both measured from it.
    burst_time_s: float
    ear: str

    @property
    def duration_s(self) -> float:
        return float(self.samples.shape[0]) / self.sample_rate


def load_audio(
    path: Path,
    *,
    ear: str,
    burst_time_s: float = 0.0,
    calibration: Calibration | None = None,
    expected_sample_rate: int | None = None,
) -> AudioStimulus:
    """Read a prepared WAV and make it playable.

    Raises:
        AudioError: on a missing or unreadable file, and on a sample rate that
            does not match ``audio.sample_rate``.  Resampling here would be
            run-time DSP (§A.12) and would move every burst time the manifest
            recorded.
    """
    try:
        data, sample_rate = read_wav(path)
    except WavError as exc:
        raise AudioError(str(exc)) from exc

    if expected_sample_rate is not None and sample_rate != expected_sample_rate:
        raise AudioError(
            f"Ses dosyasının örnekleme hızı {sample_rate} Hz, config "
            f"{expected_sample_rate} Hz bekliyor: {path}. Uyaran seti yeniden "
            "hazırlanmalı — çalışma anında yeniden örnekleme yapılmaz (§A.12)."
        )

    samples = prepare_samples(data, ear=ear, calibration=calibration)
    return AudioStimulus(
        path=path,
        samples=samples,
        sample_rate=sample_rate,
        burst_time_s=burst_time_s,
        ear=ear,
    )


# --------------------------------------------------------------- PsychoPy side


def require_ptb_backend() -> None:
    """Fail loudly unless the audio backend in use is Psychtoolbox (§A.2).

    Only PTB can schedule playback against a future flip time
    (``Sound.play(when=...)``).  Any other backend degrades A/V sync to
    "whenever the call happens to return", and the resulting offset would be
    invisible in the recorded data.
    """
    from psychopy import sound

    backend_name = getattr(sound.Sound, "backend", None)
    if backend_name != "ptb":
        raise AudioError(
            f"Ses backend'i 'ptb' değil (seçili: {backend_name!r}).\n"
            "Deney bu backend ile çalıştırılamaz: A/V senkronu garanti edilemez "
            "(§A.2). configure_psychopy() psychopy.sound import'undan önce "
            "çağrıldı mı?"
        )

    # The name being right does not mean the module imports: psychtoolbox is a
    # separate wheel and can be missing or broken.
    try:
        sound.Sound.getBackends()["ptb"].load()
    except (KeyError, ImportError) as exc:
        raise AudioError(
            "Psychtoolbox ses backend'i yüklenemedi.\n"
            "'pip install -r requirements.txt' ile kurun; kuruluysa ses "
            "aygıtının başka bir uygulama tarafından kilitlenmediğinden emin "
            f"olun.\nAyrıntı: {exc}"
        ) from exc

    logger.info("Ses backend'i doğrulandı: ptb")


def open_speaker(
    *,
    device_name: str | None = None,
    latency_class: int = 3,
    sample_rate: int = 48000,
) -> Any:
    """Open the output device with the configured latency class.

    ``timing.audio_latency_mode`` is applied here, not through preferences:
    PsychoPy 2026.1 moved it to ``SpeakerDevice(latencyClass=...)`` and the old
    preference key no longer exists (see ``psychopy_prefs``).  Its default is
    1 — "share the device with the rest of the system" — which is not a
    setting this study can be run at.

    The device's stream rate is checked against ``audio.sample_rate``: PsychoPy
    would otherwise resample every stimulus at load time, silently undoing the
    48 kHz the set was prepared at.

    Raises:
        AudioError: if the device cannot be opened, runs at another rate, or
            is not stereo (lateralisation needs two channels).
    """
    from psychopy.hardware.speaker import SpeakerDevice

    try:
        speaker = SpeakerDevice(name=device_name, latencyClass=latency_class)
    except (ConnectionError, OSError, ValueError, KeyError) as exc:
        raise AudioError(
            f"Ses aygıtı açılamadı (aygıt: {device_name or 'varsayılan'}, "
            f"gecikme sınıfı {latency_class}): {exc}"
        ) from exc

    device_rate = int(getattr(speaker, "sampleRateHz", 0) or 0)
    if device_rate != sample_rate:
        raise AudioError(
            f"Ses aygıtı {device_rate} Hz'de açıldı, config {sample_rate} Hz "
            "istiyor. Windows > Ses > Aygıt özellikleri > Gelişmiş'ten aygıtı "
            f"{sample_rate} Hz'e ayarlayın. Aksi hâlde PsychoPy her uyaranı "
            "yeniden örnekler."
        )

    channels = int(getattr(speaker, "channels", 0) or 0)
    if channels < 2:
        raise AudioError(
            f"Ses aygıtı {channels} kanallı — lateralizasyon iki kanal gerektirir."
        )

    logger.info(
        "Ses aygıtı: %s (%d Hz, %d kanal, gecikme sınıfı %d)",
        getattr(speaker, "name", "?"),
        device_rate,
        channels,
        latency_class,
    )
    return speaker


def make_sound(stimulus: AudioStimulus, speaker: Any = None) -> Any:
    """Build a fully buffered ``sound.Sound`` from *stimulus*.

    ``preBuffer=-1`` loads the whole waveform into memory, so ``present()``
    does no disk I/O (§A.12).  ``sampleRate`` is passed explicitly: without it
    PsychoPy labels the array with the *device's* rate, which plays a 48 kHz
    stimulus at whatever the card happens to run at.
    """
    from psychopy import sound

    return sound.Sound(
        value=stimulus.samples,
        sampleRate=stimulus.sample_rate,
        stereo=True,
        hamming=False,
        preBuffer=-1,
        speaker=speaker,
        autoLog=False,
    )


def reported_start_time(snd: Any) -> float | None:
    """The start time PsychPortAudio reports for *snd*, on the ``ptb`` clock.

    **This is not an independent measurement of the onset.**  Measured on this
    project's machine (WASAPI, latency class 3), ``StartTime`` comes back bit
    for bit equal to ``RequestedStartTime``: with no hardware timestamping the
    device offers (``PredictedLatency`` and ``LatencyBias`` are both 0), PTB has
    nothing to report but the time it was asked for.  On an interface that does
    timestamp its output the two can differ, which is why it is read at all.

    What genuinely verifies the onset is a physical measurement — level 2 of
    ``timing_selftest.py`` for the jitter, the photodiode procedure for the
    absolute offset.  Nothing in software can substitute for either.

    Returns ``None`` when playback has not started or the backend does not
    report it; the caller then records the scheduled time and says so.
    """
    status = getattr(snd, "statusDetailed", None)
    if not isinstance(status, dict):
        return None
    start = status.get("StartTime")
    if start is None:
        return None
    try:
        value = float(start)
    except (TypeError, ValueError):
        return None
    return value if value > 0.0 else None


def playback_health(snd: Any) -> tuple[int, int]:
    """``(time_failed, xruns)`` from the backend's status.

    ``TimeFailed`` counts deadlines PsychPortAudio could not meet and ``XRuns``
    counts buffer under-runs.  Either one during a trial means the sound did
    not come out when it was asked for — the one failure mode the scheduling
    code cannot detect on its own, because from its side everything was
    requested correctly.
    """
    status = getattr(snd, "statusDetailed", None)
    if not isinstance(status, dict):
        return 0, 0
    try:
        return int(float(status.get("TimeFailed", 0))), int(float(status.get("XRuns", 0)))
    except (TypeError, ValueError):
        return 0, 0
