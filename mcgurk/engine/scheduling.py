"""Timing arithmetic for A/V presentation.  No PsychoPy, no I/O.

Everything that decides *when* something happens lives here, so it can be
tested against synthetic timestamps on a machine with no screen and no sound
card.  ``av_presenter.py`` is then a shell that reads clocks, calls these
functions and does what they say.

The model:

* The video can only start on a refresh boundary.  The audio can be scheduled
  to sample precision by the PTB backend.  Therefore **all SOA manipulation is
  done on the audio side** (steps.md §C Adım 3) — the flip target is only ever
  pushed further into the future, never moved to express an SOA.
* ``system_av_offset_ms`` (*D*, from ``docs/01_av_gecikme_olcumu.md``) is the
  difference between the two physical latencies, sound minus light.  Scheduling
  the audio *D* earlier makes the experienced asynchrony equal the nominal one::

      t_audio = t_flip + SOA − D

* A negative SOA needs the audio to start before the video.  That is only
  possible if the flip target is far enough ahead, so the lead is computed per
  trial rather than taken from the config as a constant: at 60 Hz the config's
  six frames cover 100 ms, and the TBW module asks for −300 ms.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from . import EngineError

#: How far in the future a sound must be scheduled for PTB to arm the buffer in
#: time.  20 ms is comfortably above the block size at latency mode 3 and still
#: only ~1 frame at 60 Hz, so it costs nothing in practice.  A request that
#: lands inside this margin is an error, not something to nudge.
DEFAULT_SCHEDULE_MARGIN_S = 0.020

#: Tolerated deviation between the measured refresh rate and the configured
#: one before the session is called mis-configured.
DEFAULT_REFRESH_TOLERANCE_PCT = 5.0


class SchedulingError(EngineError):
    """A trial cannot be presented with the timing it was asked for."""


@dataclass(frozen=True)
class TimingParams:
    """The timing side of the config, resolved for one machine.

    ``system_av_offset_ms`` is 0.0 when the photodiode measurement has not been
    made.  That is allowed in ``development`` only — the config layer refuses
    ``data_collection`` without it (Adım 1) — and the caller is expected to say
    so in the log once, not once per trial.
    """

    frame_period_s: float
    lead_frames: int = 6
    system_av_offset_ms: float = 0.0
    schedule_margin_s: float = DEFAULT_SCHEDULE_MARGIN_S
    dropped_frame_tolerance: float = 1.5
    #: Ceiling on the computed lead.  The lead grows to make room for a
    #: negative SOA, and a second is far more room than any design in this
    #: study needs (the widest is TBW's −300 ms).  Past that, something is
    #: wrong — an absurd SOA, or a caller that was blocked for most of a
    #: second between reading the clock and asking for a plan — and stretching
    #: the trial silently is the wrong answer.
    max_lead_s: float = 1.0

    def __post_init__(self) -> None:
        if self.frame_period_s <= 0:
            raise SchedulingError(
                f"Kare süresi pozitif olmalı (verilen: {self.frame_period_s})"
            )
        if self.lead_frames < 1:
            raise SchedulingError(
                f"timing.lead_frames en az 1 olmalı (verilen: {self.lead_frames})"
            )
        if self.schedule_margin_s < 0:
            raise SchedulingError("Planlama payı negatif olamaz")
        if self.dropped_frame_tolerance <= 1.0:
            raise SchedulingError(
                "timing.dropped_frame_tolerance 1.0'dan büyük olmalı; 1.0 her "
                "kareyi düşmüş sayardı"
            )
        if self.max_lead_s < self.lead_frames * self.frame_period_s:
            raise SchedulingError(
                "max_lead_s, timing.lead_frames'in kendisinden küçük olamaz"
            )

    @property
    def refresh_hz(self) -> float:
        return 1.0 / self.frame_period_s

    @property
    def offset_s(self) -> float:
        return self.system_av_offset_ms / 1000.0


@dataclass(frozen=True)
class PresentationPlan:
    """When the video flips and when the audio is handed to PTB."""

    #: Target time of the flip that shows the first video frame.
    video_flip_s: float
    #: Time passed to ``Sound.play(when=...)``; ``None`` for a silent trial.
    audio_start_s: float | None
    #: Frames waited before the video flip — ``timing.lead_frames`` or more.
    lead_frames: int
    #: Audio start relative to the video flip: ``SOA − D``, in seconds.
    audio_offset_s: float


def audio_offset_s(nominal_soa_ms: float | None, params: TimingParams) -> float:
    """Where the audio sits relative to the video flip, in seconds.

    Negative means the audio starts first.  ``None`` is treated as SOA 0: a
    module that does not manipulate SOA still wants the compensation applied.
    """
    soa_s = (nominal_soa_ms or 0.0) / 1000.0
    return soa_s - params.offset_s


def required_lead_frames(
    *,
    earliest_flip_s: float,
    now_s: float,
    nominal_soa_ms: float | None,
    params: TimingParams,
    with_audio: bool = True,
) -> int:
    """Frames to wait before the video flip so the audio can still be armed.

    ``timing.lead_frames`` is the floor.  A negative SOA raises it: the audio
    has to start ``|SOA − D|`` before the flip, and PTB needs
    ``schedule_margin_s`` on top of that to arm the buffer.

    Raises:
        SchedulingError: when the required lead exceeds ``max_lead_s``.
    """
    if not with_audio:
        return params.lead_frames

    delta = audio_offset_s(nominal_soa_ms, params)
    needed_s = (now_s + params.schedule_margin_s) - (earliest_flip_s + delta)
    if needed_s <= 0.0:
        return params.lead_frames

    lead = max(params.lead_frames, math.ceil(needed_s / params.frame_period_s))
    if lead * params.frame_period_s > params.max_lead_s:
        raise SchedulingError(
            f"Gereken pay {lead} kare ({lead * params.frame_period_s * 1000:.0f} ms), "
            f"üst sınır {params.max_lead_s * 1000:.0f} ms. SOA {nominal_soa_ms} ms "
            "bu tasarım için fazla büyük ya da çağıran uzun süre bloke oldu; "
            "denemeyi sessizce uzatmak yerine durduruluyor."
        )
    return lead


def plan_presentation(
    *,
    earliest_flip_s: float,
    now_s: float,
    params: TimingParams,
    nominal_soa_ms: float | None = None,
    with_audio: bool = True,
) -> PresentationPlan:
    """Decide the flip target and the audio start time for one trial.

    Args:
        earliest_flip_s: ``win.getFutureFlipTime(clock='ptb')`` — the next flip
            the window can produce.
        now_s: ``ptb.GetSecs()`` read at the same moment.

    Raises:
        SchedulingError: if the audio would have to start in the past (or
            inside the arming margin).  There is no fallback: a sound that PTB
            starts "as soon as it can" silently destroys the SOA it was asked
            for, and nothing downstream would ever notice.
    """
    delta = audio_offset_s(nominal_soa_ms, params)
    lead = required_lead_frames(
        earliest_flip_s=earliest_flip_s,
        now_s=now_s,
        nominal_soa_ms=nominal_soa_ms,
        params=params,
        with_audio=with_audio,
    )
    video_flip_s = earliest_flip_s + lead * params.frame_period_s

    if not with_audio:
        return PresentationPlan(video_flip_s, None, lead, delta)

    audio_start_s = video_flip_s + delta
    # Tolerance of a microsecond: the lead was computed to satisfy exactly this
    # inequality, so only floating-point dust can land on the boundary.
    if audio_start_s < now_s + params.schedule_margin_s - 1e-6:
        raise SchedulingError(
            f"Ses {(now_s - audio_start_s) * 1000:.1f} ms geçmişe planlanıyor "
            f"(SOA {nominal_soa_ms} ms, D {params.system_av_offset_ms} ms, "
            f"pay {lead} kare). timing.lead_frames artırılmalı."
        )
    return PresentationPlan(video_flip_s, audio_start_s, lead, delta)


def experienced_soa_ms(
    *,
    video_onset_s: float,
    audio_onset_s: float,
    params: TimingParams,
    video_burst_s: float = 0.0,
    audio_burst_s: float = 0.0,
) -> float:
    """The asynchrony the participant experienced, in milliseconds.

    Measured between the two *acoustic burst* moments rather than between the
    two file onsets, so the residual alignment error inside the prepared files
    (< 1 ms, Adım 2) is part of the number instead of being assumed away.

    *D* is added back in, which is the decision recorded in ``progress.md``:
    ``trials.actual_soa_ms`` is what the participant experienced, directly
    comparable with ``nominal_soa_ms``.  The raw software difference is
    recoverable as ``actual_soa_ms − sessions.system_av_offset_ms``.
    """
    software_diff_s = (audio_onset_s + audio_burst_s) - (video_onset_s + video_burst_s)
    return software_diff_s * 1000.0 + params.system_av_offset_ms


def burst_onset_s(audio_onset_s: float, audio_burst_s: float) -> float:
    """Wall-clock time of the acoustic burst — the RT reference (Adım 4)."""
    return audio_onset_s + audio_burst_s


@dataclass(frozen=True)
class FrameStats:
    """What the refresh loop did during one presentation (§A.4)."""

    n_frames: int
    dropped_frames: int
    max_interval_ms: float


def frame_stats(intervals_s: Sequence[float], params: TimingParams) -> FrameStats:
    """Summarise recorded frame intervals.

    A frame counts as dropped when its interval exceeds
    ``dropped_frame_tolerance`` times the nominal period.  The count is of
    *late intervals*, not of missing frames: two frames' worth of delay in one
    interval is one dropped frame here.  It is a flag for excluding a trial,
    not a frame budget.
    """
    limit = params.frame_period_s * params.dropped_frame_tolerance
    dropped = sum(1 for interval in intervals_s if interval > limit)
    longest = max(intervals_s) * 1000.0 if intervals_s else 0.0
    return FrameStats(len(intervals_s), dropped, longest)


def refresh_deviation_pct(measured_hz: float, expected_hz: float) -> float:
    if expected_hz <= 0:
        raise SchedulingError("display.expected_refresh_hz pozitif olmalı")
    return abs(measured_hz - expected_hz) / expected_hz * 100.0


def refresh_matches(
    measured_hz: float,
    expected_hz: float,
    tolerance_pct: float = DEFAULT_REFRESH_TOLERANCE_PCT,
) -> bool:
    return refresh_deviation_pct(measured_hz, expected_hz) <= tolerance_pct


def check_burst_alignment(
    *, video_burst_s: float, audio_burst_s: float, tolerance_ms: float
) -> float:
    """Verify the prepared pair really is aligned; return the error in ms.

    Adım 2 mounts every audio token on the video's own burst time, so the two
    manifest entries have to agree.  If they do not, the set was prepared with
    a different config than the one now being presented, and every SOA in the
    session would be off by the difference.

    Raises:
        SchedulingError: when the disagreement exceeds *tolerance_ms*.
    """
    error_ms = (audio_burst_s - video_burst_s) * 1000.0
    if abs(error_ms) > tolerance_ms:
        raise SchedulingError(
            f"Uyaran hizalaması bozuk: ses patlaması videonunkinden "
            f"{error_ms:+.1f} ms uzakta (tolerans {tolerance_ms:.1f} ms). "
            "Uyaran seti güncel config ile hazırlanmamış olabilir: "
            "python tools/verify_stimuli.py"
        )
    return error_ms
