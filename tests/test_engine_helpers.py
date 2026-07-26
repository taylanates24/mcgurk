"""Engine helpers that need no window: seed resolution and noise lookup."""

from pathlib import Path

import pytest

from src.experiment.engine import _find_noise_file, resolve_seed

pytestmark = pytest.mark.psychopy


def test_configured_seed_is_used_verbatim():
    assert resolve_seed({"seed": 20260726}) == 20260726


def test_missing_seed_is_drawn_and_in_range():
    seed = resolve_seed({"seed": None})

    assert isinstance(seed, int)
    assert 0 <= seed < 2**31


def test_absent_seed_key_behaves_like_null():
    assert isinstance(resolve_seed({}), int)


def test_clean_condition_needs_no_noise_file(config: dict):
    assert _find_noise_file("clean", config) is None


def test_existing_noise_file_is_found(config: dict, stimulus_tree: Path):
    found = _find_noise_file("white", config)

    assert found == stimulus_tree / "noise" / "white_noise.mp3"


def test_missing_noise_file_raises(config: dict):
    """A missing noise file must not silently downgrade to the clean condition."""
    with pytest.raises(FileNotFoundError, match="speech_shaped"):
        _find_noise_file("speech_shaped", config)
