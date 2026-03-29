"""Data models for the McGurk experiment."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Participant:
    name: str
    age: int
    gender: str
    group: str  # "SSD-right", "SSD-left", "control"
    notes: str = ""
    participant_id: int | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Session:
    participant_id: int
    speaker: str
    sections_run: str  # comma-separated section names
    admin_notes: str = ""
    session_id: int | None = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None


@dataclass
class Trial:
    session_id: int
    participant_id: int
    section_type: str  # "mcgurk", "av_congruent", "audio_only", "visual_only", "dichotic"
    speaker: str
    visual_syllable: str
    audio_syllable: str
    noise_condition: str  # "clean" or noise type
    snr_db: float | None
    participant_response: str
    correct_answer: str  # always the audio syllable
    is_correct: bool
    rt_from_video_end_ms: float
    rt_from_options_shown_ms: float
    trial_order: int
    ear_side: str | None = None  # "left" or "right" for dichotic
    trial_id: int | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
