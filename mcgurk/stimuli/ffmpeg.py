"""ffmpeg invocation and media inspection.

``ffprobe`` is deliberately not used: the machine this was developed on has no
system ffmpeg, and the fallback (``imageio-ffmpeg``, a pinned dependency)
ships ffmpeg only.  Everything needed here — stream types, duration, frame
rate, frame count — can be read from ffmpeg's own stderr, so requiring a
second binary would buy nothing and break the fallback.
"""

from __future__ import annotations

import functools
import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import StimulusError

logger = logging.getLogger(__name__)

_TIMEOUT_S = 300


class FFmpegError(StimulusError):
    """ffmpeg could not be found, or a conversion failed."""


@functools.lru_cache(maxsize=1)
def find_ffmpeg() -> str:
    """Path to an ffmpeg binary: system PATH first, then imageio-ffmpeg."""
    system = shutil.which("ffmpeg")
    if system:
        return system
    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise FFmpegError(
            "ffmpeg bulunamadı ve imageio-ffmpeg kurulu değil.\n"
            "Ya ffmpeg'i PATH'e ekleyin ya da 'pip install -r requirements.txt' "
            "çalıştırın."
        ) from exc
    path: str = imageio_ffmpeg.get_ffmpeg_exe()
    logger.debug("Sistem ffmpeg'i yok, imageio-ffmpeg kullanılıyor: %s", path)
    return path


def run(*args: str) -> str:
    """Run ffmpeg with *args*; return its stderr.

    ffmpeg writes everything informational to stderr, so the caller gets it
    back for parsing.  A non-zero exit is always an error here: this module
    only ever asks for conversions that must succeed.
    """
    command = [find_ffmpeg(), "-hide_banner", "-nostdin", *args]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, errors="replace",
            timeout=_TIMEOUT_S, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise FFmpegError(f"ffmpeg çalıştırılamadı: {exc}") from exc
    if result.returncode != 0:
        raise FFmpegError(
            f"ffmpeg başarısız (çıkış {result.returncode}):\n"
            f"  komut: {' '.join(command)}\n{result.stderr.strip()}"
        )
    return result.stderr


def _inspect(path: Path) -> str:
    """Return ffmpeg's stderr for ``-i path`` with no output file.

    ffmpeg exits non-zero in this mode ("At least one output file must be
    specified") which is why it does not go through :func:`run`.
    """
    command = [find_ffmpeg(), "-hide_banner", "-nostdin", "-i", str(path)]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, errors="replace",
            timeout=_TIMEOUT_S, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise FFmpegError(f"ffmpeg çalıştırılamadı: {exc}") from exc
    return result.stderr


_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d\d):(\d\d(?:\.\d+)?)")
_STREAM_RE = re.compile(r"Stream #\d+:\d+.*?: (Video|Audio): (\w+)")
_FPS_RE = re.compile(r"([\d.]+) fps")
_SIZE_RE = re.compile(r"(?<![\d])(\d{2,5})x(\d{2,5})(?![\d])")
_HZ_RE = re.compile(r"(\d+) Hz")
_CHANNELS_RE = re.compile(r"\b(mono|stereo|(\d+) channels)\b")
_FRAME_RE = re.compile(r"frame=\s*(\d+)")


@dataclass(frozen=True)
class VideoStream:
    codec: str
    fps: float
    width: int
    height: int


@dataclass(frozen=True)
class AudioStream:
    codec: str
    sample_rate: int
    channels: int


@dataclass(frozen=True)
class MediaInfo:
    path: Path
    duration_s: float
    video: VideoStream | None
    audio: AudioStream | None

    def require_video(self) -> VideoStream:
        if self.video is None:
            raise FFmpegError(f"Görüntü akışı yok: {self.path}")
        return self.video

    def require_audio(self) -> AudioStream:
        if self.audio is None:
            raise FFmpegError(f"Ses akışı yok: {self.path}")
        return self.audio


