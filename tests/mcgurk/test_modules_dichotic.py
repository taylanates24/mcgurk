"""Modül 5 — the design it generates, what a response means, and the index.

Everything here runs in CI: no PsychoPy, no sound card, no prepared set.  What
the trial loop does with the module is in ``tests/test_modules_block_dichotic.py``
(hardware).

The acceptance criteria of this file come from ``docs/EK_DIKOTIK_DINLEME.docx``
§6.5: six pairs presented in a seeded order, no correct answer, a report
attributed to the ear whose token it matches, and the laterality index
[(right − left) / (right + left)] × 100 over the trials that were answered.
"""

from __future__ import annotations

import copy
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from mcgurk.config.loader import ConfigError, load_config
from mcgurk.db.design import DesignExtraError, validate_design_extra
from mcgurk.modules.base import QUIET, ModuleError
from mcgurk.modules.dichotic import (
    LEFT,
    NONE,
    OTHER,
    RIGHT,
    EarAdvantage,
    categorise,
    categorise_for,
    cell_counts,
    design_cells,
    ear_advantage,
    ear_advantage_by_pair,
    mean_rt_ms,
    plan_trials,
    summarise_measures,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STIMULI = Path("stimuli")
SEED = 20260728


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


def _row(**fields: Any) -> dict[str, Any]:
    """One ``v_trials_flat`` row, with the columns the measures read."""
    row: dict[str, Any] = {
        "module": "dichotic",
        "condition_label": "Left-ba/Right-da",
        "category": None,
        "rt_from_burst_ms": None,
        "rt_from_prompt_ms": None,
    }
    row.update(fields)
    return row


# ---------------------------------------------------------------- the design


def test_the_generator_produces_exactly_what_the_config_estimated(
    config: Any, manifest: Any
) -> None:
    assert len(_plan(config, manifest)) == config.trial_counts()["dichotic"]


def test_every_pair_is_presented_the_configured_number_of_times(
    config: Any, manifest: Any
) -> None:
    module = config.modules.dichotic
    counts = Counter(
        (item.trial.design_extra["left_token"], item.trial.design_extra["right_token"])
        for item in _plan(config, manifest)
    )
    assert set(counts) == {(pair.left, pair.right) for pair in module.pairs}
    assert set(counts.values()) == {module.reps}


def test_nothing_is_crossed_with_reps(config: Any) -> None:
    """No noise, no ear factor: the pair itself is the lateralisation, and the
    competition between the ears is the difficult condition (§6.5)."""
    module = config.modules.dichotic
    cells, reps = design_cells(module)
    assert len(cells) == len(module.pairs)
    assert reps == [module.reps] * len(module.pairs)


def test_the_same_seed_gives_the_same_order(config: Any, manifest: Any) -> None:
    def order(seed: int) -> list[str]:
        return [item.trial.condition_label for item in _plan(config, manifest, seed)]

    assert order(SEED) == order(SEED)
    assert order(SEED) != order(SEED + 1)


def test_the_order_does_not_depend_on_the_other_modules(
    config: Any, manifest: Any
) -> None:
    """The RNG stream is derived per module, so moving dichotic in
    ``session.module_order`` cannot change its trial order."""
    before = [item.trial.condition_label for item in _plan(config, manifest)]
    config.session.module_order = [
        "practice",
        "dichotic",
        "mcgurk",
        "avsr",
        "tbw",
        "oddball",
        "gin",
    ]
    assert [item.trial.condition_label for item in _plan(config, manifest)] == before


def test_block_shuffle_spreads_the_pairs_over_the_module(
    config: Any, manifest: Any
) -> None:
    """Round by round: every pair appears once per round, so a participant who
    tires halfway through affects every pair equally rather than whichever ones
    happened to be scheduled late."""
    planned = _plan(config, manifest)
    module = config.modules.dichotic
    size = len(module.pairs)
    labels = [item.trial.condition_label for item in planned]
    rounds = [labels[start : start + size] for start in range(0, len(labels), size)]

    assert len(rounds) == module.reps
    for members in rounds:
        assert sorted(members) == sorted({item.trial.condition_label for item in planned})
    # Shuffled inside the round, or the pairs would run in config order.
    assert len({tuple(members) for members in rounds}) > 1


def test_every_trial_resolves_to_a_prepared_stereo_file(
    config: Any, manifest: Any
) -> None:
    for item in _plan(config, manifest):
        spec = item.spec
        assert spec.video_path is None  # no visual cue to lipread (§6.5)
        assert spec.audio_path is not None
        left = item.trial.design_extra["left_token"]
        right = item.trial.design_extra["right_token"]
        assert spec.audio_path.name == f"Left-{left}_Right-{right}.wav"
        # A stereo file must not be routed anywhere: engine.audio refuses it,
        # and routing it would destroy what it was prepared for.
        assert spec.ear == "both"
        assert spec.mode == "A"
        assert spec.nominal_soa_ms is None


def test_both_ears_sit_on_one_burst_time(config: Any, manifest: Any) -> None:
    """Adım 2 aligns the two channels to a common burst; the RT reference is
    that burst, so a per-ear onset difference would enter the reaction time."""
    bursts = {item.spec.audio_burst_s for item in _plan(config, manifest)}
    assert len(bursts) == 1


def test_the_row_says_quiet_both_ears_and_no_soa(config: Any, manifest: Any) -> None:
    for item in _plan(config, manifest):
        trial = item.trial
        assert trial.module == "dichotic"
        assert trial.presentation_mode == "A"
        # Sound reaches both ears; *what* each receives is the pair.  NULL would
        # say "not applicable", which is not true here.
        assert trial.ear == "both"
        assert trial.snr_db is None
        assert trial.noise_condition == QUIET
        assert trial.nominal_soa_ms is None
        # Two simultaneous tokens, so there is no single audio_token.
        assert trial.audio_token is None
        assert trial.visual_token is None


def test_every_trial_carries_a_valid_design_extra(config: Any, manifest: Any) -> None:
    for item in _plan(config, manifest):
        validate_design_extra("dichotic", item.trial.design_extra)


def test_the_design_extra_needs_the_speaker(config: Any, manifest: Any) -> None:
    """The config snapshot only pins the speaker down while the strategy is
    ``fixed`` (§F.4), so the trial itself has to carry it."""
    extra = dict(_plan(config, manifest)[0].trial.design_extra)
    assert extra["speaker_id"] == config.modules.dichotic.speaker_id
    extra.pop("speaker_id")
    with pytest.raises(DesignExtraError, match="speaker_id"):
        validate_design_extra("dichotic", extra)


def test_the_speaker_can_be_overridden_per_participant(
    config: Any, manifest: Any
) -> None:
    planned = plan_trials(
        config, manifest, seed=SEED, stimuli_root=STIMULI, speaker_id=2
    )
    assert {item.trial.design_extra["speaker_id"] for item in planned} == {2}
    assert all("speaker_2" in str(item.spec.audio_path) for item in planned)


def test_a_disabled_module_generates_nothing(
    write_config: Any, config_dict: dict[str, Any], manifest_factory: Any
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["dichotic"]["enabled"] = False
    data["session"]["module_order"] = [
        name for name in data["session"]["module_order"] if name != "dichotic"
    ]
    config = _load(write_config, data)
    with pytest.raises(ModuleError, match="enabled false"):
        plan_trials(
            config, manifest_factory(config), seed=SEED, stimuli_root=STIMULI
        )


def test_a_pair_missing_from_the_prepared_set_fails_before_the_session(
    config: Any, manifest: Any
) -> None:
    """Failing here means failing before the participant sits down, which is the
    whole point of resolving every file up front."""
    manifest.dichotic = [
        entry for entry in manifest.dichotic if entry.left_token != "ga"
    ]
    with pytest.raises(ModuleError, match="prepare_stimuli"):
        _plan(config, manifest)


def test_cell_counts_are_built_from_the_plan(config: Any, manifest: Any) -> None:
    counts = cell_counts(_plan(config, manifest))
    module = config.modules.dichotic
    assert len(counts) == len(module.pairs)
    assert set(counts.values()) == {module.reps}
    assert ("Left-ba/Right-da", "L-ba/R-da", "both", QUIET) in counts


# ------------------------------------------------------------- categorisation


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ("ba", LEFT),
        ("BA", LEFT),          # the response set is upper case, the tokens are not
        ("  da  ", RIGHT),
        ("ga", OTHER),         # the third syllable — an intrusion (§6.5)
        ("DIGER", OTHER),      # the free-text option matches neither token
        (None, NONE),
        ("", NONE),
        ("   ", NONE),
    ],
)
def test_a_report_is_attributed_to_the_ear_it_matches(
    response: str | None, expected: str
) -> None:
    assert categorise(response, left_token="ba", right_token="da") == expected


