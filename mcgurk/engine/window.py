"""Window setup, refresh-rate measurement and frame bookkeeping.

The refresh rate is *measured*, never assumed: every audio schedule in
``scheduling.py`` is expressed in frame periods, so a window that reports
60 Hz while the panel runs at 59.94 Hz would drift a whole frame every 17
seconds.  ``display.expected_refresh_hz`` is what the config claims; what this
module returns is what the machine does.
"""

from __future__ import annotations

import logging
from typing import Any

from ..config.schema import DisplayConfig
from . import EngineError
from .scheduling import DEFAULT_REFRESH_TOLERANCE_PCT, FrameStats, TimingParams, frame_stats

logger = logging.getLogger(__name__)


class WindowError(EngineError):
    """The window could not be opened or its timing could not be trusted."""


def open_window(display: DisplayConfig, *, mouse_visible: bool = False) -> Any:
    """Open the presentation window described by *display*.

    ``waitBlanking=True`` and ``checkTiming=True`` are not options: the first
    is §A.8, and without the second ``getFutureFlipTime`` has no frame period
    to work from and raises.
    """
    from psychopy import visual

    try:
        win = visual.Window(
            size=tuple(display.size),
            fullscr=display.fullscreen,
            screen=display.screen,
            color=display.background,
            units="pix",
            waitBlanking=True,
            checkTiming=True,
            allowGUI=False,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        # Deliberately not a blanket handler (§A.7): anything else is a bug
        # rather than a misconfigured screen, and a traceback is the right
        # output for it.
        raise WindowError(
            f"Pencere açılamadı (ekran {display.screen}, "
            f"{display.size[0]}x{display.size[1]}): {exc}"
        ) from exc

    win.mouseVisible = mouse_visible
    logger.info(
        "Pencere açıldı: %s, ekran %d, %s",
        "tam ekran" if display.fullscreen else "pencereli",
        display.screen,
        tuple(win.clientSize),
    )
    return win


def measure_refresh_hz(
    win: Any,
    *,
    n_identical: int = 20,
    n_max_frames: int = 200,
    n_warmup_frames: int = 20,
    threshold_ms: float = 1.0,
) -> float:
    """Measure the actual refresh rate, or fail.

    PsychoPy returns ``None`` when the frame times never settle — a compositor
    is running, vsync is off, or the window is not really fullscreen.  That is
    a broken timing chain, not a reason to assume 60 Hz.
    """
    measured = win.getActualFrameRate(
        nIdentical=n_identical,
        nMaxFrames=n_max_frames,
        nWarmUpFrames=n_warmup_frames,
        threshold=threshold_ms,
    )
    if not measured:
        raise WindowError(
            "Yenileme hızı ölçülemedi: kare süreleri kararlı değil. "
            "Tam ekran mı, vsync açık mı, arka planda kompozitör/oyun modu "
            "var mı kontrol edin. Ölçülemeyen bir yenileme hızıyla ses "
            "zamanlaması yapılamaz."
        )
    logger.info("Ölçülen yenileme hızı: %.3f Hz (kare %.3f ms)", measured, 1000.0 / measured)
    return float(measured)


def check_refresh_hz(
    measured_hz: float,
    display: DisplayConfig,
    *,
    tolerance_pct: float = DEFAULT_REFRESH_TOLERANCE_PCT,
    strict: bool = False,
) -> bool:
    """Compare the measured rate with ``display.expected_refresh_hz``.

    Args:
        strict: raise instead of warning.  The session checklist (Adım 8) uses
            this in ``data_collection``; a development run only gets a warning
            so the code can be exercised on a laptop.
    """
    from .scheduling import refresh_deviation_pct

    deviation = refresh_deviation_pct(measured_hz, display.expected_refresh_hz)
    if deviation <= tolerance_pct:
        return True

    message = (
        f"Ölçülen yenileme hızı {measured_hz:.2f} Hz, config "
        f"{display.expected_refresh_hz:.2f} Hz diyor (%{deviation:.1f} sapma). "
        "display.expected_refresh_hz düzeltilmeli ya da monitör ayarı yanlış."
    )
    if strict:
        raise WindowError(message)
    logger.warning(message)
    return False


def make_fixation(
    win: Any, *, size_px: float = 40.0, line_width: float = 4.0, color: str = "white"
) -> Any:
    """A fixation cross for the trials that have nothing to show.

    ``audio_only`` and the dichotic module present no video at all (Adım 0
    decision), so something has to hold the participant's gaze at the centre
    where the video would have been.
    """
    from psychopy import visual

    half = size_px / 2.0
    return visual.ShapeStim(
        win,
        vertices=((-half, 0), (half, 0), (0, 0), (0, -half), (0, half)),
        lineWidth=line_width,
        closeShape=False,
        lineColor=color,
        units="pix",
        pos=(0, 0),
        autoLog=False,
    )


class FrameMonitor:
    """Records frame intervals for the duration of one presentation (§A.4).

    PsychoPy accumulates intervals into a single list on the window, so this
    clears it at the start of every trial; otherwise every trial would inherit
    the previous one's dropped frames.
    """

    def __init__(self, win: Any, params: TimingParams) -> None:
        self._win = win
        self._params = params

    def start(self) -> None:
        self._win.recordFrameIntervals = False
        self._win.frameIntervals = []
        # The interval before the first recorded flip includes whatever the
        # inter-trial interval was doing, so recording starts after the flip
        # that opens the trial, not before it.
        self._win.recordFrameIntervals = True

    def stop(self) -> FrameStats:
        self._win.recordFrameIntervals = False
        intervals = list(self._win.frameIntervals)
        stats = frame_stats(intervals, self._params)
        if stats.dropped_frames:
            logger.warning(
                "Düşen kare: %d (en uzun aralık %.1f ms, sınır %.1f ms)",
                stats.dropped_frames,
                stats.max_interval_ms,
                self._params.frame_period_s * self._params.dropped_frame_tolerance * 1000.0,
            )
        return stats
