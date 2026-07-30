"""Stimulus loading and presentation helpers for PsychoPy.

Audio-video synchronisation strategy
-------------------------------------
``MovieStim`` (ffpyplayer backend) plays audio through SDL2, which adds
noticeable latency on Windows.  It cannot be turned off: in PsychoPy 2026.1
``MovieStim.__init__`` overwrites the caller's ``noAudio`` argument —

    if audioLib is None and self._movieLib == 'ffpyplayer':
        self._audioLib = 'sdl2'
        self._noAudio = False        # <- our noAudio=True is discarded
    ...
    if self._audioLib != 'sdl2':
        raise MovieAudioError(...)   # <- and any other value is rejected

so passing ``audioLib`` does not help either.  The only reliable way to keep
SDL2 silent is to hand MovieStim a file that has no audio stream at all.
Hence:

1. Produce a copy of the video with the audio stream stripped (``-an``) and
   give *that* to ``MovieStim``.
2. Extract the audio track to a wav separately.
3. Play the wav through ``sound.Sound`` on the ptb backend, scheduled against
   the window's flip clock.
4. Start video and audio together in ``present_video``.

PsychoPy still logs "Using `sdl2` for audio playback via `ffpyplayer`" when a
MovieStim is created.  That warning is unavoidable and harmless here — the
file it was handed carries no audio.  ``tests/test_silent_video.py`` asserts
the stripped copies really are silent.

The extracted wavs and silent videos are cached per source path for the
lifetime of the process and cleaned up on exit.
"""

import atexit
import hashlib
import logging
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from psychopy import core, event, sound, visual
from psychopy import logging as psychopy_logging

logger = logging.getLogger(__name__)

# Key that aborts the session.  Live during every wait loop, not just while a
# response is being collected.
ABORT_KEY = "escape"


class AbortSession(Exception):
    """Raised when the operator aborts the session with the abort key.

    Carries no message: it is control flow, not an error.  The engine catches
    it, marks the session 'aborted' and keeps everything recorded so far.
    """


def _get_ffmpeg() -> str:
    """Return path to ffmpeg binary.

    Prefers the system ffmpeg (PATH), falls back to the binary bundled with
    imageio-ffmpeg (a pinned dependency in requirements.txt).
    """
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise RuntimeError(
            "ffmpeg bulunamadı ve imageio-ffmpeg kurulu değil.\n"
            "Ya ffmpeg'i PATH'e ekleyin ya da 'pip install -r requirements.txt' çalıştırın."
        ) from exc
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    logger.debug("Sistem ffmpeg'i yok, imageio-ffmpeg kullanılıyor: %s", ffmpeg_path)
    return ffmpeg_path


def require_ptb_backend() -> None:
    """Fail loudly unless the audio backend in use is Psychtoolbox.

    Only the ptb backend can schedule playback against a future flip time
    (``Sound.play(when=...)``).  Any other backend degrades A/V sync to
    "whenever the call happens to return", and the resulting offset would be
    invisible in the recorded data — see the method document §5.3.

    API note: PsychoPy 2026.1 moved backend selection from
    ``prefs.hardware['audioLib']`` / ``sound.audioLib`` to the class attribute
    ``sound.Sound.backend``.  ``sound.audioLib`` no longer exists, so testing
    that attribute would fail here on every run.
    """
    backend_name = getattr(sound.Sound, "backend", None)
    if backend_name != "ptb":
        raise RuntimeError(
            f"Ses backend'i 'ptb' değil (seçili: {backend_name!r}).\n"
            "Deney bu backend ile çalıştırılamaz (A/V senkronu garanti edilemez)."
        )

    # The name being right does not mean the module imports: psychtoolbox is a
    # separate wheel and can be missing or broken.
    try:
        sound.Sound.getBackends()["ptb"].load()
    except (KeyError, ImportError) as exc:
        raise RuntimeError(
            "Psychtoolbox ses backend'i yüklenemedi.\n"
            "'pip install -r requirements.txt' ile kurun; kuruluysa ses "
            "aygıtının başka bir uygulama tarafından kilitlenmediğinden emin "
            "olun.\n"
            f"Ayrıntı: {exc}"
        ) from exc

    logger.info("Ses backend'i doğrulandı: ptb")
    logger.info(
        "Video oynatma sessiz kopyalar üzerinden yapılıyor; MovieStim'in "
        "SDL2 uyarısı bastırılıyor (dosyalarda ses akışı yok)."
    )