def test_the_category_comes_from_the_chosen_option_not_the_typed_text(
    config: Any, manifest: Any
) -> None:
    """A participant who picked "DİĞER" declined the syllables on the screen.
    Reading their text back into an ear would invent a report they did not give;
    the text is stored verbatim instead."""
    trial = _plan(config, manifest)[0].trial
    free_text_label = config.modules.dichotic.free_text_response
    assert categorise_for(free_text_label, trial) == OTHER


def test_categorise_for_uses_the_tokens_on_the_trial(
    config: Any, manifest: Any
) -> None:
    for item in _plan(config, manifest):
        trial = item.trial
        assert categorise_for(trial.design_extra["left_token"], trial) == LEFT
        assert categorise_for(trial.design_extra["right_token"], trial) == RIGHT


def test_a_trial_without_its_tokens_is_an_error(config: Any, manifest: Any) -> None:
    trial = _plan(config, manifest)[0].trial
    trial.design_extra.pop("right_token")
    with pytest.raises(ModuleError, match="right_token"):
        categorise_for("ba", trial)


# -------------------------------------------------------------------- measures


def test_the_index_is_the_documented_formula() -> None:
    """KAİ = [(Sağ - Sol) / (Sağ + Sol)] x 100 (§6.5).  18 right, 6 left over
    24 lateralised reports is (18-6)/24 x 100 = +50."""
    rows = [_row(category=RIGHT) for _ in range(18)]
    rows += [_row(category=LEFT) for _ in range(6)]
    stats = ear_advantage(rows)
    assert stats.n_lateralised == 24
    assert stats.laterality_index == pytest.approx(50.0)
    assert stats.right_rate == pytest.approx(0.75)
    assert stats.left_rate == pytest.approx(0.25)


