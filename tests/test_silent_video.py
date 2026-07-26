"""The video handed to MovieStim must carry no audio stream.

PsychoPy 2026.1's MovieStim overwrites the caller's ``noAudio`` argument and
always routes ffpyplayer through SDL2 (passing any other ``audioLib`` raises
MovieAudioError).  So the only thing keeping SDL2 quiet is the file itself
having no audio track.  If ``extract_silent_video`` ever stops stripping it,
SDL2 would start playing the embedded track alongside the ptb-scheduled one
and A/V sync would silently break — hence this test.
"""

import subprocess
from pathlib import Path

import pytest

from src.experiment.stimuli import _get_ffmpeg, extract_silent_video

SOURCE_VIDEO = Path("assets/female_speaker_1/Vis-ba_Aud-ba.mp4")


def _stream_types(path: Path) -> list[str]:
    """Return the codec types ('video'/'audio') of the streams in *path*."""
    result = subprocess.run(
        [_get_ffmpeg(), "-hide_banner", "-i", str(path)],
        capture_output=True,
        text=True,
        errors="replace",
    )
    # ffmpeg writes stream info to stderr and exits non-zero without an
    # output file; parsing that is enough and avoids requiring ffprobe, which
    # imageio-ffmpeg does not ship.
    types = []
    for line in result.stderr.splitlines():
        if "Stream #" not in line:
            continue
        if ": Video:" in line:
            types.append("video")
        elif ": Audio:" in line:
            types.append("audio")
    return types


requires_stimuli = pytest.mark.skipif(
    not SOURCE_VIDEO.exists(),
    reason="uyaran dosyaları yok (assets/ depoya dâhil değil)",
)


@requires_stimuli
def test_source_video_has_audio():
    """Guard the guard: the test is meaningless if the source is already silent."""
    assert "audio" in _stream_types(SOURCE_VIDEO)


@requires_stimuli
def test_silent_copy_has_no_audio_stream():
    silent = extract_silent_video(SOURCE_VIDEO)

    streams = _stream_types(silent)
    assert "video" in streams, "görüntü akışı kaybolmuş"
    assert "audio" not in streams, "sessiz kopyada ses akışı var — SDL2 çalar"


@requires_stimuli
def test_silent_copy_is_cached():
    """Stripping runs ffmpeg; doing it twice per trial would be wasteful."""
    first = extract_silent_video(SOURCE_VIDEO)
    second = extract_silent_video(SOURCE_VIDEO)

    assert first == second