@contextmanager
def _quiet_movie_init() -> Iterator[None]:
    """Silence PsychoPy's console during MovieStim construction.

    MovieStim always warns that it is using SDL2 for audio (see the module
    docstring — it cannot be turned off).  The warning is emitted through
    PsychoPy's own logging, not the stdlib one, so a stdlib logger level has
    no effect on it; only ``psychopy.logging.console`` does.

    The window is deliberately narrow — one constructor call — so that later
    warnings that *do* matter, such as dropped frames during presentation,
    still reach the operator.  Errors are unaffected: they raise rather than
    log.
    """
    original_level = psychopy_logging.console.level
    psychopy_logging.console.setLevel(psychopy_logging.ERROR)
    try:
        yield
    finally:
        psychopy_logging.console.setLevel(original_level)

# ---------------------------------------------------------------------------
# Audio extraction cache
# ---------------------------------------------------------------------------

_audio_cache: dict[str, Path] = {}
_silent_video_cache: dict[str, Path] = {}
_noise_wav_cache: dict[str, Path] = {}
_mixed_wav_cache: dict[str, Path] = {}
_temp_dir: Path | None = None

_SR = 48000


def _get_temp_dir() -> Path:
    """Return (and lazily create) a temp directory for extracted wav files."""
    global _temp_dir
    if _temp_dir is None:
        _temp_dir = Path(tempfile.mkdtemp(prefix="mcgurk_audio_"))
        atexit.register(_cleanup_temp_audio)
    return _temp_dir


def _cleanup_temp_audio() -> None:
    """Remove temporary wav files on interpreter exit."""
    if _temp_dir and _temp_dir.exists():
        shutil.rmtree(_temp_dir, ignore_errors=True)


def extract_audio(video_path: Path) -> Path:
    """Extract audio track from *video_path* to a wav file (cached).

    Uses ffmpeg (must be on PATH).  The wav is written to a process-local
    temp directory and reused if the same video is requested again.
    """
    key = str(video_path.resolve())
    if key in _audio_cache:
        return _audio_cache[key]

    temp_dir = _get_temp_dir()
    # Build a unique-enough filename: <speaker_folder>_<video_stem>.wav
    wav_name = f"{video_path.parent.name}_{video_path.stem}.wav"
    wav_path = temp_dir / wav_name

    # If there's a hash collision (unlikely), add a short hash
    if wav_path.exists():
        h = hashlib.md5(key.encode()).hexdigest()[:8]
        wav_name = f"{video_path.parent.name}_{video_path.stem}_{h}.wav"
        wav_path = temp_dir / wav_name

    try:
        subprocess.run(
            [
                _get_ffmpeg(),
                "-i", str(video_path),
                "-vn",                    # no video
                "-acodec", "pcm_s16le",   # 16-bit PCM
                "-ar", "48000",           # 48 kHz (common for ptb)
                "-ac", "2",               # stereo (needed for dichotic)
                str(wav_path),
                "-y",                     # overwrite
            ],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"ffmpeg ses çıkarma hatası ({video_path.name}): {exc.stderr.decode()}"
        ) from exc

    _audio_cache[key] = wav_path
    return wav_path


def _get_noise_wav(noise_file: Path) -> Path:
    """Convert noise file (mp3/wav/…) to 48 kHz stereo PCM wav, cached."""
    key = str(noise_file.resolve())
    if key in _noise_wav_cache:
        return _noise_wav_cache[key]

    temp_dir = _get_temp_dir()
    out_path = temp_dir / f"noise_{noise_file.stem}.wav"
    try:
        subprocess.run(
            [
                _get_ffmpeg(),
                "-i", str(noise_file),
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", str(_SR),
                "-ac", "2",
                str(out_path),
                "-y",
            ],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"ffmpeg gürültü dönüştürme hatası ({noise_file.name}): {exc.stderr.decode()}"
        ) from exc

    _noise_wav_cache[key] = out_path
    return out_path