def test_a_left_advantage_is_negative() -> None:
    rows = [_row(category=LEFT) for _ in range(9)] + [_row(category=RIGHT)]
    assert ear_advantage(rows).laterality_index == pytest.approx(-80.0)


def test_a_symmetrical_participant_lands_on_zero() -> None:
    rows = [_row(category=LEFT) for _ in range(5)]
    rows += [_row(category=RIGHT) for _ in range(5)]
    assert ear_advantage(rows).laterality_index == pytest.approx(0.0)


def test_a_timeout_is_a_missing_observation_not_a_report() -> None:
    """The opposite of AVSR's rule and for the opposite reason: with no correct
    answer, assigning an unanswered trial to either ear moves the index."""
    rows = [_row(category=RIGHT) for _ in range(6)]
    rows += [_row(category=LEFT) for _ in range(2)]
    rows += [_row(category=None) for _ in range(4)]

    stats = ear_advantage(rows)
    assert stats.n_trials == 12
    assert stats.n_missing == 4
    assert stats.n_answered == 8
    # 4 timeouts changed nothing but their own count.
    assert stats.laterality_index == pytest.approx(50.0)
    assert stats.right_rate == pytest.approx(0.75)


def test_intrusions_are_in_the_denominator_but_not_in_the_index() -> None:
    """A report matching neither syllable is an answer — it belongs in the rates
    — but it names no ear, so it cannot enter [(R-L)/(R+L)]."""
    rows = [_row(category=RIGHT) for _ in range(3)]
    rows += [_row(category=LEFT) for _ in range(1)]
    rows += [_row(category=OTHER) for _ in range(4)]

    stats = ear_advantage(rows)
    assert stats.n_answered == 8
    assert stats.intrusion_rate == pytest.approx(0.5)
    assert stats.right_rate == pytest.approx(0.375)
    assert stats.laterality_index == pytest.approx(50.0)


def test_an_index_with_no_lateralised_report_is_undefined() -> None:
    """Zero would read as "perfectly symmetrical" for a participant who in fact
    reported neither of the syllables presented."""
    stats = ear_advantage([_row(category=OTHER) for _ in range(5)])
    assert stats.laterality_index is None
    assert stats.intrusion_rate == pytest.approx(1.0)


