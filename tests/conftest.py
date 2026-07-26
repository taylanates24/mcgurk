"""Shared pytest fixtures.

The project root is put on ``sys.path`` so ``src`` and ``mcgurk`` imports
resolve the same way they do when running ``python main.py`` from the
repository root.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Modules that import PsychoPy at module level.  Each carries
# ``pytestmark = pytest.mark.psychopy`` so they can be deselected; here they
# are dropped from collection entirely when PsychoPy is not installed, which
# is the case on CI.  Marker deselection happens after import and would still
# hit the ImportError.
_NEEDS_PSYCHOPY = [
    "test_abort.py",
    "test_audio_backend.py",
    "test_engine_helpers.py",
    "test_participant_code.py",
    "test_silent_video.py",
]
collect_ignore = (
    [] if importlib.util.find_spec("psychopy") is not None else list(_NEEDS_PSYCHOPY)
)

from src.utils.assets import Speaker  # noqa: E402  (needs sys.path above)

SYLLABLES = ["ba", "da", "ga"]


@pytest.fixture
def stimulus_tree(tmp_path: Path) -> Path:
    """Build a fake assets/ tree.

    Only filenames matter for trial generation — the discovery code never
    opens the files — so empty placeholders are enough and the tests stay
    free of binary fixtures.
    """
    assets = tmp_path / "assets"
    speaker_dir = assets / "female_speaker_1"
    speaker_dir.mkdir(parents=True)
    for visual in SYLLABLES:
        for audio in SYLLABLES:
            (speaker_dir / f"Vis-{visual}_Aud-{audio}.mp4").touch()

    # Dichotic stimuli are stereo WAVs — these trials carry no video.
    dichotic_dir = assets / "dichotic" / "female_speaker_1"
    dichotic_dir.mkdir(parents=True)
    for left in SYLLABLES:
        for right in SYLLABLES:
            if left != right:
                (dichotic_dir / f"Left-{left}_Right-{right}.wav").touch()

    noise_dir = assets / "noise"
    noise_dir.mkdir(parents=True)
    (noise_dir / "white_noise.mp3").touch()
    (noise_dir / "cocktail_noise.mp3").touch()

    return assets


@pytest.fixture
def speaker(stimulus_tree: Path) -> Speaker:
    return Speaker(
        folder_name="female_speaker_1",
        gender="female",
        number=1,
        path=stimulus_tree / "female_speaker_1",
    )


@pytest.fixture
def config(stimulus_tree: Path) -> dict:
    return {
        "syllables": list(SYLLABLES),
        "trial_repetitions": 1,
        "noise": {"type": "white", "snr_db": 5},
        # get_assets_dir() resolves relative to the project root, so hand it
        # an absolute path to the temporary tree instead.
        "assets_dir": str(stimulus_tree),
    }
