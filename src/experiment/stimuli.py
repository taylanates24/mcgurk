"""Stimulus loading and presentation helpers for PsychoPy.

Audio-video synchronisation strategy
-------------------------------------
PsychoPy's ``MovieStim`` (ffpyplayer backend) plays audio through SDL2,
which introduces noticeable latency on Windows.  To achieve precise A/V
sync we:

1. **Always** create ``MovieStim`` with ``noAudio=True``.
2. Extract the audio track from the mp4 to a temporary wav via *ffmpeg*.
3. Play the wav through ``sound.Sound`` (ptb / sounddevice backend) which
   has sub-millisecond timing control.
4. Start video and audio together in ``present_video``.

The extracted wavs are cached per video path for the lifetime of the
process and cleaned up on exit.
"""

import atexit
import hashlib
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

from psychopy import visual, core, sound


def _get_ffmpeg() -> str:
    """Return path to ffmpeg binary.

    Prefers the system ffmpeg (PATH), falls back to the binary bundled with
    imageio-ffmpeg (installed as a PsychoPy dependency).
    """
    import shutil as _shutil
    system_ffmpeg = _shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    raise RuntimeError(
        "ffmpeg bulunamadı. Lütfen ffmpeg'in PATH'te olduğundan emin olun."
    )

logger = logging.getLogger(__name__)

# Suppress the sdl2 A/V sync warning — we no longer use sdl2 for audio,
# but MovieStim still logs the warning during initialisation.
logging.getLogger("psychopy.visual.movies").setLevel(logging.ERROR)

# ---------------------------------------------------------------------------
# Audio extraction cache
# ---------------------------------------------------------------------------

_audio_cache: dict[str, Path] = {}
_silent_video_cache: dict[str, Path] = {}
_temp_dir: Optional[Path] = None


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
        )

    _audio_cache[key] = wav_path
    return wav_path


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
        )

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


def load_video_stimulus(
    win: visual.Window, video_path: Path, with_audio: bool = True
) -> tuple[visual.MovieStim, Optional[sound.Sound]]:
    """Load a video stimulus and (optionally) its audio track.

    The video is **always** loaded with embedded audio disabled.  When
    *with_audio* is True the audio track is extracted to a wav file and
    returned as a ``sound.Sound`` object that uses PsychoPy's configured
    audio backend (ptb preferred) for precise timing.

    Returns:
        ``(movie, audio)`` — *audio* is ``None`` when *with_audio* is False.
    """
    if not with_audio:
        # noAudio=True and setVolume(0) are both ignored by some ffpyplayer
        # builds on Windows.  Strip the audio stream at the file level so
        # MovieStim literally has nothing to play.
        video_path = extract_silent_video(video_path)

    movie = visual.MovieStim(
        win,
        str(video_path),
        noAudio=True,   # always mute embedded SDL2 audio
        loop=False,
    )
    audio_obj = None
    if with_audio:
        wav_path = extract_audio(video_path)
        audio_obj = sound.Sound(str(wav_path))
    return movie, audio_obj


def present_fixation(
    win: visual.Window,
    fixation: visual.ShapeStim,
    duration_ms: int,
):
    """Present fixation cross for specified duration."""
    duration_sec = duration_ms / 1000.0
    fixation.draw()
    win.flip()
    core.wait(duration_sec)


def present_video(
    win: visual.Window,
    movie: visual.MovieStim,
    clock: core.Clock,
    audio: Optional[sound.Sound] = None,
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
    movie.play()
    if audio is not None:
        audio.play()

    while not movie.isFinished:
        movie.draw()
        win.flip()

    win.flip()  # clear screen after video
    video_end_time = clock.getTime()

    # Ensure audio doesn't keep playing if it's slightly longer than video
    if audio is not None:
        audio.stop()

    return video_end_time


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