def test_an_empty_run_produces_no_rates() -> None:
    stats = ear_advantage([])
    assert stats == EarAdvantage()
    assert stats.laterality_index is None
    assert stats.left_rate is None
    assert mean_rt_ms([]) is None


def test_other_modules_rows_are_ignored() -> None:
    rows = [_row(category=RIGHT), _row(module="mcgurk", category="FUSION")]
    assert ear_advantage(rows).n_trials == 1


def test_an_unknown_category_is_an_error_not_a_silent_drop() -> None:
    with pytest.raises(ModuleError, match="bilinmeyen kategori"):
        ear_advantage([_row(category="FUSION")])


def test_the_per_pair_tally_would_expose_a_stimulus_artefact() -> None:
    """If every pair containing /ga/ is reported as /ga/ whichever ear it came
    from, the asymmetry is in the tokens rather than in the ears."""
    rows = [_row(condition_label="Left-ga/Right-ba", category=LEFT) for _ in range(5)]
    rows += [_row(condition_label="Left-ba/Right-ga", category=RIGHT) for _ in range(5)]
    by_pair = ear_advantage_by_pair(rows)
    assert set(by_pair) == {"Left-ga/Right-ba", "Left-ba/Right-ga"}
    assert by_pair["Left-ga/Right-ba"].laterality_index == pytest.approx(-100.0)
    assert by_pair["Left-ba/Right-ga"].laterality_index == pytest.approx(100.0)


def test_mean_rt_uses_the_reference_it_is_asked_for() -> None:
    rows = [
        _row(category=LEFT, rt_from_burst_ms=800.0, rt_from_prompt_ms=300.0),
        _row(category=RIGHT, rt_from_burst_ms=1000.0, rt_from_prompt_ms=500.0),
        _row(category=None),  # a timeout contributes to neither
    ]
    assert mean_rt_ms(rows, "rt_from_burst_ms") == pytest.approx(900.0)
    assert mean_rt_ms(rows, "rt_from_prompt_ms") == pytest.approx(400.0)


def test_the_summary_reports_the_index_and_the_missing_trials() -> None:
    rows = [_row(category=RIGHT, rt_from_burst_ms=900.0) for _ in range(6)]
    rows += [_row(category=LEFT) for _ in range(2)]
    rows += [_row(category=None)]
    text = summarise_measures(rows)
    assert "+50.0" in text
    assert "1 yanıtsız" in text
    assert "Karışım yanıtı" in text


def test_the_summary_says_so_when_the_index_is_undefined() -> None:
    text = summarise_measures([_row(category=OTHER)])
    assert "tanımsız" in text


# ---------------------------------------------------------------- config gates


def test_a_pair_with_the_same_syllable_in_both_ears_is_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["dichotic"]["pairs"][0] = {"left": "ba", "right": "ba"}
    with pytest.raises(ConfigError, match="dikotik sunum farklı hece"):
        _load(write_config, data)


def test_a_response_without_a_key_is_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    """Inherited from ResponseUIConfig, but the error has to name *this*
    module's section or the operator is sent to the wrong block."""
    data = copy.deepcopy(config_dict)
    data["modules"]["dichotic"]["response_keys"] = ["1", "2", "3"]
    with pytest.raises(ConfigError, match="modules.dichotic.response_keys"):
        _load(write_config, data)


def test_a_free_text_option_without_its_prompt_is_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    data = copy.deepcopy(config_dict)
    del data["modules"]["dichotic"]["prompts"]["other"]
    with pytest.raises(ConfigError, match="prompts.other"):
        _load(write_config, data)


def test_the_configured_pairs_drive_the_design(
    write_config: Any, config_dict: dict[str, Any], manifest_factory: Any
) -> None:
    """steps.md §C Adım 4's criterion, applied here: changing the config changes
    the trial list, with no code edit."""
    data = copy.deepcopy(config_dict)
    data["modules"]["dichotic"]["pairs"] = [
        {"left": "ba", "right": "ga"},
        {"left": "ga", "right": "ba"},
    ]
    data["modules"]["dichotic"]["reps"] = 3
    config = _load(write_config, data)
    planned = plan_trials(
        config, manifest_factory(config), seed=SEED, stimuli_root=STIMULI
    )
    assert len(planned) == 6 == config.trial_counts()["dichotic"]
    assert {item.trial.condition_label for item in planned} == {
        "Left-ba/Right-ga",
        "Left-ga/Right-ba",
    }
