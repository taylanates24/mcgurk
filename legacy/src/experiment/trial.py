"""Trial data model for experiment execution."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class TrialSpec:
    """Specification for a single trial to be presented."""

    section_type: str  # "mcgurk", "av_congruent", "audio_only", "visual_only", "dichotic"
    video_path: Path | None  # None for audio_only / dichotic
    audio_path: Path | None  # None for visual_only, separate audio for dichotic
    visual_syllable: str
    audio_syllable: str
    noise_condition: str  # "clean", "white", "speech_shaped", "cocktail"
    snr_db: float | None
    # The audio syllable.  Only meaningful for congruent sections; for McGurk
    # trials the stimulus is incongruent by design and there is no correct
    # answer.  For dichotic trials this holds "<left>|<right>".
    correct_answer: str
    speaker_name: str
    ear_side: str | None = None  # for dichotic: which ear the response matched


@dataclass
class TrialResult:
    """Result of a completed trial."""

    spec: TrialSpec
    participant_response: str
    is_correct: bool | None  # None when the section has no correct answer
    rt_from_video_end_ms: float
    rt_from_options_shown_ms: float
    trial_order: int