def probe(path: Path) -> MediaInfo:
    """Duration and stream properties of *path*."""
    if not path.is_file():
        raise FFmpegError(f"Dosya yok: {path}")

    stderr = _inspect(path)

    duration = 0.0
    match = _DURATION_RE.search(stderr)
    if match:
        hours, minutes, seconds = match.groups()
        duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)

    video: VideoStream | None = None
    audio: AudioStream | None = None
    for line in stderr.splitlines():
        stream = _STREAM_RE.search(line)
        if stream is None:
            continue
        kind, codec = stream.group(1), stream.group(2)
        if kind == "Video" and video is None:
            fps = _FPS_RE.search(line)
            size = _SIZE_RE.search(line)
            if fps is None or size is None:
                raise FFmpegError(
                    f"Görüntü akışı çözümlenemedi: {path}\n  satır: {line.strip()}"
                )
            video = VideoStream(
                codec=codec,
                fps=float(fps.group(1)),
                width=int(size.group(1)),
                height=int(size.group(2)),
            )
        elif kind == "Audio" and audio is None:
            hertz = _HZ_RE.search(line)
            channels = _CHANNELS_RE.search(line)
            if hertz is None or channels is None:
                raise FFmpegError(
                    f"Ses akışı çözümlenemedi: {path}\n  satır: {line.strip()}"
                )
            count = {"mono": 1, "stereo": 2}.get(channels.group(1))
            if count is None:
                count = int(channels.group(2))
            audio = AudioStream(
                codec=codec, sample_rate=int(hertz.group(1)), channels=count
            )

    if video is None and audio is None:
        raise FFmpegError(
            f"Medya akışı bulunamadı: {path}\n{stderr.strip()}"
        )
    return MediaInfo(path=path, duration_s=duration, video=video, audio=audio)


def has_audio_stream(path: Path) -> bool:
    """Whether *path* carries an audio stream.

    §A.1: the video handed to MovieStim must not.  PsychoPy 2026.1 overrides
    ``noAudio`` and always routes ffpyplayer through SDL2, so the file itself
    being silent is the only thing keeping a second, unscheduled audio path
    from playing.
    """
    return probe(path).audio is not None


def count_frames(path: Path) -> int:
    """Number of video frames in *path*, counted by decoding it."""
    stderr = run("-i", str(path), "-map", "0:v", "-c", "copy", "-f", "null", "-")
    matches = _FRAME_RE.findall(stderr)
    if not matches:
        raise FFmpegError(f"Kare sayısı okunamadı: {path}\n{stderr.strip()}")
    return int(matches[-1])


def extract_audio(source: Path, destination: Path, *, sample_rate: int) -> None:
    """Extract *source*'s audio as a mono 32-bit float WAV at *sample_rate*.

    Float rather than integer: this file is only an intermediate that gets
    measured and normalised, and rounding it to integers twice would add
    quantisation noise for nothing.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    run(
        "-y", "-i", str(source),
        "-vn",
        "-map", "0:a:0",
        "-acodec", "pcm_f32le",
        "-ar", str(sample_rate),
        "-ac", "1",
        str(destination),
    )


def write_silent_video(
    source: Path,
    destination: Path,
    *,
    fps: float,
    crf: int,
    all_intra: bool,
) -> None:
    """Re-encode *source*'s video stream to CFR *fps* with no audio track.

    ``-an`` is what makes the file safe for MovieStim (§A.1).  The frame rate
    filter only relabels timestamps for clips this short — the caller checks
    that the frame count survived.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    args = [
        "-y", "-i", str(source),
        "-an",
        "-map", "0:v:0",
        # The fps filter emits frames on an exact 1/fps grid, which is what
        # makes the output constant-rate.  ``-fps_mode cfr`` would say so
        # explicitly but only exists from ffmpeg 5.1, and the caller verifies
        # the frame count and rate of the result anyway.
        "-vf", f"fps={fps}",
        "-c:v", "libx264",
        "-crf", str(crf),
        "-preset", "slow",
        "-pix_fmt", "yuv420p",
    ]
    if all_intra:
        # Every frame an I-frame: decoding frame N never waits on frame N-1,
        # so a seek or a slow decode cannot stall presentation.
        args += ["-g", "1", "-bf", "0"]
    args.append(str(destination))
    run(*args)
