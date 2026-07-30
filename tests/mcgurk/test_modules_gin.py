"""Modül 6 — the design it presents, where a press lands, and the threshold.

Everything here runs in CI: no PsychoPy, no sound card.  What the stream runner
does with the module is in ``tests/test_modules_stream_gin.py`` (hardware).

The acceptance criteria come from ``docs/EK_GIN.docx`` §6.6: thirty prepared
segments in a seeded order, a press attributed to the gap it followed, a
threshold defined as the shortest duration detected on at least four of its six
presentations, and a false-alarm count reported beside it.
"""

from __future__ import annotations

import copy
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from mcgurk.config.loader import ConfigError, load_config
from mcgurk.db.design import DesignExtraError, validate_design_extra
from mcgurk.modules.base import ModuleError
from mcgurk.modules.gin import (
    FALSE_ALARM,
    HIT,
    GapDetection,
    attribute_presses,
    category_of,
    cell_counts,
    detection_by_duration,
    ears_presented,
    gap_onsets,
    measures_from_rows,
    plan_trials,
    resolve_ear,
    stream_duration_s,
    summarise_measures,
    threshold_ms,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STIMULI = Path("stimuli")
SEED = 20260729
WINDOW = (100.0, 900.0)


@pytest.fixture
def config(write_config: Any, config_dict: dict[str, Any]) -> Any:
    return load_config(write_config(config_dict), check_filesystem=False)


@pytest.fixture
def manifest(config: Any, manifest_factory: Any) -> Any:
    return manifest_factory(config)


def _plan(config: Any, manifest: Any, seed: int = SEED, ear: str = "right") -> list:
    return plan_trials(config, manifest, seed=seed, stimuli_root=STIMULI, ear=ear)


def _load(write_config: Any, data: dict[str, Any]) -> Any:
    return load_config(write_config(data), check_filesystem=False)


def _row(**fields: Any) -> dict[str, Any]:
    """One ``v_trials_flat`` row, with the columns the measures read."""
    row: dict[str, Any] = {
        "module": "gin",
        "trial_id": 1,
        "ear": "right",
        "gin_gap_durations_ms": "[]",
        "category": None,
        "event_index": None,
        "rt_from_burst_ms": None,
    }
    row.update(fields)
    return row


def _trial_rows(trial_id: int, durations: list[float], detected: dict[int, float],
                false_alarms: int = 0) -> list[dict[str, Any]]:
    """A segment's rows: one per response, or one bare row when there are none."""
    import json

    payload = json.dumps(durations)
    rows: list[dict[str, Any]] = []
    for index, rt in detected.items():
        rows.append(
            _row(
                trial_id=trial_id,
                gin_gap_durations_ms=payload,
                category=HIT,
                event_index=index,
                rt_from_burst_ms=rt,
            )
        )
    for _ in range(false_alarms):
        rows.append(
            _row(trial_id=trial_id, gin_gap_durations_ms=payload, category=FALSE_ALARM)
        )
    if not rows:
        rows.append(_row(trial_id=trial_id, gin_gap_durations_ms=payload))
    return rows


# ---------------------------------------------------------------- the design


def test_the_generator_produces_exactly_what_the_config_estimated(
    config: Any, manifest: Any
) -> None:
    assert len(_plan(config, manifest)) == config.trial_counts()["gin"]


def test_every_prepared_segment_is_presented_once(config: Any, manifest: Any) -> None:
    indices = [item.trial.design_extra["segment_index"] for item in _plan(config, manifest)]
    assert sorted(indices) == [entry.index for entry in manifest.gin_segments]


def test_the_gaps_come_from_the_manifest_not_from_a_generator(
    config: Any, manifest: Any
) -> None:
    """The segments were cut offline and measured from disk (Adım 2); the module
    reads those positions rather than re-deriving them, so what the participant
    hears and what the database says cannot disagree."""
    by_index = {entry.index: entry for entry in manifest.gin_segments}
    for item in _plan(config, manifest):
        entry = by_index[item.trial.design_extra["segment_index"]]
        assert item.trial.design_extra["gap_onsets_s"] == list(entry.gap_onsets_s)
        assert item.trial.design_extra["gap_durations_ms"] == list(entry.gap_durations_ms)


def test_the_total_number_of_gaps_matches_the_config(config: Any, manifest: Any) -> None:
    planned = _plan(config, manifest)
    assert sum(len(onsets) for onsets in gap_onsets(planned)) == (
        config.modules.gin.total_gaps()
    )


def test_every_gap_duration_appears_its_configured_number_of_times(
    config: Any, manifest: Any
) -> None:
    counts = Counter(
        duration
        for item in _plan(config, manifest)
        for duration in item.trial.design_extra["gap_durations_ms"]
    )
    module = config.modules.gin
    assert set(counts) == set(module.gap_durations_ms)
    assert set(counts.values()) == {module.reps_per_gap}


def test_the_same_seed_gives_the_same_order(config: Any, manifest: Any) -> None:
    def order(seed: int) -> list[int]:
        return [item.trial.design_extra["segment_index"] for item in _plan(config, manifest, seed)]

    assert order(SEED) == order(SEED)
    assert order(SEED) != order(SEED + 1)


def test_the_order_does_not_depend_on_the_other_modules(
    config: Any, manifest: Any
) -> None:
    before = [item.trial.design_extra["segment_index"] for item in _plan(config, manifest)]
    config.session.module_order = [
        "practice", "gin", "mcgurk", "avsr", "tbw", "oddball", "dichotic",
    ]
    assert [
        item.trial.design_extra["segment_index"] for item in _plan(config, manifest)
    ] == before


def test_the_row_says_monaural_no_video_and_no_noise_condition(
    config: Any, manifest: Any
) -> None:
    for item in _plan(config, manifest, ear="left"):
        trial = item.trial
        assert trial.module == "gin"
        assert trial.presentation_mode == "A"
        assert trial.ear == "left"
        assert trial.visual_token is None and trial.audio_token is None
        assert trial.snr_db is None
        # NULL, not "quiet": the stimulus *is* noise, so "presented in noise"
        # does not describe a condition here.
        assert trial.noise_condition is None
        assert trial.nominal_soa_ms is None
        assert item.spec.video_path is None
        assert item.spec.audio_path is not None
        assert item.spec.ear == "left"


def test_every_trial_carries_a_valid_design_extra(config: Any, manifest: Any) -> None:
    for item in _plan(config, manifest):
        validate_design_extra("gin", item.trial.design_extra)


def test_the_design_extra_needs_the_segment_index(config: Any, manifest: Any) -> None:
    """Without it a trial cannot be traced back to the manifest entry whose gaps
    were measured from disk."""
    extra = dict(_plan(config, manifest)[0].trial.design_extra)
    extra.pop("segment_index")
    with pytest.raises(DesignExtraError, match="segment_index"):
        validate_design_extra("gin", extra)


def test_a_catch_segment_is_a_legitimate_trial(config: Any, manifest: Any) -> None:
    """A segment with no gaps at all is what the false-alarm rate is measured
    against, so it has to survive into the plan with an empty — not missing —
    pair of lists."""
    empty = [
        item
        for item in _plan(config, manifest)
        if not item.trial.design_extra["gap_onsets_s"]
    ]
    assert empty, "hazırlanmış sette yakalama segmenti yok"
    for item in empty:
        assert item.trial.design_extra["gap_durations_ms"] == []
        validate_design_extra("gin", item.trial.design_extra)


def test_a_disabled_module_generates_nothing(
    write_config: Any, config_dict: dict[str, Any], manifest_factory: Any
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["gin"]["enabled"] = False
    data["session"]["module_order"] = [
        name for name in data["session"]["module_order"] if name != "gin"
    ]
    config = _load(write_config, data)
    with pytest.raises(ModuleError, match="enabled false"):
        plan_trials(
            config, manifest_factory(config), seed=SEED, stimuli_root=STIMULI,
            ear="right",
        )


def test_a_prepared_set_that_does_not_match_the_design_is_refused(
    config: Any, manifest: Any
) -> None:
    """A config changed after the stimuli were prepared would put one design in
    the report and another in the participant's ears."""
    manifest.gin_segments = manifest.gin_segments[:-1]
    with pytest.raises(ModuleError, match="segment"):
        _plan(config, manifest)


def test_a_wrong_gap_distribution_is_refused(config: Any, manifest: Any) -> None:
    manifest.gin_segments[0].gap_durations_ms = [
        99.0 for _ in manifest.gin_segments[0].gap_durations_ms
    ]
    with pytest.raises(ModuleError, match="dağılımı"):
        _plan(config, manifest)


def test_an_empty_prepared_set_names_the_tool_that_fixes_it(
    config: Any, manifest: Any
) -> None:
    manifest.gin_segments = []
    with pytest.raises(ModuleError, match="prepare_stimuli"):
        _plan(config, manifest)


def test_the_duration_estimate_follows_the_design(config: Any, manifest: Any) -> None:
    module = config.modules.gin
    planned = _plan(config, manifest)
    expected = module.lead_in_s + len(planned) * (
        module.segment_duration_s + module.inter_segment_interval_s
    )
    assert stream_duration_s(planned, module) == pytest.approx(expected)


def test_cell_counts_group_by_gap_count(config: Any, manifest: Any) -> None:
    counts = cell_counts(_plan(config, manifest))
    assert sum(counts.values()) == config.trial_counts()["gin"]
    assert all(ear == "right" for _, _, ear, _ in counts)
    assert ("0 boşluk", "geniş bantlı gürültü", "right", "—") in counts


# -------------------------------------------------------------- ear selection


def test_the_good_ear_has_to_be_given(config: Any, manifest: Any) -> None:
    """Picking a side silently would mean testing whichever ear the code
    defaulted to, and the result would look like a measurement."""
    with pytest.raises(ModuleError, match="iyi kulağına"):
        plan_trials(config, manifest, seed=SEED, stimuli_root=STIMULI)


def test_a_fixed_ear_needs_no_argument(
    write_config: Any, config_dict: dict[str, Any], manifest_factory: Any
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["gin"]["ear_selection"] = "fixed"
    data["modules"]["gin"]["fixed_ear"] = "left"
    config = _load(write_config, data)
    planned = plan_trials(
        config, manifest_factory(config), seed=SEED, stimuli_root=STIMULI
    )
    assert ears_presented(planned) == ["left"]


def test_both_ears_doubles_the_module(
    write_config: Any, config_dict: dict[str, Any], manifest_factory: Any
) -> None:
    """EK_GIN's alternative: the same segments to each ear in turn, which costs
    another four minutes."""
    data = copy.deepcopy(config_dict)
    data["modules"]["gin"]["ear_selection"] = "both"
    config = _load(write_config, data)
    planned = plan_trials(
        config, manifest_factory(config), seed=SEED, stimuli_root=STIMULI
    )
    assert len(planned) == 2 * config.modules.gin.n_segments
    assert len(planned) == config.trial_counts()["gin"]
    assert sorted(ears_presented(planned)) == ["left", "right"]

    # A different order per ear: the same one twice would let the second run be
    # answered from memory of the first.
    half = len(planned) // 2
    first = [item.trial.design_extra["segment_index"] for item in planned[:half]]
    second = [item.trial.design_extra["segment_index"] for item in planned[half:]]
    assert sorted(first) == sorted(second)
    assert first != second


def test_a_diotic_ear_is_refused(config: Any, manifest: Any) -> None:
    """GIN is monaural; "both" as a side means diotic, which is a different
    measure."""
    with pytest.raises(ModuleError, match="monaural"):
        _plan(config, manifest, ear="both")


def test_resolve_ear_reports_what_the_config_allows(config: Any) -> None:
    module = config.modules.gin
    assert resolve_ear(module, "left") == ["left"]
    module.ear_selection = "both"
    assert resolve_ear(module) == ["left", "right"]


# ---------------------------------------------------------------- attribution


def test_a_press_belongs_to_the_gap_it_followed() -> None:
    presses = attribute_presses([1.0, 3.0, 5.0], [3.4], window_ms=WINDOW)
    assert presses[0].gap_index == 1
    assert presses[0].rt_ms == pytest.approx(400.0)
    assert presses[0].in_window


@pytest.mark.parametrize(
    ("rt_s", "in_window"),
    [
        (0.099, False),  # faster than a decision to that gap
        (0.100, True),   # the lower edge counts
        (0.900, True),   # so does the upper
        (0.901, False),
    ],
)
def test_the_window_edges_are_inclusive(rt_s: float, in_window: bool) -> None:
    press = attribute_presses([1.0], [1.0 + rt_s], window_ms=WINDOW)[0]
    assert press.gap_index == 0
    assert press.in_window is in_window


def test_a_late_press_is_a_false_alarm_on_the_gap_it_followed() -> None:
    """Not OUTSIDE_WINDOW as in oddball: a press 2 s after a gap answered no
    gap, and that is what a false alarm is here."""
    press = attribute_presses([1.0], [3.0], window_ms=WINDOW)[0]
    assert press.gap_index == 0 and not press.in_window
    assert category_of(press) == FALSE_ALARM


def test_a_press_before_the_first_gap_belongs_to_no_gap() -> None:
    press = attribute_presses([2.0], [0.5], window_ms=WINDOW)[0]
    assert press.gap_index is None
    assert press.rt_ms is None
    assert category_of(press) == FALSE_ALARM


def test_every_press_of_a_catch_segment_is_a_false_alarm() -> None:
    """A segment with no gaps is what the false-alarm rate is measured against;
    dropping its presses would hide the participant it exists to find."""
    presses = attribute_presses([], [0.5, 3.2, 5.9], window_ms=WINDOW)
    assert [press.gap_index for press in presses] == [None, None, None]
    assert {category_of(press) for press in presses} == {FALSE_ALARM}


def test_a_press_cannot_answer_two_gaps() -> None:
    """The config keeps the window shorter than the closest gap spacing, so the
    press after the second gap is attributed to the second one only."""
    presses = attribute_presses([1.0, 2.05], [2.4], window_ms=WINDOW)
    assert len(presses) == 1
    assert presses[0].gap_index == 1
    assert presses[0].rt_ms == pytest.approx(350.0)


def test_a_detection_is_a_hit() -> None:
    press = attribute_presses([1.0], [1.3], window_ms=WINDOW)[0]
    assert category_of(press) == HIT


# -------------------------------------------------------------------- measures


def test_detection_counts_are_grouped_by_gap_duration() -> None:
    rows = _trial_rows(1, [5.0, 10.0], detected={0: 300.0})
    rows += _trial_rows(2, [5.0, 20.0], detected={1: 250.0})
    by_duration = detection_by_duration(rows)
    assert by_duration == [
        GapDetection(duration_ms=5.0, n_presented=2, n_detected=1),
        GapDetection(duration_ms=10.0, n_presented=1, n_detected=0),
        GapDetection(duration_ms=20.0, n_presented=1, n_detected=1),
    ]


def test_a_gap_with_no_press_is_a_miss_not_a_missing_row() -> None:
    """``v_trials_flat`` LEFT JOINs responses, so a segment nobody answered is
    still one row — and its gaps still count as presented."""
    rows = _trial_rows(1, [5.0, 10.0], detected={})
    assert detection_by_duration(rows) == [
        GapDetection(duration_ms=5.0, n_presented=1, n_detected=0),
        GapDetection(duration_ms=10.0, n_presented=1, n_detected=0),
    ]


def test_the_threshold_is_the_shortest_duration_meeting_the_criterion() -> None:
    by_duration = [
        GapDetection(duration_ms=2.0, n_presented=6, n_detected=1),
        GapDetection(duration_ms=4.0, n_presented=6, n_detected=3),
        GapDetection(duration_ms=6.0, n_presented=6, n_detected=4),
        GapDetection(duration_ms=8.0, n_presented=6, n_detected=6),
    ]
    assert threshold_ms(by_duration, hits=4, presentations=6) == 6.0


def test_the_threshold_takes_the_shortest_qualifying_duration() -> None:
    """A participant can miss 4 ms and catch 3 ms by chance.  The rule is
    "shortest duration detected 4 of 6", not "shortest run of them" — taking the
    longer one would be a different, undocumented criterion."""
    by_duration = [
        GapDetection(duration_ms=3.0, n_presented=6, n_detected=4),
        GapDetection(duration_ms=4.0, n_presented=6, n_detected=2),
        GapDetection(duration_ms=6.0, n_presented=6, n_detected=6),
    ]
    assert threshold_ms(by_duration, hits=4, presentations=6) == 3.0


def test_a_threshold_that_was_never_reached_is_none_not_the_longest_gap() -> None:
    by_duration = [
        GapDetection(duration_ms=2.0, n_presented=6, n_detected=0),
        GapDetection(duration_ms=20.0, n_presented=6, n_detected=3),
    ]
    assert threshold_ms(by_duration, hits=4, presentations=6) is None


def test_an_incomplete_run_is_not_scored_against_a_fixed_criterion() -> None:
    """"4 of 6" cannot be evaluated on three presentations; an aborted run
    reports the counts without inventing a threshold."""
    by_duration = [GapDetection(duration_ms=2.0, n_presented=3, n_detected=3)]
    assert threshold_ms(by_duration, hits=4, presentations=6) is None


def test_the_measures_carry_the_criterion_and_the_false_alarms(config: Any) -> None:
    module = config.modules.gin
    rows = _trial_rows(1, [2.0], detected={}, false_alarms=2)
    rows += _trial_rows(2, [20.0], detected={0: 320.0})
    rows += _trial_rows(3, [], detected={}, false_alarms=1)

    measures = measures_from_rows(rows, module)
    assert measures.n_trials == 3
    assert measures.n_gaps == 2
    assert measures.n_detected == 1
    assert measures.n_false_alarms == 3
    assert measures.detection_rate == pytest.approx(0.5)
    assert measures.criterion == module.threshold_criterion
    assert measures.mean_rt_ms == pytest.approx(320.0)
    assert measures.ears == ("right",)


def test_measures_ignore_other_modules_rows(config: Any) -> None:
    rows = _trial_rows(1, [5.0], detected={0: 200.0})
    rows.append(_row(module="oddball", trial_id=99, category="OUTSIDE_WINDOW"))
    assert measures_from_rows(rows, config.modules.gin).n_trials == 1


def test_a_hit_without_its_gap_index_is_an_error(config: Any) -> None:
    """The threshold is computed per gap duration; a hit that does not name its
    gap cannot enter it, and silently dropping it would lower the rate."""
    rows = [_row(gin_gap_durations_ms="[5.0]", category=HIT, event_index=None)]
    with pytest.raises(ModuleError, match="event_index"):
        measures_from_rows(rows, config.modules.gin)


def test_a_gap_index_outside_the_trial_is_an_error(config: Any) -> None:
    rows = [_row(gin_gap_durations_ms="[5.0]", category=HIT, event_index=3)]
    with pytest.raises(ModuleError, match="event_index"):
        measures_from_rows(rows, config.modules.gin)


def test_an_unknown_category_is_an_error(config: Any) -> None:
    rows = [_row(gin_gap_durations_ms="[5.0]", category="FUSION")]
    with pytest.raises(ModuleError, match="bilinmeyen kategori"):
        measures_from_rows(rows, config.modules.gin)


def test_the_summary_reports_the_threshold_beside_the_false_alarms(
    config: Any,
) -> None:
    module = config.modules.gin
    rows: list[dict[str, Any]] = []
    for trial_id, duration in enumerate(module.gap_durations_ms, start=1):
        detected = {0: 300.0} if duration >= 6.0 else {}
        for rep in range(module.reps_per_gap):
            rows += _trial_rows(trial_id * 100 + rep, [duration], detected=detected)
    rows += _trial_rows(999, [], detected={}, false_alarms=4)

    text = summarise_measures(rows, module)
    assert "6 ms" in text
    assert "<-- eşik" in text
    assert "Yanlış alarm           : 4" in text


def test_the_summary_says_so_when_the_threshold_was_not_reached(config: Any) -> None:
    module = config.modules.gin
    rows = _trial_rows(1, [2.0], detected={})
    text = summarise_measures(rows, module)
    assert "ulaşılamadı" in text


# ---------------------------------------------------------------- config gates


def test_a_window_reaching_the_next_gap_is_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    """A press inside one gap's window would also be inside the previous gap's,
    and which one it counted for would depend on the code."""
    data = copy.deepcopy(config_dict)
    data["modules"]["gin"]["response_window_ms"] = [100, 1100]
    with pytest.raises(ConfigError, match="iki boşluğa birden"):
        _load(write_config, data)


def test_a_backwards_window_is_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["gin"]["response_window_ms"] = [500, 200]
    with pytest.raises(ConfigError, match="artan olmalı"):
        _load(write_config, data)


def test_a_diotic_fixed_ear_is_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["gin"]["ear_selection"] = "fixed"
    data["modules"]["gin"]["fixed_ear"] = "both"
    with pytest.raises(ConfigError, match="monaural"):
        _load(write_config, data)


def test_both_ears_shows_up_in_the_duration_estimate(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    data = copy.deepcopy(config_dict)
    monaural = _load(write_config, data).modules.gin.estimated_duration_s()
    data["modules"]["gin"]["ear_selection"] = "both"
    binaural = _load(write_config, data).modules.gin.estimated_duration_s()
    assert binaural == pytest.approx(2 * monaural)