def mix_noise_into_audio(speech_wav: Path, noise_file: Path, snr_db: float) -> Path:
    """Mix *speech_wav* with *noise_file* at *snr_db* dB SNR, return mixed wav (cached).

    The mixed wav is written once to the process temp directory and reused on
    subsequent calls with the same arguments.
    """
    cache_key = f"{speech_wav}|{noise_file}|{snr_db}"
    if cache_key in _mixed_wav_cache:
        return _mixed_wav_cache[cache_key]

    import numpy as np
    from scipy.io import wavfile

    noise_wav = _get_noise_wav(noise_file)

    _, speech_raw = wavfile.read(speech_wav)
    speech = speech_raw.astype(np.float32)
    if speech.ndim == 1:
        speech = np.stack([speech, speech], axis=1)

    _, noise_raw = wavfile.read(noise_wav)
    noise = noise_raw.astype(np.float32)
    if noise.ndim == 1:
        noise = np.stack([noise, noise], axis=1)

    # Loop noise to cover full speech length
    n = len(speech)
    repeats = n // len(noise) + 1
    noise = np.tile(noise, (repeats, 1))[:n]

    # Scale noise to achieve desired SNR: SNR = 20*log10(rms_speech / rms_noise)
    speech_rms = np.sqrt(np.mean(speech ** 2) + 1e-10)
    noise_rms  = np.sqrt(np.mean(noise  ** 2) + 1e-10)
    target_noise_rms = speech_rms / (10 ** (snr_db / 20.0))
    noise_scaled = noise * (target_noise_rms / noise_rms)

    mixed = speech + noise_scaled
    peak = np.abs(mixed).max()
    if peak > 32700:
        mixed = mixed * (32700.0 / peak)
    mixed = mixed.astype(np.int16)

    temp_dir = _get_temp_dir()
    h = hashlib.md5(cache_key.encode()).hexdigest()[:8]
    out_path = temp_dir / f"mixed_{speech_wav.stem}_{h}.wav"
    wavfile.write(out_path, _SR, mixed)

    _mixed_wav_cache[cache_key] = out_path
    return out_path


def extract_silent_video(video_path: Path) -> Path:
    """Return a copy of *video_path* with the audio track stripped (cached).

    noAudio=True and setVolume(0) are both ignored by some ffpyplayer builds
    on Windows.  The only reliable way to guarantee silence is to give
    MovieStim a video file that has no audio stream at all.
    """
    key = str(video_path.resolve())
    if key in _silent_video_cache:
        return _silent_video_cache[key]

    temp_dir = _get_temp_dir()
    out_name = f"{video_path.parent.name}_{video_path.stem}_silent.mp4"
    out_path = temp_dir / out_name

    if out_path.exists():
        h = hashlib.md5(key.encode()).hexdigest()[:8]
        out_name = f"{video_path.parent.name}_{video_path.stem}_{h}_silent.mp4"
        out_path = temp_dir / out_name

    try:
        subprocess.run(
            [
                _get_ffmpeg(),
                "-i", str(video_path),
                "-an",          # strip audio stream
                "-vcodec", "copy",
                str(out_path),
                "-y",
            ],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"ffmpeg sessiz video hatası ({video_path.name}): {exc.stderr.decode()}"
        ) from exc

    _silent_video_cache[key] = out_path
    return out_path


# ---------------------------------------------------------------------------
# Stimulus creation helpers
# ---------------------------------------------------------------------------


def create_fixation_cross(win: visual.Window, config: dict[str, Any]) -> visual.ShapeStim:
    """Create a fixation cross stimulus."""
    fix_config = config.get("fixation", {})
    size = fix_config.get("size", 0.05)
    color = fix_config.get("color", [-1, -1, -1])
    line_width = fix_config.get("line_width", 3)

    return visual.ShapeStim(
        win,
        vertices="cross",
        size=(size, size),
        lineColor=color,
        fillColor=color,
        lineWidth=line_width,
    )


