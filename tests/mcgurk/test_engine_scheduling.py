"""Timing arithmetic — the part that decides when a sound starts.

These run without PsychoPy, without a screen and without a sound card, which
is the point (steps.md §C Adım 3 kabul kriteri: "sentetik zaman damgalarıyla,
PsychoPy'sız").  Every number below is one a real trial would produce.
"""

from __future__ import annotations

import math

import pytest

from mcgurk.engine.scheduling import (
    FrameStats,
    SchedulingError,
    TimingParams,
    audio_offset_s,
    burst_onset_s,
    check_burst_alignment,
    experienced_soa_ms,
    frame_stats,
    plan_presentation,
    refresh_deviation_pct,
    refresh_matches,
    required_lead_frames,
)

FRAME_60HZ = 1.0 / 60.0
#: An arbitrary but realistic ptb clock reading — the machine has been up for
#: a while, so nothing may rely on the epoch being small.
NOW = 12345.678


def params(**kwargs: float | int) -> TimingParams:
    defaults: dict[str, float | int] = {"frame_period_s": FRAME_60HZ, "lead_frames": 6}
    defaults.update(kwargs)
    return TimingParams(**defaults)  # type: ignore[arg-type]


# ------------------------------------------------------------------- params


def test_params_reject_impossible_values() -> None:
    with pytest.raises(SchedulingError):
        TimingParams(frame_period_s=0.0)
    with pytest.raises(SchedulingError):
        TimingParams(frame_period_s=FRAME_60HZ, lead_frames=0)
    with pytest.raises(SchedulingError):
        TimingParams(frame_period_s=FRAME_60HZ, dropped_frame_tolerance=1.0)


def test_refresh_hz_is_the_inverse_of_the_period() -> None:
    assert params().refresh_hz == pytest.approx(60.0)


# ------------------------------------------------------------- audio offset


def test_offset_is_soa_minus_the_measured_delay() -> None:
    # D = +18.28 ms means sound comes out late, so it is scheduled that much
    # earlier (docs/01 §8).
    assert audio_offset_s(0.0, params(system_av_offset_ms=18.28)) == pytest.approx(-0.01828)
    assert audio_offset_s(100.0, params(system_av_offset_ms=18.28)) == pytest.approx(0.08172)


def test_no_soa_still_gets_the_compensation() -> None:
    """``None`` means "this module does not manipulate SOA", not "do nothing"."""
    assert audio_offset_s(None, params(system_av_offset_ms=20.0)) == pytest.approx(-0.02)


# -------------------------------------------------------------------- leads


def test_positive_soa_uses_the_configured_lead() -> None:
    lead = required_lead_frames(
        earliest_flip_s=NOW + FRAME_60HZ,
        now_s=NOW,
        nominal_soa_ms=100.0,
        params=params(),
    )
    assert lead == 6


def test_negative_soa_extends_the_lead_beyond_the_config() -> None:
    """−300 ms cannot fit in the config's six frames (100 ms at 60 Hz)."""
    lead = required_lead_frames(
        earliest_flip_s=NOW + FRAME_60HZ,
        now_s=NOW,
        nominal_soa_ms=-300.0,
        params=params(),
    )
    assert lead > 6
    assert lead * FRAME_60HZ >= 0.300


def test_silent_trial_never_extends_the_lead() -> None:
    """A V-only trial has nothing to schedule, so the SOA cannot bite."""
    lead = required_lead_frames(
        earliest_flip_s=NOW + FRAME_60HZ,
        now_s=NOW,
        nominal_soa_ms=-300.0,
        params=params(),
        with_audio=False,
    )
    assert lead == 6


def test_lead_grows_with_the_measured_delay() -> None:
    """A large D pushes the audio earlier just like a negative SOA does."""
    without = required_lead_frames(
        earliest_flip_s=NOW, now_s=NOW, nominal_soa_ms=-100.0, params=params()
    )
    with_offset = required_lead_frames(
        earliest_flip_s=NOW,
        now_s=NOW,
        nominal_soa_ms=-100.0,
        params=params(system_av_offset_ms=50.0),
    )
    assert with_offset > without


