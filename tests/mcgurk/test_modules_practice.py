"""Practice warm-up design (Adım 8b-ii).

Congruent AV trials, reproducible from the seed, written to a ``practice`` block
and never scored.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcgurk.config import load_config
from mcgurk.modules import practice


def _plan(config: Any, manifest: Any, *, seed: int = 3, speaker_id: int | None = None):
    return practice.plan_trials(
        config,
        manifest,
        seed=seed,
        stimuli_root=Path("stimuli"),
        speaker_id=speaker_id,
    )


def test_count_matches_config(manifest_factory) -> None:
    config = load_config(check_filesystem=False)
    planned = _plan(config, manifest_factory(config))
    assert len(planned) == config.trial_counts()["practice"]
    assert len(planned) == config.session.practice_trials


def test_all_trials_are_congruent_practice(manifest_factory) -> None:
    config = load_config(check_filesystem=False)
    for item in _plan(config, manifest_factory(config)):
        assert item.trial.module == "practice"
        assert item.trial.visual_token == item.trial.audio_token
        assert item.trial.presentation_mode == "AV"
        assert item.trial.design_extra == {}  # practice fits the shared columns


def test_same_seed_same_order(manifest_factory) -> None:
    config = load_config(check_filesystem=False)
    manifest = manifest_factory(config)
    a = [t.trial.visual_token for t in _plan(config, manifest, seed=7)]
    b = [t.trial.visual_token for t in _plan(config, manifest, seed=7)]
    assert a == b


def test_zero_practice_trials_yields_nothing(
    manifest_factory, write_config, config_dict
) -> None:
    config_dict["session"]["practice_trials"] = 0
    config = load_config(write_config(config_dict), check_filesystem=False)
    assert _plan(config, manifest_factory(config)) == []
