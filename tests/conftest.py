"""Shared pytest fixtures.

The project root is put on ``sys.path`` so ``mcgurk`` imports resolve when
pytest runs from the repository root.  The Adım 0 ``src/`` tree is retired
(frozen under ``legacy/``), so nothing here touches it any more.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def hardware_speaker():
    """The one output device of a test session.

    Session-scoped because PsychPortAudio takes the device exclusively at
    latency class 3: two ``psychopy``-marked modules each opening their own
    would leave whichever ran second skipped, and which one that is depends on
    collection order.  PsychoPy is imported inside the body, so a CI run that
    never requests this fixture never touches it.

    ``MCGURK_TEST_AUDIO_DEVICE`` overrides ``audio.device`` for the test run
    only.  It exists because the configured device is a Bluetooth headset: with
    it switched off the whole hardware suite skips, and the alternative — a
    fixture that quietly picks some other device — would hide which one the
    tests ran on.
    """
    import os

    from mcgurk.config.loader import load_config
    from mcgurk.engine.audio import AudioError, open_speaker, require_ptb_backend
    from mcgurk.engine.psychopy_prefs import configure_psychopy

    config = load_config(project_root=PROJECT_ROOT)
    device = os.environ.get("MCGURK_TEST_AUDIO_DEVICE") or config.audio.device
    configure_psychopy(audio_device=device)
    require_ptb_backend()
    try:
        return open_speaker(
            device_name=device,
            latency_class=config.timing.audio_latency_mode,
            sample_rate=config.audio.sample_rate,
        )
    except AudioError as exc:
        pytest.skip(f"Ses aygıtı bu makinede uygun değil: {exc}")