# --------------------------------------------------------------------- plan


def test_soa_zero_starts_audio_on_the_video_flip() -> None:
    plan = plan_presentation(
        earliest_flip_s=NOW + FRAME_60HZ, now_s=NOW, params=params(), nominal_soa_ms=0.0
    )
    assert plan.audio_start_s == pytest.approx(plan.video_flip_s)
    assert plan.video_flip_s == pytest.approx(NOW + 7 * FRAME_60HZ)


@pytest.mark.parametrize("soa_ms", [-300.0, -150.0, -50.0, 0.0, 50.0, 150.0, 300.0])
def test_every_tbw_soa_is_realised_exactly(soa_ms: float) -> None:
    """The whole SOA grid of the TBW module, with a measured D applied."""
    settings = params(system_av_offset_ms=18.28)
    plan = plan_presentation(
        earliest_flip_s=NOW + FRAME_60HZ,
        now_s=NOW,
        params=settings,
        nominal_soa_ms=soa_ms,
    )
    realised = experienced_soa_ms(
        video_onset_s=plan.video_flip_s,
        audio_onset_s=plan.audio_start_s or 0.0,
        params=settings,
    )
    # Tolerance is a nanosecond: the clock readings are large numbers, so
    # exact equality would only be testing float64's mantissa.
    assert realised == pytest.approx(soa_ms, abs=1e-6)


def test_audio_is_never_scheduled_into_the_past() -> None:
    settings = params(system_av_offset_ms=18.28)
    for soa_ms in (-300.0, -100.0, 0.0, 300.0):
        plan = plan_presentation(
            earliest_flip_s=NOW + FRAME_60HZ,
            now_s=NOW,
            params=settings,
            nominal_soa_ms=soa_ms,
        )
        assert plan.audio_start_s is not None
        assert plan.audio_start_s >= NOW + settings.schedule_margin_s - 1e-9


def test_an_absurd_soa_is_refused_rather_than_stretching_the_trial() -> None:
    """The lead grows to make room, but not without limit.

    A trial that quietly waits two seconds before starting is not a trial that
    failed — which is exactly why it has to be made to fail.
    """
    with pytest.raises(SchedulingError, match="üst sınır"):
        plan_presentation(
            earliest_flip_s=NOW + FRAME_60HZ,
            now_s=NOW,
            params=params(),
            nominal_soa_ms=-2000.0,
        )


def test_a_blocked_caller_is_refused_too() -> None:
    """The next flip is a second in the past: the process was stalled."""
    with pytest.raises(SchedulingError, match="üst sınır"):
        plan_presentation(
            earliest_flip_s=NOW - 1.5, now_s=NOW, params=params(), nominal_soa_ms=0.0
        )


def test_the_lead_ceiling_cannot_be_below_the_configured_lead() -> None:
    with pytest.raises(SchedulingError, match="max_lead_s"):
        TimingParams(frame_period_s=FRAME_60HZ, lead_frames=60, max_lead_s=0.1)


def test_silent_trial_gets_no_audio_time() -> None:
    plan = plan_presentation(
        earliest_flip_s=NOW, now_s=NOW, params=params(), with_audio=False
    )
    assert plan.audio_start_s is None


# ------------------------------------------------------------- realised SOA


def test_realised_soa_is_measured_between_the_bursts() -> None:
    """Alignment residue inside the files is part of the number, not assumed away.

    The audio file's burst sits 1 ms later than the video's; the participant
    experiences that millisecond, so it belongs in the record.
    """
    settings = params()
    value = experienced_soa_ms(
        video_onset_s=NOW,
        audio_onset_s=NOW,
        params=settings,
        video_burst_s=1.100,
        audio_burst_s=1.101,
    )
    assert value == pytest.approx(1.0)


