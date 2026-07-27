"""Modül 2 — the design it generates, the scoring, and the derived measures.

The acceptance criteria of steps.md §C Adım 5 are all here: three presentation
modes from the existing syllable stimuli, an enabled word set failing loudly
when the prepared set has no answer for it, the visual benefit index and the
lipreading score, ``open_set`` refusing to run, and V-only staying out of the
noise × ear crossing.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from mcgurk.config.loader import ConfigError, load_config
from mcgurk.db.design import validate_design_extra
from mcgurk.modules.avsr import (
    AUDIO_ONLY,
    AUDIOVISUAL,
    VISUAL_ONLY,
    Accuracy,
    OpenSetNotImplemented,
    accuracy_by_condition,
    accuracy_by_mode,
    cell_counts,
    design_cells,
    lipreading_accuracy,
    plan_trials,
    score,
    score_for,
    summarise_measures,
    visual_benefit,
    visual_benefit_by_condition,
)
from mcgurk.modules.base import QUIET, ModuleError

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


# ---------------------------------------------------------------- the design


def test_the_generator_produces_exactly_what_the_config_estimated(
    config: Any, manifest: Any
) -> None:
    assert len(_plan(config, manifest)) == config.trial_counts()["avsr"]


def test_all_three_presentation_modes_run_from_the_syllable_stimuli(
    config: Any, manifest: Any
) -> None:
    planned = _plan(config, manifest)
    modes = {item.trial.presentation_mode for item in planned}
    assert modes == {AUDIO_ONLY, VISUAL_ONLY, AUDIOVISUAL}
    for item in planned:
        # The engine derives the mode from what it was handed, so the two
        # agreeing is what proves the A-only path has no video and the V-only
        # path no audio.
        assert item.spec.mode == item.trial.presentation_mode


def test_v_only_carries_a_video_and_no_audio(config: Any, manifest: Any) -> None:
    visual = [
        item for item in _plan(config, manifest)
        if item.trial.presentation_mode == VISUAL_ONLY
    ]
    assert visual
    for item in visual:
        assert item.spec.video_path is not None
        assert item.spec.audio_path is None
        assert item.trial.audio_token is None
        assert item.trial.visual_token is not None


def test_a_only_carries_audio_and_no_video(config: Any, manifest: Any) -> None:
    audio = [
        item for item in _plan(config, manifest)
        if item.trial.presentation_mode == AUDIO_ONLY
    ]
    assert audio
    for item in audio:
        assert item.spec.audio_path is not None
        assert item.spec.video_path is None
        assert item.trial.visual_token is None
        assert item.trial.audio_token is not None


def test_v_only_is_not_crossed_with_noise_and_ear(config: Any, manifest: Any) -> None:
    """steps.md §C Adım 5.  A silent video has no SNR and no side; crossing
    them would quadruple the cell and produce identical trials."""
    module = config.modules.avsr
    planned = _plan(config, manifest)
    visual = [
        item for item in planned if item.trial.presentation_mode == VISUAL_ONLY
    ]

    items_per_set = sum(
        len(s.items()) * s.reps for s in module.stimulus_sets if s.enabled
    )
    assert len(visual) == items_per_set

    for item in visual:
        # NULL, not "quiet"/"both": absent is a different statement from quiet.
        assert item.trial.ear is None
        assert item.trial.snr_db is None
        assert item.trial.noise_condition is None
        assert item.trial.design_extra["noise_instance"] is None


def test_audio_modes_are_crossed_with_noise_and_ear(
    config: Any, manifest: Any
) -> None:
    module = config.modules.avsr
    planned = _plan(config, manifest)
    for mode in (AUDIO_ONLY, AUDIOVISUAL):
        cells = {
            (item.trial.design_extra["item"], item.trial.snr_db, item.trial.ear)
            for item in planned
            if item.trial.presentation_mode == mode
        }
        expected = (
            len(module.stimulus_sets[0].items())
            * len(module.noise_conditions)
            * len(module.ears)
        )
        assert len(cells) == expected


def test_reps_are_per_item_per_cell(config: Any, manifest: Any) -> None:
    planned = _plan(config, manifest)
    cell = [
        item
        for item in planned
        if item.trial.presentation_mode == AUDIOVISUAL
        and item.trial.design_extra["item"] == "ba"
        and item.trial.ear == "left"
        and item.trial.snr_db is None
    ]
    assert len(cell) == config.modules.avsr.stimulus_sets[0].reps


def test_changing_the_presentation_modes_changes_the_trial_list(
    write_config: Any, config_dict: dict[str, Any], manifest_factory: Any
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["avsr"]["presentation_modes"] = ["V"]
    data["modules"]["avsr"]["mode_questions"] = {"V": "Ne söyledi?"}
    trimmed = load_config(write_config(data), check_filesystem=False)
    planned = _plan(trimmed, manifest_factory(trimmed))
    assert {item.trial.presentation_mode for item in planned} == {VISUAL_ONLY}
    assert len(planned) == trimmed.trial_counts()["avsr"]


def test_a_question_for_a_mode_that_is_not_presented_is_refused(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    """Text nobody will ever read is a mistake, not a spare part."""
    data = copy.deepcopy(config_dict)
    data["modules"]["avsr"]["presentation_modes"] = ["A", "AV"]
    with pytest.raises(ConfigError, match="mode_questions"):
        load_config(write_config(data), check_filesystem=False)


def test_the_question_falls_back_to_the_shared_prompt(config: Any) -> None:
    module = config.modules.avsr
    assert module.question_for("V") == "Ne söyledi?"
    assert module.question_for("A") == module.prompts.question
    assert module.question_for("AV") == module.prompts.question


def test_the_same_seed_gives_the_same_order(config: Any, manifest: Any) -> None:
    first = [item.spec.label for item in _plan(config, manifest, seed=7)]
    second = [item.spec.label for item in _plan(config, manifest, seed=7)]
    other = [item.spec.label for item in _plan(config, manifest, seed=8)]
    assert first == second
    assert first != other


def test_the_module_has_its_own_rng_stream(config: Any, manifest: Any) -> None:
    """A shared stream would make AVSR's order depend on McGurk's position in
    ``session.module_order`` (Adım 4 decision)."""
    from mcgurk.modules.mcgurk import plan_trials as mcgurk_plan

    avsr_labels = [item.spec.label for item in _plan(config, manifest, seed=7)]
    mcgurk_first = [
        item.trial.condition_label
        for item in mcgurk_plan(config, manifest, seed=7, stimuli_root=STIMULI)
    ]
    # Nothing about McGurk's design touches AVSR's order.
    assert avsr_labels == [item.spec.label for item in _plan(config, manifest, seed=7)]
    assert mcgurk_first  # the other module still produced its own list


def test_noise_instances_are_balanced_within_a_cell(
    config: Any, manifest: Any
) -> None:
    from collections import Counter

    planned = _plan(config, manifest)
    used: Counter[int] = Counter()
    for item in planned:
        trial = item.trial
        if (
            trial.presentation_mode == AUDIOVISUAL
            and trial.design_extra["item"] == "ba"
            and trial.ear == "left"
            and trial.snr_db == 5.0
        ):
            used[trial.design_extra["noise_instance"]] += 1
    assert sum(used.values()) == config.modules.avsr.stimulus_sets[0].reps
    # Five repetitions over three waveforms: 2/2/1 in some order, never 5/0/0.
    assert max(used.values()) - min(used.values()) <= 1


def test_the_noise_condition_names_what_was_mixed_in(
    config: Any, manifest: Any
) -> None:
    planned = _plan(config, manifest)
    quiet = {
        item.trial.noise_condition
        for item in planned
        if item.trial.presentation_mode != VISUAL_ONLY and item.trial.snr_db is None
    }
    noisy = {
        item.trial.noise_condition
        for item in planned
        if item.trial.snr_db is not None
    }
    assert quiet == {QUIET}
    assert noisy == {config.stimulus_prep.noise.type}


def test_paths_and_bursts_come_from_the_manifest(config: Any, manifest: Any) -> None:
    speaker = config.modules.avsr.speaker_id
    for item in _plan(config, manifest):
        stimulus = item.trial.design_extra["item"]
        if item.spec.video_path is not None:
            video = manifest.video(speaker, stimulus)
            assert item.spec.video_path == video.file.resolve(STIMULI)
            assert item.spec.video_burst_s == video.burst_time_s
        if item.spec.audio_path is not None:
            # The noisy derivative keeps the clean token's burst (Adım 2).
            token = manifest.token(speaker, stimulus, stimulus)
            assert item.spec.audio_burst_s == token.burst_time_s


def test_the_stimuli_are_the_congruent_takes(config: Any, manifest: Any) -> None:
    """AVSR measures recognition, not integration conflict: the visual and the
    acoustic token are always the same item."""
    for item in _plan(config, manifest):
        trial = item.trial
        for token in (trial.visual_token, trial.audio_token):
            if token is not None:
                assert token == trial.design_extra["item"]


def test_the_design_extra_is_accepted_by_the_database_layer(
    config: Any, manifest: Any
) -> None:
    for item in _plan(config, manifest):
        validate_design_extra("avsr", item.trial.design_extra)


def test_the_speaker_can_be_overridden_per_participant(
    config: Any, manifest: Any
) -> None:
    planned = plan_trials(
        config, manifest, seed=SEED, stimuli_root=STIMULI, speaker_id=2
    )
    assert {item.trial.design_extra["speaker_id"] for item in planned} == {2}


def test_a_disabled_module_refuses_to_plan(
    write_config: Any, config_dict: dict[str, Any], manifest_factory: Any
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["avsr"]["enabled"] = False
    data["session"]["module_order"].remove("avsr")
    disabled = load_config(write_config(data), check_filesystem=False)
    with pytest.raises(ModuleError, match="enabled false"):
        _plan(disabled, manifest_factory(disabled))


def test_cell_counts_cover_every_cell(config: Any, manifest: Any) -> None:
    planned = _plan(config, manifest)
    counts = cell_counts(planned)
    assert len(counts) == len(design_cells(config.modules.avsr)[0])
    assert sum(counts.values()) == len(planned)


# ------------------------------------------------------------------ open set


def test_open_set_is_refused_before_anything_is_presented(
    write_config: Any, config_dict: dict[str, Any], manifest_factory: Any
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["avsr"]["response_mode"] = "open_set"
    open_set = load_config(write_config(data), check_filesystem=False)
    with pytest.raises(NotImplementedError) as exc:
        _plan(open_set, manifest_factory(open_set))
    assert isinstance(exc.value, OpenSetNotImplemented)
    assert "closed_set" in str(exc.value)


# ------------------------------------------------------------------ the words


def _word_config(
    write_config: Any,
    config_dict: dict[str, Any],
    tmp_path: Path,
    items: list[str],
    *,
    tokens: list[str] | None = None,
) -> Any:
    """A config whose AVSR word set is enabled and points at *items*."""
    data = copy.deepcopy(config_dict)
    word_list = tmp_path / "words.yaml"
    word_list.write_text(
        yaml.safe_dump(
            {"name": "test", "language": "tr", "items": items}, allow_unicode=True
        ),
        encoding="utf-8",
    )
    sets = data["modules"]["avsr"]["stimulus_sets"]
    sets[1]["enabled"] = True
    sets[1]["list"] = str(word_list)
    if tokens is not None:
        data["stimulus_prep"]["tokens"] = tokens
    return load_config(write_config(data), check_filesystem=False)


def test_an_enabled_word_set_joins_the_trial_count(
    write_config: Any, config_dict: dict[str, Any], tmp_path: Path
) -> None:
    tokens = list(config_dict["stimulus_prep"]["tokens"]) + ["kitap"]
    config = _word_config(
        write_config, config_dict, tmp_path, ["kitap"], tokens=tokens
    )
    syllables, words = config.modules.avsr.stimulus_sets
    assert words.n_items() == 1
    # One word, reps 1, over the same modes: 1 + 4 + 4 = 9 more trials.
    per_item = 1 + 2 * len(config.modules.avsr.noise_conditions) * len(
        config.modules.avsr.ears
    )
    assert config.trial_counts()["avsr"] == per_item * (
        syllables.n_items() * syllables.reps + words.n_items() * words.reps
    )


def test_a_word_the_stimulus_set_cannot_hold_is_refused_at_load(
    write_config: Any, config_dict: dict[str, Any], tmp_path: Path
) -> None:
    """The word has to be preparable before it can be presented; catching it
    here means catching it before the participant sits down."""
    with pytest.raises(ConfigError) as exc:
        _word_config(write_config, config_dict, tmp_path, ["kitap"])
    assert "stimulus_prep.tokens" in str(exc.value)


def test_a_word_missing_from_the_manifest_is_refused_before_the_session(
    write_config: Any, config_dict: dict[str, Any], tmp_path: Path, manifest_factory: Any
) -> None:
    """steps.md §C Adım 5 acceptance criterion: ``enabled: true`` with no
    manifest entry is an explicit error."""
    tokens = list(config_dict["stimulus_prep"]["tokens"]) + ["kitap"]
    config = _word_config(
        write_config, config_dict, tmp_path, ["kitap"], tokens=tokens
    )
    # A manifest built for the *syllables only* — the state the prepared set is
    # actually in today, since no words have been recorded (§F.2).
    unprepared = copy.deepcopy(config_dict)
    stripped = load_config(write_config(unprepared, "syllables.yaml"), check_filesystem=False)
    with pytest.raises(ModuleError) as exc:
        _plan(config, manifest_factory(stripped))
    assert "kitap" in str(exc.value)
    assert "prepare_stimuli" in str(exc.value)


def test_the_shipped_template_is_readable_and_empty() -> None:
    """The file the config points at has to parse — it is the shape the
    recording session will fill in (§F.2)."""
    from mcgurk.config.word_lists import WordListError, load_word_list

    path = PROJECT_ROOT / "config" / "word_lists" / "tr_pb_50.yaml"
    assert path.is_file()
    with pytest.raises(WordListError, match="items boş"):
        load_word_list(path)


def test_a_word_list_refuses_duplicates(tmp_path: Path) -> None:
    from mcgurk.config.word_lists import WordListError, load_word_list

    path = tmp_path / "words.yaml"
    path.write_text(
        yaml.safe_dump({"name": "t", "items": ["kitap", "Kitap"]}, allow_unicode=True),
        encoding="utf-8",
    )
    with pytest.raises(WordListError, match="tekrarlı"):
        load_word_list(path)


def test_a_word_list_refuses_unknown_fields(tmp_path: Path) -> None:
    from mcgurk.config.word_lists import WordListError, load_word_list

    path = tmp_path / "words.yaml"
    path.write_text(
        yaml.safe_dump({"name": "t", "items": ["kitap"], "reps": 3}),
        encoding="utf-8",
    )
    with pytest.raises(WordListError):
        load_word_list(path)


def test_a_missing_word_list_names_the_file(
    write_config: Any, config_dict: dict[str, Any], tmp_path: Path
) -> None:
    data = copy.deepcopy(config_dict)
    data["modules"]["avsr"]["stimulus_sets"][1]["enabled"] = True
    data["modules"]["avsr"]["stimulus_sets"][1]["list"] = str(tmp_path / "yok.yaml")
    with pytest.raises(ConfigError) as exc:
        load_config(write_config(data), check_filesystem=False)
    assert "yok.yaml" in str(exc.value)


# -------------------------------------------------------------------- scoring


def test_a_response_is_scored_against_the_item_presented() -> None:
    assert score("BA", "ba") is True
    assert score("ba", "BA") is True
    assert score(" da ", "ba") is False
    # No response is not a wrong response — how a timeout enters the accuracy
    # is decided in the measures, not here.
    assert score(None, "ba") is None
    assert score("   ", "ba") is None


def test_scoring_reads_the_item_off_the_trial(config: Any, manifest: Any) -> None:
    item = _plan(config, manifest)[0]
    presented = item.trial.design_extra["item"]
    assert score_for(presented.upper(), item.trial) is True
    wrong = next(t for t in ("ba", "da", "ga") if t != presented)
    assert score_for(wrong, item.trial) is False


def test_an_empty_response_label_is_refused_at_load(
    write_config: Any, config_dict: dict[str, Any]
) -> None:
    """An unreadable option would be scored with a NULL ``is_correct``, and
    NULL is reserved for the modules that have no correct answer at all."""
    data = copy.deepcopy(config_dict)
    data["modules"]["avsr"]["response_set"] = ["BA", " "]
    data["modules"]["avsr"]["response_keys"] = ["1", "2"]
    with pytest.raises(ConfigError, match="boş bir yanıt"):
        load_config(write_config(data), check_filesystem=False)


def test_scoring_a_trial_with_no_item_is_an_error(config: Any, manifest: Any) -> None:
    from dataclasses import replace

    item = _plan(config, manifest)[0]
    broken = replace(item.trial, design_extra={"speaker_id": 1})
    with pytest.raises(ModuleError, match="item"):
        score_for("BA", broken)


# ------------------------------------------------------------------- measures


def _row(mode: str, correct: bool | None, snr: float | None = None, ear: str | None = None):
    return {
        "module": "avsr",
        "presentation_mode": mode,
        "is_correct": correct,
        "snr_db": snr,
        "ear": ear,
    }


def test_accuracy_counts_a_timeout_as_incorrect() -> None:
    """Excluding no-responses would raise the accuracy of exactly the
    participants who could not answer in time."""
    stats = accuracy_by_mode([_row("A", True), _row("A", False), _row("A", None)])["A"]
    assert stats == Accuracy(n_trials=3, n_correct=1, n_missing=1)
    assert stats.accuracy == pytest.approx(1 / 3)


def test_an_empty_condition_has_no_accuracy() -> None:
    assert Accuracy().accuracy is None
    assert lipreading_accuracy([]) is None
    assert visual_benefit([]) is None


def test_visual_benefit_is_av_minus_a() -> None:
    rows = [
        _row("AV", True), _row("AV", True), _row("AV", True), _row("AV", False),
        _row("A", True), _row("A", False), _row("A", False), _row("A", False),
    ]
    assert visual_benefit(rows) == pytest.approx(0.75 - 0.25)


def test_visual_benefit_needs_both_modes() -> None:
    assert visual_benefit([_row("AV", True), _row("AV", False)]) is None


def test_lipreading_is_the_v_only_accuracy() -> None:
    rows = [_row("V", True), _row("V", False), _row("A", True)]
    assert lipreading_accuracy(rows) == pytest.approx(0.5)


def test_visual_benefit_is_computed_within_a_condition() -> None:
    """The SSD hypothesis is about how the benefit depends on noise and ear, so
    the index has to exist per cell and not only pooled."""
    rows = [
        _row("AV", True, 5.0, "left"), _row("AV", True, 5.0, "left"),
        _row("A", True, 5.0, "left"), _row("A", False, 5.0, "left"),
        _row("AV", True, None, "right"), _row("AV", False, None, "right"),
        _row("A", True, None, "right"), _row("A", True, None, "right"),
    ]
    benefits = visual_benefit_by_condition(rows)
    assert benefits[(5.0, "left")] == pytest.approx(0.5)
    assert benefits[(None, "right")] == pytest.approx(-0.5)


def test_a_condition_with_no_baseline_yields_no_index() -> None:
    assert visual_benefit_by_condition([_row("AV", True, 5.0, "left")]) == {}


def test_v_only_lands_in_its_own_condition() -> None:
    by_condition = accuracy_by_condition([_row("V", True)])
    assert list(by_condition) == [("V", None, None)]


def test_other_modules_rows_are_ignored() -> None:
    rows = [_row("A", True), {"module": "mcgurk", "presentation_mode": "AV",
                              "is_correct": None, "snr_db": None, "ear": "left"}]
    assert accuracy_by_mode(rows)["A"].n_trials == 1
    assert "AV" not in accuracy_by_mode(rows)


def test_the_summary_reports_both_measures() -> None:
    rows = [_row("AV", True), _row("A", False), _row("V", True), _row("V", None)]
    text = summarise_measures(rows)
    assert "Görsel fayda" in text
    assert "Lipreading" in text
    assert "yanıtsız" in text
