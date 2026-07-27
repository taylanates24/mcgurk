"""Presenting one trial and recording what actually happened.

The contract is deliberately narrow: a ``TrialSpec`` goes in, a stimulus is
presented, a ``TimingRecord`` comes out.  Choosing what to present is the
modules' job (Adım 4–7c), collecting the response likewise; this file only has
to make the presentation happen at the right time and say when it did.

Two rules shape everything below:

* **prepare() and present() are separate.**  Decoding, reading files and
  building sound buffers happen between trials.  ``present()`` does no I/O and
  no DSP (§A.12) — it reads clocks, flips the window and returns.
* **A missed schedule is an error, not a degraded trial.**  There is no branch
  anywhere that starts a sound "as soon as possible": an unschedulable onset
  produces unusable data that looks exactly like usable data.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config.calibration import Calibration
from ..db.models import TrialTiming
from . import AbortSession, EngineError
from .audio import (
    EARS,
    AudioStimulus,
    load_audio,
    make_sound,
    playback_health,
    reported_start_time,
)
from .scheduling import (
    FrameStats,
    TimingParams,
    burst_onset_s,
    check_burst_alignment,
    experienced_soa_ms,
    plan_presentation,
)
from .window import FrameMonitor

logger = logging.getLogger(__name__)

#: Key that stops the session at any point of a trial (Adım 0 lesson: an abort
#: key that only works on the response screen is not an abort key).
ABORT_KEY = "escape"


class PresentationError(EngineError):
    """A trial could not be presented as specified."""


@contextmanager
def _quiet_movie_init() -> Iterator[None]:
    """Silence PsychoPy's console during ``MovieStim`` construction.

    MovieStim always warns that it is using SDL2 for audio and it cannot be
    turned off (PsychoPy overwrites the ``noAudio`` argument — see CLAUDE.md).
    The prepared videos carry no audio stream at all, so the warning is noise.
    The window is one constructor call wide on purpose: dropped-frame warnings
    during presentation must still reach the operator.
    """
    from psychopy import logging as psychopy_logging

    original_level = psychopy_logging.console.level
    psychopy_logging.console.setLevel(psychopy_logging.ERROR)
    try:
        yield
    finally:
        psychopy_logging.console.setLevel(original_level)


def check_abort(key: str = ABORT_KEY) -> None:
    """Raise :class:`AbortSession` if the operator pressed the abort key."""
    from psychopy import event

    if event.getKeys(keyList=[key]):
        raise AbortSession()


# --------------------------------------------------------------------- specs


@dataclass(frozen=True)
class TrialSpec:
    """What to present in one trial.

    Paths are resolved by the caller: the modules read the manifest and pick
    the noise instance (Adım 4–5), the presenter just plays what it is given.
    Burst times come from the manifest too — they are the common time origin
    the SOA is expressed against.
    """

    label: str = ""
    video_path: Path | None = None
    video_burst_s: float = 0.0
    audio_path: Path | None = None
    audio_burst_s: float = 0.0
    #: Which ear the audio goes to.  ``both`` for diotic and for the dichotic
    #: files, whose two channels are already different.
    ear: str = "both"
    #: Positive = audio after video.  ``None`` means "no SOA manipulation",
    #: which is still scheduled through the same path with SOA 0.
    nominal_soa_ms: float | None = None

    def __post_init__(self) -> None:
        if self.video_path is None and self.audio_path is None:
            raise PresentationError(
                "TrialSpec en az bir uyaran taşımalı (video veya ses)"
            )
        if self.ear not in EARS:
            raise PresentationError(f"Bilinmeyen kulak: {self.ear!r}")
        if self.nominal_soa_ms is not None and self.mode != "AV":
            raise PresentationError(
                f"SOA yalnızca AV denemesinde anlamlı (mod: {self.mode}). "
                "Tek modaliteli denemede iki akış arasında bir gecikme yoktur."
            )

    @property
    def mode(self) -> str:
        """``AV``, ``A`` or ``V`` — matching ``trials.presentation_mode``."""
        if self.video_path is not None and self.audio_path is not None:
            return "AV"
        return "V" if self.video_path is not None else "A"


@dataclass
class PreparedTrial:
    """A trial with its media loaded and buffered, ready to present."""

    spec: TrialSpec
    movie: Any | None = None
    sound: Any | None = None
    audio: AudioStimulus | None = None
    #: Disagreement between the video's burst time and the audio's, in ms.
    alignment_error_ms: float | None = None

    @property
    def audio_duration_s(self) -> float:
        return self.audio.duration_s if self.audio is not None else 0.0


@dataclass(frozen=True)
class TimingRecord:
    """What actually happened (§A.4).

    Onsets are seconds relative to the presenter's reference time, so they are
    small, comparable within a session, and free of the machine's boot epoch.
    """

    nominal_soa_ms: float | None = None
    video_onset_s: float | None = None
    audio_onset_s: float | None = None
    actual_soa_ms: float | None = None
    #: Wall-clock (reference-relative) time of the burst.  Adım 4 measures
    #: ``rt_from_burst_ms`` from here.  In a trial with audio it is the
    #: acoustic burst; in a V-only trial (Adım 5) there is none, so it is the
    #: *visual* one — the release the manifest measured on the original take.
    #: Without it, a V-only RT would have no reference other than the prompt
    #: and could not be compared with the AV trials it is the baseline for.
    burst_onset_s: float | None = None
    dropped_frames: int = 0
    max_frame_interval_ms: float = 0.0
    n_frames: int = 0
    #: Flip that showed the first video frame minus the flip it was planned
    #: for.  Non-zero means the refresh loop slipped.
    flip_error_ms: float | None = None
    #: Lead used for this trial; larger than ``timing.lead_frames`` whenever a
    #: negative SOA needed the room.
    lead_frames: int = 0
    #: True when the audio onset is the time PsychPortAudio reported, False
    #: when it is the time the engine asked for because PTB reported nothing.
    #: Note that "reported" is not "measured": on hardware without output
    #: timestamping PTB reports back exactly what it was asked for (see
    #: ``audio.reported_start_time``).  The onset is verified physically, by
    #: the loopback and photodiode measurements, or not at all.
    audio_onset_reported: bool = False
    #: Deadlines PsychPortAudio could not meet, and buffer under-runs, during
    #: this trial.  Anything but zero means the sound did not come out when it
    #: was asked for.
    audio_time_failed: int = 0
    audio_xruns: int = 0
    #: Presentation timestamp of the first video frame shown; ~0 when the
    #: video really started at its first frame.
    first_frame_pts_s: float | None = None
    duration_s: float = 0.0
    alignment_error_ms: float | None = None

    def to_trial_timing(self) -> TrialTiming:
        """Map onto the database row (``trials`` realised-timing columns)."""
        return TrialTiming(
            video_onset_s=self.video_onset_s,
            audio_onset_s=self.audio_onset_s,
            actual_soa_ms=self.actual_soa_ms,
            dropped_frames=self.dropped_frames,
            max_frame_interval_ms=self.max_frame_interval_ms,
        )


# ----------------------------------------------------------------- presenter


@dataclass
class _Clocks:
    """The one time base: everything is ``psychtoolbox.GetSecs()``."""

    module: Any = field(default=None)

    def now(self) -> float:
        if self.module is None:
            import psychtoolbox

            self.module = psychtoolbox
        return float(self.module.GetSecs())


class AVPresenter:
    """Presents prepared trials on a window with a PTB sound backend."""

    def __init__(
        self,
        win: Any,
        params: TimingParams,
        *,
        speaker: Any = None,
        calibration: Calibration | None = None,
        sample_rate: int | None = None,
        alignment_tolerance_ms: float = 5.0,
        fixation: Any = None,
        reference_time_s: float | None = None,
    ) -> None:
        self.win = win
        self.params = params
        self.speaker = speaker
        self.calibration = calibration
        self.sample_rate = sample_rate
        self.alignment_tolerance_ms = alignment_tolerance_ms
        self.fixation = fixation
        self._clocks = _Clocks()
        self._monitor = FrameMonitor(win, params)
        self.reference_time_s = (
            reference_time_s if reference_time_s is not None else self._clocks.now()
        )
        if calibration is None:
            logger.warning(
                "Kalibrasyon yok: ses seviyesi trim'i uygulanmıyor. Bu yalnızca "
                "development modunda kabul edilebilir."
            )
        if params.system_av_offset_ms == 0.0:
            logger.warning(
                "system_av_offset_ms ölçülmemiş (0 kabul ediliyor). Fotodiyot "
                "ölçümü yapılana kadar mutlak A/V gecikmesi telafi edilmiyor "
                "(docs/01_av_gecikme_olcumu.md)."
            )

    # -- preparation ------------------------------------------------------

    def prepare(self, spec: TrialSpec) -> PreparedTrial:
        """Load and buffer everything *spec* needs.  Runs between trials."""
        prepared = PreparedTrial(spec=spec)

        if spec.mode == "AV":
            prepared.alignment_error_ms = check_burst_alignment(
                video_burst_s=spec.video_burst_s,
                audio_burst_s=spec.audio_burst_s,
                tolerance_ms=self.alignment_tolerance_ms,
            )

        if spec.audio_path is not None:
            prepared.audio = load_audio(
                spec.audio_path,
                ear=spec.ear,
                burst_time_s=spec.audio_burst_s,
                calibration=self.calibration,
                expected_sample_rate=self.sample_rate,
            )
            prepared.sound = make_sound(prepared.audio, self.speaker)

        if spec.video_path is not None:
            prepared.movie = self._load_movie(spec.video_path)

        return prepared

    def _load_movie(self, path: Path) -> Any:
        from psychopy import visual

        if not path.is_file():
            raise PresentationError(f"Video dosyası yok: {path}")

        with _quiet_movie_init():
            movie = visual.MovieStim(
                self.win,
                str(path),
                noAudio=True,
                loop=False,
                autoStart=False,
                units="pix",
                pos=(0, 0),  # §A.13 — centred, and the config cannot say otherwise
            )
        # The prepared videos have no audio stream at all, but MovieStim keeps
        # an SDL2 path alive regardless; muting costs nothing and removes the
        # last way a sound could escape the video container (§A.1).
        movie.setVolume(0)

        # Decode and upload frame 0 now, so the first draw inside the
        # presentation loop is a texture swap rather than a decode.
        movie.updateVideoFrame()
        movie.draw()
        self.win.clearBuffer()
        return movie

    def release(self, prepared: PreparedTrial) -> None:
        """Free the media of a finished trial."""
        if prepared.movie is not None:
            prepared.movie.unload()
            prepared.movie = None
        if prepared.sound is not None:
            prepared.sound = None

    # -- presentation -----------------------------------------------------

    def present(self, prepared: PreparedTrial) -> TimingRecord:
        """Present *prepared* and return what actually happened.

        Raises:
            SchedulingError: if the audio cannot be scheduled as asked.
            AbortSession: if the operator pressed the abort key.
        """
        spec = prepared.spec
        period = self.params.frame_period_s

        # One settling flip before the trial: it gives getFutureFlipTime a
        # fresh reference and keeps the inter-trial gap out of the frame
        # statistics.
        self._draw_background()
        self.win.flip()
        self._monitor.start()

        now = self._clocks.now()
        earliest_flip = float(self.win.getFutureFlipTime(clock="ptb"))
        plan = plan_presentation(
            earliest_flip_s=earliest_flip,
            now_s=now,
            params=self.params,
            nominal_soa_ms=spec.nominal_soa_ms,
            with_audio=prepared.sound is not None,
        )

        reported_start: float | None = None
        video_onset: float | None = None
        first_pts: float | None = None

        def poll_audio_start() -> None:
            """Read PTB's reported start as soon as it is available.

            Read repeatedly rather than once at the end: the status dictionary
            is the only place that number exists, and there is no guarantee
            about how long it survives after playback drains.
            """
            nonlocal reported_start
            if reported_start is None and prepared.sound is not None:
                reported_start = reported_start_time(prepared.sound)

        try:
            if prepared.sound is not None:
                assert plan.audio_start_s is not None
                prepared.sound.play(when=plan.audio_start_s)

            # Wait out the lead.  The audio may well start inside this loop:
            # that is what a negative SOA is.
            while float(self.win.getFutureFlipTime(clock="ptb")) < plan.video_flip_s - period / 2:
                check_abort()
                self._draw_background()
                self.win.flip()
                poll_audio_start()

            # The onset flip.
            if prepared.movie is not None:
                prepared.movie.setVolume(0)
                prepared.movie.play()
                prepared.movie.draw()
            else:
                self._draw_background()
            self.win.flip()
            onset_time = self._clocks.now()
            poll_audio_start()

            if prepared.movie is not None:
                video_onset = onset_time
                first_pts = float(getattr(prepared.movie, "pts", 0.0) or 0.0)
                self._run_video(prepared, poll_audio_start)

            if prepared.sound is not None:
                assert plan.audio_start_s is not None
                self._wait_for_audio(
                    plan.audio_start_s + prepared.audio_duration_s, poll_audio_start
                )
        finally:
            poll_audio_start()
            health = playback_health(prepared.sound) if prepared.sound is not None else (0, 0)
            if prepared.sound is not None:
                prepared.sound.stop()
            if prepared.movie is not None and prepared.movie.isPlaying:
                prepared.movie.pause()
            stats = self._monitor.stop()
            # Clear the screen: the response prompt is drawn by the module, and
            # a stimulus left on screen would be answered while still visible.
            self.win.flip()

        audio_onset: float | None = None
        audio_reported = reported_start is not None
        if prepared.sound is not None:
            assert plan.audio_start_s is not None
            audio_onset = reported_start if reported_start is not None else plan.audio_start_s
            if not audio_reported:
                logger.warning(
                    "PTB bir başlangıç zamanı bildirmedi; planlanan zaman "
                    "kaydedildi (%.6f).",
                    plan.audio_start_s,
                )

        time_failed, xruns = health
        if time_failed or xruns:
            logger.warning(
                "Ses zamanlaması bozuldu (%s): kaçırılan zamanlama %d, buffer "
                "under-run %d. Bu denemenin ses onset'i kayıtta yazandan farklı.",
                spec.label or spec.mode,
                time_failed,
                xruns,
            )

        return self._record(
            spec=spec,
            prepared=prepared,
            plan_video_flip_s=plan.video_flip_s,
            lead_frames=plan.lead_frames,
            video_onset=video_onset,
            audio_onset=audio_onset,
            audio_reported=audio_reported,
            first_pts=first_pts,
            stats=stats,
            time_failed=time_failed,
            xruns=xruns,
        )

    # -- internals --------------------------------------------------------

    def _draw_background(self) -> None:
        """What is on screen when no video is: the fixation cross, or nothing.

        The fixation is the module's decision (Adım 4 owns trial structure);
        the presenter only keeps drawing whatever it was handed, because a
        flip loop with nothing drawn clears the screen.
        """
        if self.fixation is not None:
            self.fixation.draw()

    def _run_video(self, prepared: PreparedTrial, on_flip: Callable[[], None]) -> None:
        """Draw the video until it finishes.  No fixed duration (§C Adım 3)."""
        movie = prepared.movie
        assert movie is not None
        while not movie.isFinished:
            check_abort()
            movie.draw()
            self.win.flip()
            on_flip()

    def _wait_for_audio(self, deadline_s: float, on_flip: Callable[[], None]) -> None:
        """Hold the screen until the sound has finished.

        A flip loop rather than ``core.wait`` so the abort key stays live and
        the wait sits on the refresh grid.  The deadline comes from the sample
        count, not from polling the backend: PTB reports "finished" only after
        the device buffer drains, which is later than the sound.
        """
        while self._clocks.now() < deadline_s:
            check_abort()
            self._draw_background()
            self.win.flip()
            on_flip()

    def _record(
        self,
        *,
        spec: TrialSpec,
        prepared: PreparedTrial,
        plan_video_flip_s: float,
        lead_frames: int,
        video_onset: float | None,
        audio_onset: float | None,
        audio_reported: bool,
        first_pts: float | None,
        stats: FrameStats,
        time_failed: int = 0,
        xruns: int = 0,
    ) -> TimingRecord:
        actual_soa: float | None = None
        if video_onset is not None and audio_onset is not None:
            actual_soa = experienced_soa_ms(
                video_onset_s=video_onset,
                audio_onset_s=audio_onset,
                params=self.params,
                video_burst_s=spec.video_burst_s,
                audio_burst_s=spec.audio_burst_s,
            )

        burst: float | None = None
        if audio_onset is not None:
            burst = burst_onset_s(audio_onset, spec.audio_burst_s) - self.reference_time_s
        elif video_onset is not None:
            # V-only: the visual release stands in for the acoustic burst.
            burst = burst_onset_s(video_onset, spec.video_burst_s) - self.reference_time_s

        flip_error_ms = (
            (video_onset - plan_video_flip_s) * 1000.0 if video_onset is not None else None
        )

        record = TimingRecord(
            nominal_soa_ms=spec.nominal_soa_ms,
            video_onset_s=(
                video_onset - self.reference_time_s if video_onset is not None else None
            ),
            audio_onset_s=(
                audio_onset - self.reference_time_s if audio_onset is not None else None
            ),
            actual_soa_ms=actual_soa,
            burst_onset_s=burst,
            dropped_frames=stats.dropped_frames,
            max_frame_interval_ms=stats.max_interval_ms,
            n_frames=stats.n_frames,
            flip_error_ms=flip_error_ms,
            lead_frames=lead_frames,
            audio_onset_reported=audio_reported,
            audio_time_failed=time_failed,
            audio_xruns=xruns,
            first_frame_pts_s=first_pts,
            duration_s=max(
                prepared.audio_duration_s,
                float(getattr(prepared.movie, "duration", 0.0) or 0.0),
            ),
            alignment_error_ms=prepared.alignment_error_ms,
        )

        if first_pts is not None and first_pts > self.params.frame_period_s:
            logger.warning(
                "İlk gösterilen video karesi t=%.3f s — video ilk karesinden "
                "başlamamış olabilir.", first_pts,
            )
        if actual_soa is not None and spec.nominal_soa_ms is not None:
            error = actual_soa - spec.nominal_soa_ms
            if abs(error) > self.params.frame_period_s * 1000.0:
                logger.warning(
                    "Gerçekleşen SOA nominalden %.1f ms sapıyor (nominal %.1f, "
                    "gerçekleşen %.1f).", error, spec.nominal_soa_ms, actual_soa,
                )
        return record