def test_realised_soa_includes_the_measured_delay() -> None:
    """The decision recorded in progress.md: actual_soa_ms is what was experienced.

    The engine scheduled the audio D early; the participant therefore hears it
    at the nominal SOA, and that is what gets stored.
    """
    settings = params(system_av_offset_ms=18.28)
    value = experienced_soa_ms(
        video_onset_s=NOW,
        audio_onset_s=NOW - 0.01828,  # what the engine actually did for SOA 0
        params=settings,
    )
    assert value == pytest.approx(0.0, abs=1e-6)


def test_raw_software_difference_is_recoverable() -> None:
    """Analysis can undo the decision: raw = actual − sessions.system_av_offset_ms."""
    settings = params(system_av_offset_ms=18.28)
    stored = experienced_soa_ms(
        video_onset_s=NOW, audio_onset_s=NOW - 0.01828, params=settings
    )
    assert stored - settings.system_av_offset_ms == pytest.approx(-18.28, abs=1e-6)


def test_burst_onset_is_the_rt_reference() -> None:
    assert burst_onset_s(NOW, 1.092) == pytest.approx(NOW + 1.092)


# ------------------------------------------------------------- frame stats


def test_clean_run_drops_nothing() -> None:
    intervals = [FRAME_60HZ] * 100
    stats = frame_stats(intervals, params())
    assert stats.n_frames == 100
    assert stats.dropped_frames == 0
    assert stats.max_interval_ms == pytest.approx(FRAME_60HZ * 1000.0)


def test_a_doubled_interval_counts_as_one_dropped_frame() -> None:
    intervals = [FRAME_60HZ] * 50 + [2 * FRAME_60HZ] + [FRAME_60HZ] * 49
    stats = frame_stats(intervals, params())
    assert stats.dropped_frames == 1
    assert stats.max_interval_ms == pytest.approx(2 * FRAME_60HZ * 1000.0)


def test_tolerance_is_what_decides() -> None:
    """1.5 × 16.67 ms = 25 ms: a 20 ms interval is late but not a dropped frame."""
    intervals = [0.020]
    assert frame_stats(intervals, params(dropped_frame_tolerance=1.5)).dropped_frames == 0
    assert frame_stats(intervals, params(dropped_frame_tolerance=1.1)).dropped_frames == 1


def test_no_flips_is_not_a_crash() -> None:
    stats = frame_stats([], params())
    assert stats == FrameStats(0, 0, 0.0)


# ----------------------------------------------------------------- refresh


def test_refresh_deviation() -> None:
    assert refresh_deviation_pct(59.94, 60.0) == pytest.approx(0.1, abs=0.01)
    assert refresh_matches(59.94, 60.0)
    assert not refresh_matches(120.0, 60.0)


def test_refresh_needs_a_positive_expectation() -> None:
    with pytest.raises(SchedulingError):
        refresh_deviation_pct(60.0, 0.0)


# --------------------------------------------------------------- alignment


def test_aligned_pair_passes_and_reports_the_residue() -> None:
    error = check_burst_alignment(
        video_burst_s=1.1082, audio_burst_s=1.1090, tolerance_ms=5.0
    )
    assert error == pytest.approx(0.8, abs=0.01)


def test_misaligned_pair_stops_the_trial() -> None:
    """Speaker 2's unaligned tokens sit 248 ms apart (Adım 2 measurement).

    Presenting that pair would put the sound outside the McGurk fusion window
    entirely, and nothing downstream would show it.
    """
    with pytest.raises(SchedulingError, match="hizalaması bozuk"):
        check_burst_alignment(video_burst_s=1.084, audio_burst_s=0.836, tolerance_ms=5.0)


def test_lead_is_a_whole_number_of_frames() -> None:
    """Video can only start on a refresh boundary; a fractional lead is a bug."""
    lead = required_lead_frames(
        earliest_flip_s=NOW, now_s=NOW, nominal_soa_ms=-217.0, params=params()
    )
    assert isinstance(lead, int)
    assert lead == math.ceil(lead)
