"""Data models for the McGurk experiment."""

from dataclasses import dataclass, field
from datetime import datetime


# Session lifecycle states.  A session is 'running' from the moment it is
# created until it either finishes normally ('completed') or is interrupted
# ('aborted').  Analysis must be able to tell these apart — see progress.md.
SESSION_RUNNING = "running"
SESSION_COMPLETED = "completed"
SESSION_ABORTED = "aborted"


@dataclass
class Participant:
    """A participant, identified by an anonymous code.

    No name, surname or date of birth is ever collected or stored (KVKK).
    ``participant_code`` is the only identifier and is supplied by the
    operator from the separately-kept code↔identity mapping.
    """

    participant_code: str
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
    seed: int  # RNG seed — makes the trial order reproducible
    admin_notes: str = ""
    status: str = SESSION_RUNNING
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
    correct_answer: str  # audio syllable; meaningless for incongruent trials
    is_correct: bool | None  # None when the trial has no correct answer
    rt_from_video_end_ms: float
    rt_from_options_shown_ms: float
    trial_order: int
    ear_side: str | None = None  # "left" or "right" for dichotic
    trial_id: int | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
