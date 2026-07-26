"""Trial list generation: reproducibility and per-repetition independence."""

from pathlib import Path

from src.experiment.sections import build_trial_list
from src.utils.assets import Speaker


def _order(trials) -> list[tuple]:
    """Return a comparable fingerprint of a trial list's order."""
    return [
        (t.section_type, t.visual_syllable, t.audio_syllable, t.noise_condition)
        for t in trials
    ]


def test_same_seed_gives_same_order(speaker: Speaker, config: dict):
    first = build_trial_list(speaker, ["mcgurk", "av_congruent"], config, seed=42)
    second = build_trial_list(speaker, ["mcgurk", "av_congruent"], config, seed=42)

    assert _order(first) == _order(second)


def test_different_seed_gives_different_order(speaker: Speaker, config: dict):
    sections = ["mcgurk", "av_congruent", "audio_only"]
    first = build_trial_list(speaker, sections, config, seed=1)
    second = build_trial_list(speaker, sections, config, seed=2)

    assert len(first) == len(second)
    assert _order(first) != _order(second)


def test_repetitions_produce_distinct_objects(speaker: Speaker, config: dict):
    """Regression: ``specs * repetitions`` aliased one object per trial.

    TrialSpec is mutable — the engine writes ear_side back into it — so
    aliased repetitions silently overwrote each other's data.
    """
    config["trial_repetitions"] = 3
    trials = build_trial_list(speaker, ["dichotic"], config, seed=7)

    assert len(trials) == 18  # 6 dichotic pairs x 3 repetitions
    assert len({id(t) for t in trials}) == len(trials)


def test_mutating_one_trial_does_not_affect_repetitions(speaker: Speaker, config: dict):
    """Writing ear_side into one trial must not leak into its repetitions."""
    config["trial_repetitions"] = 2
    trials = build_trial_list(speaker, ["dichotic"], config, seed=7)

    trials[0].ear_side = "left"

    assert [t.ear_side for t in trials[1:]] == ["both"] * (len(trials) - 1)


def test_repetitions_scale_trial_count(speaker: Speaker, config: dict):
    single = build_trial_list(speaker, ["mcgurk"], config, seed=3)

    config["trial_repetitions"] = 4
    quadruple = build_trial_list(speaker, ["mcgurk"], config, seed=3)

    assert len(quadruple) == 4 * len(single)


def test_noisy_sections_add_one_set_per_noise_type(speaker: Speaker, config: dict):
    """Two noise files exist in the fixture, so noisy runs double the set."""
    clean_only = build_trial_list(speaker, ["mcgurk"], config, seed=5)
    with_noise = build_trial_list(
        speaker, ["mcgurk"], config, seed=5, noisy_sections=["mcgurk"]
    )

    assert len(with_noise) == 3 * len(clean_only)  # clean + white + cocktail
    assert {t.noise_condition for t in with_noise} == {"clean", "white", "cocktail"}


def test_visual_only_is_never_noisy(speaker: Speaker, config: dict):
    """V-only carries no audio, so a noise condition there is meaningless."""
    trials = build_trial_list(
        speaker, ["visual_only"], config, seed=5, noisy_sections=["visual_only"]
    )

    assert {t.noise_condition for t in trials} == {"clean"}


def test_missing_speaker_videos_yield_no_trials(tmp_path: Path, config: dict):
    empty_dir = tmp_path / "assets" / "male_speaker_9"
    empty_dir.mkdir(parents=True)
    empty_speaker = Speaker(
        folder_name="male_speaker_9", gender="male", number=9, path=empty_dir
    )

    assert build_trial_list(empty_speaker, ["mcgurk"], config, seed=1) == []
