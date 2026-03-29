"""Trial data model for experiment execution."""

from dataclasses import dataclass, field
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
    correct_answer: str  # always the audio syllable
    speaker_name: str
    ear_side: str | None = None  # for dichotic: "left" or "right" (which ear has correct answer)


@dataclass
class TrialResult:
    """Result of a completed trial."""

    spec: TrialSpec
    participant_response: str
    is_correct: bool
    rt_from_video_end_ms: float
    rt_from_options_shown_ms: float
    trial_order: int