def load_audio_stimulus(
    audio_path: Path,
    noise_file: Path | None = None,
    snr_db: float | None = None,
) -> sound.Sound:
    """Load a standalone audio stimulus — no video, no MovieStim.

    Used by the sections that present sound with nothing to look at
    (``audio_only``, ``dichotic``).  Wrapping those in a hidden movie would tie
    the trial's end time to a video stream's frame grid; here the sound is the
    only thing being timed.

    A ``.wav`` is used as-is.  Any other container (an mp4 the audio has to be
    lifted out of) goes through the cached ffmpeg extraction path.
    """
    wav_path = (
        audio_path
        if audio_path.suffix.lower() == ".wav"
        else extract_audio(audio_path)
    )
    if noise_file is not None and snr_db is not None:
        wav_path = mix_noise_into_audio(wav_path, noise_file, snr_db)
    return sound.Sound(str(wav_path))


def load_video_stimulus(
    win: visual.Window,
    video_path: Path,
    with_audio: bool = True,
    noise_file: Path | None = None,
    snr_db: float | None = None,
) -> tuple[visual.MovieStim, sound.Sound | None]:
    """Load a video stimulus and (optionally) its audio track.

    The video is **always** loaded with embedded audio disabled.  When
    *with_audio* is True the audio track is extracted to a wav file and
    returned as a ``sound.Sound`` object that uses PsychoPy's configured
    audio backend (ptb preferred) for precise timing.

    When *noise_file* and *snr_db* are provided the extracted speech audio is
    mixed with the noise file at the given SNR before creating the Sound object.
    The mixed wav is cached so repeated trials incur no extra I/O cost.

    Returns:
        ``(movie, audio)`` — *audio* is ``None`` when *with_audio* is False.
    """
    # Always give MovieStim a silent video: PsychoPy overwrites the noAudio
    # argument and hard-wires ffpyplayer to SDL2 (see module docstring), so a
    # file with no audio stream is the only thing that keeps SDL2 quiet.
    silent_path = extract_silent_video(video_path)

    with _quiet_movie_init():
        movie = visual.MovieStim(
            win,
            str(silent_path),
            noAudio=True,
            loop=False,
        )
    audio_obj = None
    if with_audio:
        wav_path = extract_audio(video_path)
        if noise_file is not None and snr_db is not None:
            wav_path = mix_noise_into_audio(wav_path, noise_file, snr_db)
        audio_obj = sound.Sound(str(wav_path))
    return movie, audio_obj


def check_abort() -> None:
    """Raise AbortSession if the operator has pressed the abort key.

    Called from every wait loop, so the session can be stopped at any point of
    a trial — during the fixation cross, mid-stimulus, or while the response
    screen is up — not only when a response is being awaited.
    """
    if event.getKeys(keyList=[ABORT_KEY]):
        raise AbortSession()


def present_fixation(
    win: visual.Window,
    fixation: visual.ShapeStim,
    duration_ms: int,
):
    """Present the fixation cross for *duration_ms*, abortable throughout.

    Held with a flip loop rather than ``core.wait`` so the duration lands on
    the refresh grid and the abort key stays live for the whole interval.
    """
    duration_sec = duration_ms / 1000.0
    timer = core.Clock()
    while timer.getTime() < duration_sec:
        check_abort()
        fixation.draw()
        win.flip()


def present_audio_only(
    win: visual.Window,
    audio: sound.Sound,
    fixation: visual.ShapeStim,
    clock: core.Clock,
) -> float:
    """Play *audio* with only the fixation cross on screen.

    There is no video to step through, so the trial lasts exactly as long as
    the sound file.  The wait is a flip loop rather than ``core.wait`` so the
    abort key remains live while the stimulus plays.

    Returns:
        Time (on the provided clock) when playback finished.
    """
    fixation.draw()
    # Schedule first, flip second — getFutureFlipTime targets the flip that
    # the following call performs, and that is the onset the sound is aligned
    # to.  No fallback: an unschedulable onset means invalid trial timing.
    audio.play(when=win.getFutureFlipTime(clock="ptb"))
    win.flip()

    duration = audio.getDuration()
    timer = core.Clock()
    try:
        while timer.getTime() < duration:
            check_abort()
            fixation.draw()
            win.flip()
    finally:
        audio.stop()

    win.flip()  # clear the fixation cross before the response screen
    return clock.getTime()


