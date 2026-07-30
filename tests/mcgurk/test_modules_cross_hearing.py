"""Cross-hearing check design and outcome logic (Adım 8b-ii).

The presentation needs a sound card, but the design — which trials carry the
tone, on which ear, in what balance — and the hit/false-alarm classification are
pure and tested here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from mcgurk.config import load_config
from mcgurk.modules import cross_hearing
from mcgurk.modules.base import ModuleError


def _config_and_manifest(manifest_factory, config_dict=None, write_config=None):
    if config_dict is None:
        config = load_config(check_filesystem=False)
    else:
        config = load_config(write_config(config_dict), check_filesystem=False)
    return config, manifest_factory(config)


def _plan(config: Any, manifest: Any, *, ear: str = "right", seed: int = 5):
    return cross_hearing.plan_trials(
        config, manifest, seed=seed, stimuli_root=Path("stimuli"), deaf_ear=ear
    )


def test_plan_count_matches_config(manifest_factory) -> None:
    config, manifest = _config_and_manifest(manifest_factory)
    planned = _plan(config, manifest)
    assert len(planned) == config.trial_counts()["cross_hearing"]
    assert len(planned) == config.cross_hearing_check.n_trials


def test_signal_and_catch_balance(manifest_factory) -> None:
    config, manifest = _config_and_manifest(manifest_factory)
    planned = _plan(config, manifest)
    n_signal = sum(1 for t in planned if t.signal_present)
    n_catch = len(planned) - n_signal
    # 20 trials at catch_ratio 0.5 -> 10 / 10.
    assert n_signal == 10
    assert n_catch == 10
    # Signal trials carry the tone; catch trials carry nothing.
    assert all(t.tone_path is not None for t in planned if t.signal_present)
    assert all(t.tone_path is None for t in planned if not t.signal_present)


def test_every_trial_is_on_the_deaf_ear(manifest_factory) -> None:
    config, manifest = _config_and_manifest(manifest_factory)
    for ear in ("left", "right"):
        planned = _plan(config, manifest, ear=ear)
        assert all(t.ear == ear for t in planned)
        assert all(t.trial.ear == ear for t in planned)
        # signal_present travels in design_extra for the QC report.
        assert all(
            t.trial.design_extra["signal_present"] == t.signal_present for t in planned
        )


def test_same_seed_same_sequence(manifest_factory) -> None:
    config, manifest = _config_and_manifest(manifest_factory)
    a = [t.signal_present for t in _plan(config, manifest, seed=11)]
    b = [t.signal_present for t in _plan(config, manifest, seed=11)]
    c = [t.signal_present for t in _plan(config, manifest, seed=12)]
    assert a == b
    assert a != c  # a different seed shuffles differently (overwhelmingly likely)


def test_catch_ratio_is_clamped_to_keep_both_kinds(
    manifest_factory, write_config, config_dict
) -> None:
    # A tiny ratio would round to zero catch trials; the design guarantees at
    # least one of each so both a hit rate and a false-alarm rate exist.
    config_dict["cross_hearing_check"]["catch_ratio"] = 0.02
    config, manifest = _config_and_manifest(manifest_factory, config_dict, write_config)
    planned = _plan(config, manifest)
    n_catch = sum(1 for t in planned if not t.signal_present)
    assert n_catch == 1


def test_bad_ear_is_rejected(manifest_factory) -> None:
    config, manifest = _config_and_manifest(manifest_factory)
    with pytest.raises(ModuleError):
        _plan(config, manifest, ear="both")


def test_disabled_module_refuses_to_plan(
    manifest_factory, write_config, config_dict
) -> None:
    config_dict["cross_hearing_check"]["enabled"] = False
    config, manifest = _config_and_manifest(manifest_factory, config_dict, write_config)
    with pytest.raises(ModuleError):
        _plan(config, manifest)


def test_tone_is_added_to_required_tones() -> None:
    # The prepared set has to include the detection tone, so it is derived into
    # required_tones() (Adım 8b-ii) rather than listed a second time.
    config = load_config(check_filesystem=False)
    assert config.cross_hearing_check.tone_hz in config.required_tones()


def test_classify() -> None:
    assert cross_hearing.classify(True, True) == cross_hearing.HIT
    assert cross_hearing.classify(True, False) == cross_hearing.MISS
    assert cross_hearing.classify(False, True) == cross_hearing.FALSE_ALARM
    assert cross_hearing.classify(False, False) == cross_hearing.CORRECT_REJECTION


def test_tally_counts_outcomes() -> None:
    outcome = cross_hearing.CrossHearingOutcome(ear="right")
    cross_hearing._tally(outcome, signal_present=True, detected=True)
    cross_hearing._tally(outcome, signal_present=True, detected=False)
    cross_hearing._tally(outcome, signal_present=False, detected=True)
    cross_hearing._tally(outcome, signal_present=False, detected=False)
    assert (outcome.hits, outcome.misses) == (1, 1)
    assert (outcome.false_alarms, outcome.correct_rejections) == (1, 1)
    assert outcome.n_trials == 4
