"""GIN gap placement and gap cutting.

The gap durations are the independent variable of the whole module, so a gap
that is placed wrongly, cut short by its own ramp, or silently dropped would
shift the threshold estimate without leaving a trace in the data.
"""

from __future__ import annotations

import numpy as np
import pytest

from mcgurk.stimuli import dsp

SR = 48000

DURATIONS = [2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0]
#: The shipped GIN design (config/experiment.yaml, Musiek et al. 2005).
N_SEGMENTS = 30
MAX_GAPS_PER_SEGMENT = 3
SEGMENT_DURATION_S = 6.0
MIN_SEPARATION_S = 1.0


def _standard_plan(seed: int = 20260726) -> list[list[tuple[float, float]]]:
    return dsp.plan_gaps(
        np.random.default_rng(seed),
        gap_durations_ms=[d for d in DURATIONS for _ in range(6)],
        n_segments=N_SEGMENTS,
        max_gaps_per_segment=MAX_GAPS_PER_SEGMENT,
        segment_duration_s=SEGMENT_DURATION_S,
        min_separation_s=MIN_SEPARATION_S,
    )


def test_every_gap_is_placed_exactly_once() -> None:
    placed = [gap for segment in _standard_plan() for gap in segment]
    counts: dict[float, int] = {}
    for _, duration in placed:
        counts[duration] = counts.get(duration, 0) + 1

    assert len(placed) == 60
    assert counts == {duration: 6 for duration in DURATIONS}


def test_no_segment_exceeds_its_gap_limit() -> None:
    plan = _standard_plan()
    counts = [len(segment) for segment in plan]
    assert all(count <= MAX_GAPS_PER_SEGMENT for count in counts)
    # The count varies between segments.  A fixed number per segment would let
    # a participant learn how many gaps to expect once the segment starts.
    assert len(set(counts)) > 1


def test_gaps_stay_apart_and_away_from_the_edges() -> None:
    for segment in _standard_plan():
        previous_end = 0.0
        for onset, gap_ms in segment:
            assert onset - previous_end >= MIN_SEPARATION_S - 1e-9
            previous_end = onset + gap_ms / 1000.0
        if segment:
            assert previous_end <= SEGMENT_DURATION_S - MIN_SEPARATION_S + 1e-9


def test_the_same_seed_gives_the_same_plan() -> None:
    assert _standard_plan(1) == _standard_plan(1)
    assert _standard_plan(1) != _standard_plan(2)


def test_a_design_that_does_not_fit_is_an_error() -> None:
    with pytest.raises(dsp.DSPError, match="sığmıyor"):
        dsp.plan_gaps(
            np.random.default_rng(0),
            gap_durations_ms=[5.0] * 100,
            n_segments=10,
            max_gaps_per_segment=3,
            segment_duration_s=6.0,
            min_separation_s=1.0,
        )


def test_a_segment_too_short_for_its_gaps_is_an_error() -> None:
    with pytest.raises(dsp.DSPError, match="sığmıyor"):
        dsp.plan_gaps(
            np.random.default_rng(0),
            gap_durations_ms=[20.0, 20.0],
            n_segments=1,
            max_gaps_per_segment=2,
            segment_duration_s=1.0,
            min_separation_s=0.5,
        )


# ------------------------------------------------------------- cutting gaps


def test_the_gap_is_silent_and_the_rest_is_untouched() -> None:
    rng = np.random.default_rng(3)
    noise = dsp.bandlimited_noise(2 * SR, SR, 100.0, 8000.0, rng)
    cut = dsp.apply_gaps(noise, SR, [(1.0, 10.0)], ramp_ms=1.0)

    inside = cut[int(1.002 * SR) : int(1.008 * SR)]
    assert dsp.peak_dbfs(inside) < -100.0
    # Everything outside the gap and its ramps is bit-identical.
    assert np.array_equal(cut[: int(0.998 * SR)], noise[: int(0.998 * SR)])
    assert np.array_equal(cut[int(1.012 * SR) :], noise[int(1.012 * SR) :])


def test_the_nominal_gap_edges_sit_at_half_amplitude() -> None:
    """The ramp is centred on the edge, so the -6 dB points are the design's.

    Putting the whole ramp inside the gap would make a 2 ms gap effectively
    1 ms of silence, and the shortest detectable gap is the measurement.
    """
    gain = dsp.apply_gaps(np.ones(SR), SR, [(0.5, 10.0)], ramp_ms=1.0)
    assert gain[int(0.5 * SR)] == pytest.approx(0.5, abs=0.05)
    assert gain[int(0.51 * SR)] == pytest.approx(0.5, abs=0.05)


def test_the_gap_edge_has_no_step() -> None:
    """An instantaneous cut clicks; the ramp has to make the edge continuous."""
    gain = dsp.apply_gaps(np.ones(SR), SR, [(0.5, 10.0)], ramp_ms=1.0)
    assert float(np.max(np.abs(np.diff(gain)))) < 0.05


def test_a_gap_against_the_edge_is_an_error() -> None:
    rng = np.random.default_rng(4)
    noise = dsp.bandlimited_noise(SR, SR, 100.0, 8000.0, rng)
    with pytest.raises(dsp.DSPError, match="dışına taşıyor"):
        dsp.apply_gaps(noise, SR, [(0.0, 10.0)], ramp_ms=1.0)
