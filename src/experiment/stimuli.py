"""Stimulus loading and presentation helpers for PsychoPy."""

import logging
from pathlib import Path
from typing import Any

from psychopy import visual, core

# Suppress the sdl2 A/V sync warning — not relevant when audio is embedded in video.
# The warning fires because ffpyplayer uses sdl2 for audio, but since our audio and
# video are muxed in the same mp4 file, they share the same decode timeline.
logging.getLogger("psychopy.visual.movies").setLevel(logging.ERROR)


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
) -> visual.MovieStim:
    """Load a video stimulus from file.

    Args:
        win: PsychoPy window.
        video_path: Path to mp4 file.
        with_audio: If False, video plays without sound (for visual_only section).
    """
    movie = visual.MovieStim(
        win,
        str(video_path),
        noAudio=not with_audio,
        loop=False,
    )
    # Fallback: some PsychoPy/ffpyplayer versions ignore noAudio,
    # so force volume to zero as a safety net.
    if not with_audio:
        try:
            movie.setVolume(0)
        except Exception:
            pass
    return movie


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
) -> float:
    """Present a video stimulus and return the timestamp when it ends.

    Returns:
        Time (on the provided clock) when the video finished.
    """
    movie.play()
    while not movie.isFinished:
        movie.draw()
        win.flip()
    win.flip()  # clear screen after video
    video_end_time = clock.getTime()
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