def present_video(
    win: visual.Window,
    movie: visual.MovieStim,
    clock: core.Clock,
    audio: sound.Sound | None = None,
) -> float:
    """Present a video stimulus and return the timestamp when it ends.

    If *audio* is provided it is started on the same frame as the video
    so that A/V sync is governed by PsychoPy's audio backend (ptb) rather
    than ffpyplayer's SDL2 path.

    Returns:
        Time (on the provided clock) when the video finished.
    """
    # Silence movie-level SDL2 audio right before play — ffpyplayer may
    # reset volume on play(), so this must happen here, not just at load time.
    movie.setVolume(0)

    # Schedule audio to start on the exact next flip so video frame 1 and
    # audio onset land on the same display refresh.  No fallback: if this
    # cannot be scheduled the trial timing is invalid, so fail loudly rather
    # than collect unusable data.
    if audio is not None:
        audio.play(when=win.getFutureFlipTime(clock="ptb"))

    movie.play()

    try:
        while not movie.isFinished:
            check_abort()
            movie.draw()
            win.flip()
    finally:
        movie.stop()
        if audio is not None:
            audio.stop()

    win.flip()  # clear screen after video
    return clock.getTime()


def create_response_screen(
    win: visual.Window,
    syllables: list[str],
    key_map: dict[str, str],
) -> list[dict]:
    """Create response option stimuli with colored backgrounds.

    Each option is a colored rounded rectangle with text inside.
    Returns a list of dicts with 'bg' and 'text' keys.
    """
    # Colors for each option button (PsychoPy color space [-1, 1])
    button_colors = [
        [-0.2, 0.4, -0.2],   # green
        [0.2, 0.2, 0.8],     # blue
        [0.8, 0.2, 0.2],     # red
        [0.6, 0.4, -0.2],    # orange
        [0.5, -0.2, 0.6],    # purple
    ]

    n = len(syllables)
    spacing = 0.3
    start_x = -spacing * (n - 1) / 2
    button_width = 0.22
    button_height = 0.1

    stims = []
    for i, syl in enumerate(syllables):
        key = key_map.get(syl, str(i + 1))
        pos = (start_x + i * spacing, -0.3)
        bg_color = button_colors[i % len(button_colors)]

        bg = visual.Rect(
            win,
            width=button_width,
            height=button_height,
            pos=pos,
            fillColor=bg_color,
            lineColor=[c + 0.2 for c in bg_color],
            lineWidth=2,
        )

        text = visual.TextStim(
            win,
            text=f"[{key}] {syl.upper()}",
            pos=pos,
            height=0.05,
            color=[1, 1, 1],
            bold=True,
        )
        stims.append({"bg": bg, "text": text})
    return stims


def present_response_screen(
    win: visual.Window,
    response_stims: list[dict],
    prompt: str = "Ne duydunuz?",
    trial_info: str = "",
) -> float:
    """Draw the response options and return the time they appeared.

    Returns:
        Timestamp (from the window's clock) when options were shown.
    """
    prompt_stim = visual.TextStim(
        win, text=prompt, pos=(0, 0.1), height=0.06, color=[1, 1, 1]
    )
    prompt_stim.draw()
    for stim in response_stims:
        stim["bg"].draw()
        stim["text"].draw()
    # Trial info (top-right) and end-test hint (bottom-right)
    if trial_info:
        info_stim = visual.TextStim(
            win, text=trial_info, pos=(0, 0.4), height=0.03,
            color=[-0.2, -0.2, -0.2],
        )
        info_stim.draw()
    end_hint = visual.TextStim(
        win, text="[ESC] Testi Bitir", pos=(0, -0.45), height=0.03,
        color=[-0.2, -0.2, -0.2],
    )
    end_hint.draw()
    win.flip()
    return core.getTime()
