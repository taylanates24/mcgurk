"""Modül 4 — the stream it designs and what a press means.

The acceptance criteria of steps.md §C Adım 7 that can be checked without
hardware: the target rate matches the config, the spacing constraint holds, the
same seed gives the same stream, a press lands on the right tone, and d' and the
criterion come out right for counts whose answer is known.
"""

from __future__ import annotations

import copy
import random
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from mcgurk.config.loader import ConfigError, load_config
from mcgurk.db.design import DesignExtraError, validate_design_extra
from mcgurk.modules.base import QUIET, ModuleError
from mcgurk.modules.oddball import (
    CORRECT_REJECTION,
    FALSE_ALARM,
    HIT,
    MISS,
    OUTSIDE_WINDOW,
    STANDARD,
    TARGET,
    Counts,
    attribute_presses,
    build_sequence,
    cell_counts,
    count_outcomes,
    detection_measures,
    draw_intervals,
    measures_from_rows,
    onset_times,
    plan_trials,
    summarise_measures,
    target_gaps,
    target_positions,
    trial_outcomes,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STIMULI = Path("stimuli")
SEED = 20260727


@pytest.fixture
def config(write_config: Any, config_dict: dict[str, Any]) -> Any:
    return load_config(write_config(config_dict), check_filesystem=False)


@pytest.fixture
def manifest(config: Any, manifest_factory: Any) -> Any:
    return manifest_factory(config)


def _plan(config: Any, manifest: Any, seed: int = SEED) -> list:
    return plan_trials(config, manifest, seed=seed, stimuli_root=STIMULI)


def _load(write_config: Any, data: dict[str, Any]) -> Any:
    return load_config(write_config(data), check_filesystem=False)


# ---------------------------------------------------------------- the design


def test_the_generator_produces_exactly_what_the_config_estimated(
    config: Any, manifest: Any
) -> None:
    planned = _plan(config, manifest)
    assert len(planned) == config.trial_counts()["oddball"]


def test_the_target_rate_matches_the_configured_probability(
    config: Any, manifest: Any
) -> None:
    planned = _plan(config, manifest)
    targets = sum(
        1 for item in planned if item.trial.design_extra["tone_type"] == TARGET
    )
    assert targets == config.modules.oddball.n_targets()


def test_every_target_has_its_run_of_standards_before_it(
    config: Any, manifest: Any
) -> None:
    """Including the first one: a deviant with no established standard in front
    of it is not a deviant, it is the beginning of the stream."""
    planned = _plan(config, manifest)
    gaps = target_gaps(planned)
    assert min(gaps) >= config.modules.oddball.min_standards_between_targets


@pytest.mark.parametrize("seed", [1, 2, 3, 17, 20260727])
def test_the_constraint_holds_for_every_seed(
    config: Any, manifest: Any, seed: int
) -> None:
    gaps = target_gaps(_plan(config, manifest, seed=seed))
    assert len(gaps) == config.modules.oddball.n_targets()
    assert min(gaps) >= config.modules.oddball.min_standards_between_targets


def test_targets_are_not_pushed_towards_the_end_of_the_stream(
    config: Any, manifest: Any
) -> None:
    """A greedy placement leaves the free space at the end and puts the targets
    there with it; in an attention task the second half is exactly where the
    target rate has to stay what it says it is."""
    planned = _plan(config, manifest)
    half = len(planned) // 2
    first = sum(
        1 for item in planned[:half] if item.trial.design_extra["tone_type"] == TARGET
    )
    second = sum(
        1 for item in planned[half:] if item.trial.design_extra["tone_type"] == TARGET
    )
    # 54 targets over two halves: a split more lopsided than 40/60 would be
    # about ten standard errors out.
    assert abs(first - second) <= 0.2 * (first + second)


def test_the_same_seed_gives_the_same_stream(config: Any, manifest: Any) -> None:
    first = [item.trial.design_extra for item in _plan(config, manifest, seed=11)]
    second = [item.trial.design_extra for item in _plan(config, manifest, seed=11)]
    assert first == second


def test_a_different_seed_gives_a_different_stream(config: Any, manifest: Any) -> None:
    first = [item.trial.design_extra["tone_type"] for item in _plan(config, manifest, seed=11)]
    second = [item.trial.design_extra["tone_type"] for item in _plan(config, manifest, seed=12)]
    assert first != second


def test_every_trial_is_audio_only_in_quiet_and_carries_its_tone(
    config: Any, manifest: Any
) -> None:
    module = config.modules.oddball
    for item in _plan(config, manifest):
        trial = item.trial
        assert trial.module == "oddball"
        assert trial.presentation_mode == "A"
        assert trial.noise_condition == QUIET
        assert trial.snr_db is None
        assert trial.nominal_soa_ms is None
        assert trial.ear == module.ears[0]
        assert item.spec.video_path is None
        assert item.spec.audio_path is not None
        expected = (
            module.target_hz
            if trial.design_extra["tone_type"] == TARGET
            else module.standard_hz
        )
        assert trial.design_extra["tone_hz"] == expected


def test_the_design_extra_is_valid_and_carries_the_nominal_interval(
    config: Any, manifest: Any
) -> None:
    planned = _plan(config, manifest)
    assert planned[0].trial.design_extra["isi_ms"] is None
    low, high = config.modules.oddball.isi_ms
    for item in planned[1:]:
        assert low <= item.trial.design_extra["isi_ms"] <= high
    for item in planned:
        validate_design_extra("oddball", item.trial.design_extra)


def test_a_zero_interval_is_refused_by_the_database_layer() -> None:
    with pytest.raises(DesignExtraError):
        validate_design_extra(
            "oddball", {"tone_type": STANDARD, "tone_hz": 1000.0, "isi_ms": 0.0}
        )


def test_cell_counts_reports_one_row_per_tone_type(config: Any, manifest: Any) -> None:
    counts = cell_counts(_plan(config, manifest))
    assert len(counts) == 2
    assert sum(counts.values()) == config.modules.oddball.n_trials


def test_a_disabled_module_refuses_to_generate(config: Any, manifest: Any) -> None:
    config.modules.oddball.enabled = False
    with pytest.raises(ModuleError, match="enabled false"):
        _plan(config, manifest)


def test_a_missing_tone_names_the_preparation_step(config: Any, manifest: Any) -> None:
    manifest.tones.clear()
    with pytest.raises(ModuleError, match="prepare_stimuli"):
        _plan(config, manifest)


# ------------------------------------------------------- placement and timing


def test_target_positions_are_uniform_over_the_legal_sequences() -> None:
    """Every legal arrangement has to be equally likely, and the cheap way to
    see that is that no position is systematically preferred."""
    rng = random.Random(4)
    tally: Counter[int] = Counter()
    for _ in range(4000):
        for position in target_positions(10, 2, 1, rng):
            tally[position] += 1

    # With n=10, 2 targets and 1 leading standard, the legal positions are 1..9
    # and every one of them should be visited.
    assert set(tally) <= set(range(1, 10))
    assert min(tally.values()) > 0
    # No position may take more than double the mean share; a greedy placement
    # concentrates them far worse than that.
    mean = sum(tally.values()) / len(tally)
    assert max(tally.values()) < 2.0 * mean


def test_a_constraint_that_does_not_fit_is_refused() -> None:
    with pytest.raises(ModuleError, match="deneme gerekir"):
        target_positions(n_trials=10, n_targets=5, min_standards=2, rng=random.Random(0))


def test_the_sequence_has_the_number_of_targets_it_was_asked_for(config: Any) -> None:
    flags = build_sequence(config.modules.oddball, random.Random(7))
    assert len(flags) == config.modules.oddball.n_trials
    assert sum(flags) == config.modules.oddball.n_targets()


def test_intervals_stay_inside_the_configured_range(config: Any) -> None:
    low, high = config.modules.oddball.isi_ms
    intervals = draw_intervals(config.modules.oddball, random.Random(3), 500)
    assert len(intervals) == 500
    assert all(low <= value <= high for value in intervals)
    # Jittered, not fixed: a constant interval is a rhythm and an anticipated
    # target is not a detected one.
    assert len(set(intervals)) > 100


def test_onsets_are_cumulative_from_one_origin() -> None:
    onsets = onset_times([1000.0, 900.0, 1100.0], start_s=10.0)
    assert onsets == pytest.approx([10.0, 11.0, 11.9, 13.0])


# ----------------------------------------------------------------- attribution


WINDOW = (100.0, 800.0)
ONSETS = [10.0, 11.0, 12.0, 13.0]


def test_a_press_belongs_to_the_tone_it_followed() -> None:
    attributed, before = attribute_presses(ONSETS, [11.4], window_ms=WINDOW)
    assert before == 0
    assert attributed[0].trial_index == 1
    assert attributed[0].rt_ms == pytest.approx(400.0)
    assert attributed[0].in_window


@pytest.mark.parametrize(
    ("offset_ms", "in_window"),
    [(99.5, False), (100.5, True), (450.0, True), (799.5, True), (800.5, False)],
)
def test_the_window_edges_are_where_the_config_puts_them(
    offset_ms: float, in_window: bool
) -> None:
    """Half a millisecond either side of each edge.  A press landing on the
    boundary to the microsecond is decided by the last bit of a float, and no
    part of the design leans on which way it goes."""
    attributed, _ = attribute_presses(
        ONSETS, [10.0 + offset_ms / 1000.0], window_ms=WINDOW
    )
    assert attributed[0].in_window is in_window
    assert attributed[0].trial_index == 0


def test_a_press_before_the_first_tone_belongs_to_no_trial() -> None:
    attributed, before = attribute_presses(ONSETS, [9.5], window_ms=WINDOW)
    assert attributed == []
    assert before == 1


def test_two_presses_on_one_tone_are_both_kept() -> None:
    attributed, _ = attribute_presses(ONSETS, [10.2, 10.5], window_ms=WINDOW)
    assert [press.trial_index for press in attributed] == [0, 0]


def test_a_late_press_lands_on_the_next_tone_not_the_previous_one() -> None:
    """A press 950 ms after tone 0 is 950 ms late for it and 50 ms early for
    tone 1 — outside both windows, and attributed to the one it followed."""
    attributed, _ = attribute_presses(ONSETS, [10.95], window_ms=WINDOW)
    assert attributed[0].trial_index == 0
    assert not attributed[0].in_window


# -------------------------------------------------------------------- measures


def _row(
    trial_id: int,
    tone_type: str,
    *,
    response: bool = False,
    category: str | None = None,
    rt_ms: float | None = None,
) -> dict[str, Any]:
    return {
        "module": "oddball",
        "trial_id": trial_id,
        "oddball_tone_type": tone_type,
        "response_id": 1 if response else None,
        "category": category,
        "is_correct": None,
        "rt_from_burst_ms": rt_ms,
    }


def test_the_four_outcomes_come_out_of_the_rows() -> None:
    rows = [
        _row(1, TARGET, response=True, rt_ms=300.0),
        _row(2, TARGET),
        _row(3, STANDARD, response=True, rt_ms=400.0),
        _row(4, STANDARD),
    ]
    assert [outcome.outcome for outcome in trial_outcomes(rows)] == [
        HIT,
        MISS,
        FALSE_ALARM,
        CORRECT_REJECTION,
    ]


def test_a_press_outside_the_window_changes_no_outcome() -> None:
    rows = [
        _row(1, TARGET, response=True, category=OUTSIDE_WINDOW, rt_ms=900.0),
        _row(2, STANDARD, response=True, category=OUTSIDE_WINDOW, rt_ms=850.0),
    ]
    outcomes = trial_outcomes(rows)
    assert [outcome.outcome for outcome in outcomes] == [MISS, CORRECT_REJECTION]
    assert count_outcomes(outcomes).outside_window == 2


def test_a_second_press_on_the_same_tone_does_not_become_a_second_hit() -> None:
    rows = [
        _row(1, TARGET, response=True, rt_ms=300.0),
        _row(1, TARGET, response=True, rt_ms=500.0),
    ]
    counts = count_outcomes(trial_outcomes(rows))
    assert counts.hits == 1
    assert counts.n_trials == 1


def test_rows_of_other_modules_are_ignored() -> None:
    rows = [_row(1, TARGET, response=True, rt_ms=300.0), {"module": "mcgurk"}]
    assert len(trial_outcomes(rows)) == 1


def test_an_unknown_tone_type_is_an_error() -> None:
    with pytest.raises(ModuleError, match="ton tipi"):
        trial_outcomes([_row(1, "beep")])


def test_d_prime_matches_the_hand_computed_value() -> None:
    """54 targets with 48 hits, 246 standards with 12 false alarms.  With the
    log-linear correction: h = 48.5/55 = 0.8818, f = 12.5/247 = 0.0506."""
    measures = detection_measures(
        Counts(hits=48, misses=6, false_alarms=12, correct_rejections=234)
    )
    assert measures.hit_rate == pytest.approx(48 / 54)
    assert measures.false_alarm_rate == pytest.approx(12 / 246)
    # z(0.88182) = 1.1846, z(0.05061) = -1.6396
    assert measures.d_prime == pytest.approx(2.824, abs=0.005)
    assert measures.criterion == pytest.approx(0.2275, abs=0.005)


def test_a_perfect_performance_gives_a_finite_sensitivity() -> None:
    """Without the correction this is z(1) - z(0), which is not a number and
    would take the participant out of every group mean they belong to."""
    measures = detection_measures(
        Counts(hits=54, misses=0, false_alarms=0, correct_rejections=246)
    )
    assert measures.hit_rate == 1.0
    assert measures.false_alarm_rate == 0.0
    assert 3.0 < measures.d_prime < 6.0


def test_pressing_at_everything_gives_no_sensitivity_and_an_extreme_criterion() -> None:
    """A participant who presses at every tone has demonstrated nothing about
    detection, and d' says so — but not by coming out at exactly zero.

    The log-linear correction adds the same 0.5 to both counts while the totals
    differ (54 targets, 246 standards), so the corrected hit rate moves further
    from 1 than the false-alarm rate does and d' lands slightly negative.  That
    is a property of the correction, not a finding about the participant; the
    criterion is what identifies them.
    """
    measures = detection_measures(
        Counts(hits=54, misses=0, false_alarms=246, correct_rejections=0)
    )
    assert abs(measures.d_prime) < 1.0
    assert measures.criterion < -2.0


def test_a_conservative_and_a_liberal_participant_differ_in_criterion_only() -> None:
    conservative = detection_measures(
        Counts(hits=27, misses=27, false_alarms=2, correct_rejections=244)
    )
    liberal = detection_measures(
        Counts(hits=52, misses=2, false_alarms=60, correct_rejections=186)
    )
    assert conservative.d_prime == pytest.approx(liberal.d_prime, abs=0.35)
    assert conservative.criterion > liberal.criterion


def test_a_stream_with_no_standard_has_no_false_alarm_rate() -> None:
    with pytest.raises(ModuleError, match="hesaplanamaz"):
        detection_measures(Counts(hits=3, misses=1))


def test_the_reaction_time_is_summarised_over_hits_only() -> None:
    rows = [
        _row(1, TARGET, response=True, rt_ms=300.0),
        _row(2, TARGET, response=True, rt_ms=500.0),
        _row(3, STANDARD, response=True, rt_ms=700.0),
        _row(4, STANDARD),
    ]
    measures = measures_from_rows(rows)
    assert measures.n_rt == 2
    assert measures.mean_rt_ms == pytest.approx(400.0)


def test_the_summary_names_every_outcome(config: Any) -> None:
    rows = [
        _row(1, TARGET, response=True, rt_ms=300.0),
        _row(2, TARGET),
        _row(3, STANDARD, response=True, rt_ms=400.0),
        _row(4, STANDARD),
    ]
    text = summarise_measures(rows)
    for expected in ("Isabet", "Kaçırma", "Yanlış alarm", "Doğru ret", "d'"):
        assert expected in text


def test_an_empty_run_summarises_without_dividing_by_zero() -> None:
    assert "deneme yok" in summarise_measures([])


# --------------------------------------------------------------- config gates


def test_a_response_window_longer_than_the_shortest_interval_is_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["oddball"]["response_window_ms"] = [100, 950]
    with pytest.raises(ConfigError, match="iki tona birden"):
        _load(write_config, data)


def test_an_inverted_response_window_is_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["oddball"]["response_window_ms"] = [500, 200]
    with pytest.raises(ConfigError, match="response_window_ms"):
        _load(write_config, data)


def test_a_window_shorter_than_the_tone_is_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["oddball"]["response_window_ms"] = [10, 40]
    with pytest.raises(ConfigError, match="ton süresi"):
        _load(write_config, data)


def test_two_ears_are_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["oddball"]["ears"] = ["left", "right"]
    with pytest.raises(ConfigError, match="bir değer içermeli"):
        _load(write_config, data)


def test_targets_that_cannot_all_have_their_leading_standards_are_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    """40 targets out of 100 trials at a spacing of two needs 120."""
    data = copy.deepcopy(config_dict)
    data["modules"]["oddball"]["n_trials"] = 100
    data["modules"]["oddball"]["target_probability"] = 0.4
    with pytest.raises(ConfigError, match="deneme gerekir"):
        _load(write_config, data)


def test_the_shipped_design_leaves_room_for_the_constraint(config: Any) -> None:
    module = config.modules.oddball
    needed = module.n_targets() * (1 + module.min_standards_between_targets)
    assert needed <= module.n_trials


def test_the_tones_the_module_needs_are_derived_from_it(config: Any) -> None:
    assert config.required_tones() == [
        config.modules.oddball.standard_hz,
        config.modules.oddball.target_hz,
    ]


def test_a_disabled_module_asks_for_no_tones(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["oddball"]["enabled"] = False
    data["session"]["module_order"] = [
        name for name in data["session"]["module_order"] if name != "oddball"
    ]
    # The cross-hearing check reuses the standard tone (Adım 8b-ii), so disable
    # it too to isolate oddball's contribution — which should then be nothing.
    data["cross_hearing_check"]["enabled"] = False
    assert _load(write_config, data).required_tones() == []
