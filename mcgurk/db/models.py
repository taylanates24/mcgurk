"""Row models for the experiment database.

Plain dataclasses rather than pydantic: these are the shape of a row on its way
to SQLite, and the value constraints already live in the schema (CHECK) and in
the config layer.  Duplicating them here would give two places to keep in sync.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

SESSION_RUNNING = "running"
SESSION_COMPLETED = "completed"
SESSION_ABORTED = "aborted"

GROUP_SSD_RIGHT = "SSD_R"
GROUP_SSD_LEFT = "SSD_L"
GROUP_CONTROL = "CTRL"


def _now() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


@dataclass
class Participant:
    """A participant, identified by an anonymous code only (§A.6, KVKK)."""

    participant_code: str
    group_code: str
    age: int
    sex: str
    deprivation_months: int | None = None
    pta_right_db: float | None = None
    pta_left_db: float | None = None
    postlingual: bool | None = None
    notes: str = ""
    participant_id: int | None = None
    created_at: str = field(default_factory=_now)


@dataclass
class CalibrationRecord:
    measured_on: str
    source_file: str
    k_left_db: float
    k_right_db: float
    k_mean_db: float
    channel_difference_db: float
    target_spl_db: float
    required_dbfs: float
    trim_left_db: float
    trim_right_db: float
    raw_json: str
    calibration_id: int | None = None
    imported_at: str = field(default_factory=_now)


@dataclass
class SessionRecord:
    participant_id: int
    seed: int
    config_snapshot: str
    config_mode: str
    python_version: str
    os_name: str
    calibration_id: int | None = None
    app_version: str | None = None
    git_commit: str | None = None
    psychopy_version: str | None = None
    audio_backend: str | None = None
    audio_device: str | None = None
    measured_refresh_hz: float | None = None
    system_av_offset_ms: float | None = None
    status: str = SESSION_RUNNING
    operator_notes: str = ""
    session_id: int | None = None
    started_at: str = field(default_factory=_now)
    completed_at: str | None = None


@dataclass
class Block:
    session_id: int
    module: str
    block_index: int
    n_trials_planned: int
    label: str = ""
    status: str = SESSION_RUNNING
    block_id: int | None = None
    started_at: str = field(default_factory=_now)
    completed_at: str | None = None


@dataclass
class Trial:
    """The design of one trial.  Timing is written afterwards (§A.4)."""

    block_id: int
    trial_index: int
    module: str
    condition_label: str = ""
    visual_token: str | None = None
    audio_token: str | None = None
    ear: str | None = None
    snr_db: float | None = None
    noise_condition: str | None = None
    nominal_soa_ms: float | None = None
    presentation_mode: str | None = None
    design_extra: dict[str, Any] = field(default_factory=dict)
    trial_id: int | None = None


@dataclass
class TrialTiming:
    """What actually happened during presentation (§A.4)."""

    video_onset_s: float | None = None
    audio_onset_s: float | None = None
    actual_soa_ms: float | None = None
    dropped_frames: int | None = None
    max_frame_interval_ms: float | None = None
    presented_at: str = field(default_factory=_now)


@dataclass
class Response:
    trial_id: int
    response_index: int = 0
    #: Which event inside the trial this answers (GIN: the gap's index in
    #: ``design_extra.gap_onsets_s``).  None wherever the trial is the event.
    event_index: int | None = None
    raw_response: str | None = None
    free_text: str | None = None
    category: str | None = None
    #: Must stay None for modules without a correct answer (§A.10) — the
    #: database rejects anything else.
    is_correct: bool | None = None
    rt_from_burst_ms: float | None = None
    rt_from_prompt_ms: float | None = None
    input_device: str = "keyboard"
    response_id: int | None = None
    recorded_at: str = field(default_factory=_now)
