"""Audio backend guard.

The study depends on scheduling audio against the flip clock, which only the
Psychtoolbox backend supports.  These tests pin the guard to the API PsychoPy
actually exposes — an earlier version checked ``sound.audioLib``, an attribute
removed in PsychoPy 2026.1, so the guard raised on every run.
"""

from collections.abc import Iterator

import pytest
from psychopy import sound

from src.experiment.stimuli import require_ptb_backend

pytestmark = pytest.mark.psychopy


@pytest.fixture(autouse=True)
def restore_backend() -> Iterator[None]:
    original = sound.Sound.backend
    yield
    sound.Sound.backend = original


def test_ptb_backend_passes():
    sound.Sound.backend = "ptb"

    require_ptb_backend()  # must not raise


def test_ptb_backend_is_the_default():
    """A fresh install must already be on ptb, not fall back to something else."""
    assert sound.Sound.backend == "ptb"


@pytest.mark.parametrize("backend", ["pygame", "pysound"])
def test_other_backends_are_rejected(backend: str):
    sound.Sound.backend = backend

    with pytest.raises(RuntimeError, match="ptb"):
        require_ptb_backend()


def test_ptb_backend_module_is_importable():
    """The name being right is not enough — psychtoolbox must actually load."""
    backend_module = sound.Sound.getBackends()["ptb"].load()

    assert hasattr(backend_module, "SoundPTB")


def test_scheduled_playback_is_supported():
    """play(when=...) is the mechanism the whole A/V sync strategy rests on."""
    import inspect

    backend_module = sound.Sound.getBackends()["ptb"].load()
    parameters = inspect.signature(backend_module.SoundPTB.play).parameters

    assert "when" in parameters
