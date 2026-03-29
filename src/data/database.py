"""SQLite database operations for the McGurk experiment."""

import sqlite3
from pathlib import Path
from typing import Any

from .models import Participant, Session, Trial


_SCHEMA = """
CREATE TABLE IF NOT EXISTS participants (
    participant_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    gender TEXT NOT NULL,
    "group" TEXT NOT NULL,
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id INTEGER NOT NULL,
    speaker TEXT NOT NULL,
    sections_run TEXT NOT NULL,
    admin_notes TEXT DEFAULT '',
    started_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (participant_id) REFERENCES participants(participant_id)
);

CREATE TABLE IF NOT EXISTS trials (
    trial_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    participant_id INTEGER NOT NULL,
    section_type TEXT NOT NULL,
    speaker TEXT NOT NULL,
    visual_syllable TEXT NOT NULL,
    audio_syllable TEXT NOT NULL,
    noise_condition TEXT NOT NULL,
    snr_db REAL,
    participant_response TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    is_correct INTEGER NOT NULL,
    rt_from_video_end_ms REAL NOT NULL,
    rt_from_options_shown_ms REAL NOT NULL,
    trial_order INTEGER NOT NULL,
    ear_side TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    FOREIGN KEY (participant_id) REFERENCES participants(participant_id)
);
"""


class Database:
    """SQLite database wrapper for experiment data."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    # -- Participants --

    def add_participant(self, p: Participant) -> int:
        cursor = self.conn.execute(
            'INSERT INTO participants (name, age, gender, "group", notes, created_at) '
            "VALUES (?, ?, ?, ?, ?, ?)",
            (p.name, p.age, p.gender, p.group, p.notes, p.created_at),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_participant(self, participant_id: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM participants WHERE participant_id = ?", (participant_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_all_participants(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM participants ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # -- Sessions --

    def add_session(self, s: Session) -> int:
        cursor = self.conn.execute(
            "INSERT INTO sessions (participant_id, speaker, sections_run, admin_notes, started_at, completed_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (s.participant_id, s.speaker, s.sections_run, s.admin_notes, s.started_at, s.completed_at),
        )
        self.conn.commit()
        return cursor.lastrowid

    def complete_session(self, session_id: int, completed_at: str):
        self.conn.execute(
            "UPDATE sessions SET completed_at = ? WHERE session_id = ?",
            (completed_at, session_id),
        )
        self.conn.commit()

    def get_sessions_for_participant(self, participant_id: int) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM sessions WHERE participant_id = ? ORDER BY started_at DESC",
            (participant_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # -- Trials --

    def add_trial(self, t: Trial) -> int:
        cursor = self.conn.execute(
            "INSERT INTO trials "
            "(session_id, participant_id, section_type, speaker, visual_syllable, "
            "audio_syllable, noise_condition, snr_db, participant_response, correct_answer, "
            "is_correct, rt_from_video_end_ms, rt_from_options_shown_ms, trial_order, "
            "ear_side, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                t.session_id, t.participant_id, t.section_type, t.speaker,
                t.visual_syllable, t.audio_syllable, t.noise_condition, t.snr_db,
                t.participant_response, t.correct_answer, int(t.is_correct),
                t.rt_from_video_end_ms, t.rt_from_options_shown_ms, t.trial_order,
                t.ear_side, t.timestamp,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_trials_for_session(self, session_id: int) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM trials WHERE session_id = ? ORDER BY trial_order",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_trials(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT t.*, p.name as participant_name, p.\"group\" as participant_group "
            "FROM trials t "
            "JOIN participants p ON t.participant_id = p.participant_id "
            "ORDER BY t.timestamp"
        ).fetchall()
        return [dict(r) for r in rows]
