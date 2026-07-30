"""SQLite access layer.

Two rules shape this module:

* **§A.5 — no disk I/O inside a trial.**  ``add_trial``, ``set_trial_timing``
  and ``add_response`` do *not* commit; ``finish_block`` does.  Commits happen
  at block boundaries, which is where a pause is harmless.
* **Everything the analysis needs must be recoverable.**  The session row
  carries the seed, the verbatim config and the environment it ran in, so a
  data set can be interpreted years later without the working tree.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .backup import backup_database
from .design import validate_design_extra
from .models import (
    Block,
    CalibrationRecord,
    Participant,
    Response,
    SessionRecord,
    Trial,
    TrialTiming,
)

logger = logging.getLogger(__name__)

#: 1 -> 2: v_trials_flat exposes speaker_id and noise_instance (Adım 4).
#: 2 -> 3: the §A.10 trigger also refuses is_correct on ``tbw`` trials (Adım 6).
#: 3 -> 4: responses.event_index — which event inside a trial a response
#:         answers.  GIN's unit of analysis is the gap, not the segment (Adım 7c).
SCHEMA_VERSION = 4
_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class DatabaseError(RuntimeError):
    """Base class for database problems that the operator has to act on."""


class SchemaVersionError(DatabaseError):
    """The file exists but was written by an incompatible schema."""


def _last_row_id(cursor: sqlite3.Cursor) -> int:
    row_id = cursor.lastrowid
    if row_id is None:  # pragma: no cover - sqlite3 always sets it after INSERT
        raise DatabaseError("INSERT sonrası satır kimliği alınamadı.")
    return row_id


def calibration_record_from_file(path: Path | str) -> CalibrationRecord:
    """Read a calibration JSON file into a storable row.

    Imported lazily so that ``mcgurk.db`` does not drag the config layer into
    every import of the database.
    """
    from ..config.calibration import load_calibration

    calibration_path = Path(path)
    calibration = load_calibration(calibration_path)
    return CalibrationRecord(
        measured_on=calibration.measured_on.isoformat(timespec="seconds"),
        source_file=str(calibration_path),
        k_left_db=calibration.k_left_db,
        k_right_db=calibration.k_right_db,
        k_mean_db=calibration.k_mean_db,
        channel_difference_db=calibration.channel_difference_db,
        target_spl_db=calibration.target_spl_db,
        required_dbfs=calibration.required_dbfs,
        trim_left_db=calibration.trim_left_db,
        trim_right_db=calibration.trim_right_db,
        raw_json=calibration_path.read_text(encoding="utf-8"),
    )


class Database:
    """Connection wrapper owning the schema, the writes and the backups."""

    def __init__(self, path: Path | str, *, create: bool = True) -> None:
        self.path = Path(path)
        if not self.path.exists() and not create:
            raise DatabaseError(f"Veritabanı bulunamadı: {self.path}")
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        # WAL survives a crash mid-session far better than the rollback
        # journal, and it is what the VACUUM INTO backup expects.
        if str(self.path) != ":memory:":
            self.conn.execute("PRAGMA journal_mode = WAL").fetchone()
        self._init_schema()

    # -- lifecycle --------------------------------------------------------

    def _init_schema(self) -> None:
        self._reject_incompatible_schema()
        self.conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        self.conn.commit()

    def _reject_incompatible_schema(self) -> None:
        tables = {
            row["name"]
            for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        user_tables = {t for t in tables if not t.startswith("sqlite_")}
        if not user_tables:
            return

        if "participants" in user_tables:
            columns = {
                row["name"]
                for row in self.conn.execute("PRAGMA table_info(participants)")
            }
            if "group_code" not in columns:
                raise SchemaVersionError(
                    f"'{self.path}' bu paketin şemasını kullanmıyor "
                    f"(participants sütunları: {sorted(columns)}).\n"
                    "Adım 0'ın src/ veritabanını göstermiş olabilirsiniz; yeni "
                    "paket ayrı bir dosya kullanır (config: database.path)."
                )

        version = int(self.conn.execute("PRAGMA user_version").fetchone()[0])
        if version != SCHEMA_VERSION:
            raise SchemaVersionError(
                f"'{self.path}' şema sürümü {version}, beklenen {SCHEMA_VERSION}.\n"
                "Dosyayı backups/ altına alıp yeniden oluşturun."
            )

    def close(self) -> None:
        self.conn.close()

    def commit(self) -> None:
        self.conn.commit()

    def __enter__(self) -> Database:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- participants -----------------------------------------------------

    def add_participant(self, participant: Participant) -> int:
        cursor = self.conn.execute(
            "INSERT INTO participants (participant_code, group_code, age, sex, "
            "deprivation_months, pta_right_db, pta_left_db, postlingual, notes, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                participant.participant_code,
                participant.group_code,
                participant.age,
                participant.sex,
                participant.deprivation_months,
                participant.pta_right_db,
                participant.pta_left_db,
                None if participant.postlingual is None else int(participant.postlingual),
                participant.notes,
                participant.created_at,
            ),
        )
        self.conn.commit()
        return _last_row_id(cursor)

    def get_participant(self, participant_id: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM participants WHERE participant_id = ?", (participant_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_participant_by_code(self, code: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM participants WHERE participant_code = ?", (code,)
        ).fetchone()
        return dict(row) if row else None

    # -- calibrations -----------------------------------------------------

    def add_calibration(self, calibration: CalibrationRecord) -> int:
        cursor = self.conn.execute(
            "INSERT INTO calibrations (measured_on, source_file, k_left_db, "
            "k_right_db, k_mean_db, channel_difference_db, target_spl_db, "
            "required_dbfs, trim_left_db, trim_right_db, raw_json, imported_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                calibration.measured_on,
                calibration.source_file,
                calibration.k_left_db,
                calibration.k_right_db,
                calibration.k_mean_db,
                calibration.channel_difference_db,
                calibration.target_spl_db,
                calibration.required_dbfs,
                calibration.trim_left_db,
                calibration.trim_right_db,
                calibration.raw_json,
                calibration.imported_at,
            ),
        )
        self.conn.commit()
        return _last_row_id(cursor)

    def latest_calibration(self) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM calibrations ORDER BY measured_on DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    # -- sessions ---------------------------------------------------------

    def start_session(self, session: SessionRecord) -> int:
        cursor = self.conn.execute(
            "INSERT INTO sessions (participant_id, calibration_id, seed, "
            "config_snapshot, config_mode, app_version, git_commit, "
            "psychopy_version, python_version, os_name, audio_backend, "
            "audio_device, measured_refresh_hz, system_av_offset_ms, status, "
            "operator_notes, started_at, completed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session.participant_id,
                session.calibration_id,
                session.seed,
                session.config_snapshot,
                session.config_mode,
                session.app_version,
                session.git_commit,
                session.psychopy_version,
                session.python_version,
                session.os_name,
                session.audio_backend,
                session.audio_device,
                session.measured_refresh_hz,
                session.system_av_offset_ms,
                session.status,
                session.operator_notes,
                session.started_at,
                session.completed_at,
            ),
        )
        self.conn.commit()
        return _last_row_id(cursor)

    def finish_session(
        self, session_id: int, status: str, completed_at: str | None = None
    ) -> None:
        """Close a session. Called from a ``finally`` block on every exit path."""
        stamp = completed_at or datetime.now().isoformat(timespec="milliseconds")
        self.conn.execute(
            "UPDATE sessions SET status = ?, completed_at = ? WHERE session_id = ?",
            (status, stamp, session_id),
        )
        self.conn.commit()

    def get_session(self, session_id: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        return dict(row) if row else None

    # -- blocks -----------------------------------------------------------

    def add_block(self, block: Block) -> int:
        cursor = self.conn.execute(
            "INSERT INTO blocks (session_id, module, block_index, label, "
            "n_trials_planned, status, started_at, completed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                block.session_id,
                block.module,
                block.block_index,
                block.label,
                block.n_trials_planned,
                block.status,
                block.started_at,
                block.completed_at,
            ),
        )
        self.conn.commit()
        return _last_row_id(cursor)

    def next_block_index(self, session_id: int) -> int:
        """The index a new block of *session_id* should take.

        ``blocks`` is unique on ``(session_id, block_index)``, and a module can
        contribute several blocks (§A.5 puts the commit at the block boundary,
        so a long module is split).  Asking the database rather than counting in
        the caller keeps a resumed session from colliding with its own history.
        """
        row = self.conn.execute(
            "SELECT MAX(block_index) AS last FROM blocks WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        last = row["last"] if row is not None else None
        return 0 if last is None else int(last) + 1

    def finish_block(
        self, block_id: int, status: str, completed_at: str | None = None
    ) -> None:
        """Close a block and commit — the trial loop's only write barrier (§A.5)."""
        stamp = completed_at or datetime.now().isoformat(timespec="milliseconds")
        self.conn.execute(
            "UPDATE blocks SET status = ?, completed_at = ? WHERE block_id = ?",
            (status, stamp, block_id),
        )
        self.conn.commit()

    # -- trials and responses (no commit — see §A.5) -----------------------

    def add_trial(self, trial: Trial) -> int:
        design_extra = validate_design_extra(trial.module, trial.design_extra)
        cursor = self.conn.execute(
            "INSERT INTO trials (block_id, trial_index, module, condition_label, "
            "visual_token, audio_token, ear, snr_db, noise_condition, "
            "nominal_soa_ms, presentation_mode, design_extra) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                trial.block_id,
                trial.trial_index,
                trial.module,
                trial.condition_label,
                trial.visual_token,
                trial.audio_token,
                trial.ear,
                trial.snr_db,
                trial.noise_condition,
                trial.nominal_soa_ms,
                trial.presentation_mode,
                design_extra,
            ),
        )
        return _last_row_id(cursor)

    def set_trial_timing(self, trial_id: int, timing: TrialTiming) -> None:
        self.conn.execute(
            "UPDATE trials SET video_onset_s = ?, audio_onset_s = ?, "
            "actual_soa_ms = ?, dropped_frames = ?, max_frame_interval_ms = ?, "
            "presented_at = ? WHERE trial_id = ?",
            (
                timing.video_onset_s,
                timing.audio_onset_s,
                timing.actual_soa_ms,
                timing.dropped_frames,
                timing.max_frame_interval_ms,
                timing.presented_at,
                trial_id,
            ),
        )

    def add_response(self, response: Response) -> int:
        cursor = self.conn.execute(
            "INSERT INTO responses (trial_id, response_index, event_index, "
            "raw_response, free_text, category, is_correct, rt_from_burst_ms, "
            "rt_from_prompt_ms, input_device, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                response.trial_id,
                response.response_index,
                response.event_index,
                response.raw_response,
                response.free_text,
                response.category,
                None if response.is_correct is None else int(response.is_correct),
                response.rt_from_burst_ms,
                response.rt_from_prompt_ms,
                response.input_device,
                response.recorded_at,
            ),
        )
        return _last_row_id(cursor)

    def get_trials_for_block(self, block_id: int) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM trials WHERE block_id = ? ORDER BY trial_index",
            (block_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    # -- reporting --------------------------------------------------------

    def counts(self) -> dict[str, int]:
        """Row count per table — the basis of the backup verification."""
        tables = (
            "participants",
            "calibrations",
            "sessions",
            "blocks",
            "trials",
            "responses",
        )
        return {
            table: int(
                self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            )
            for table in tables
        }

    def flat_rows(self, session_id: int | None = None) -> list[dict[str, Any]]:
        """Rows of ``v_trials_flat``, optionally for one session."""
        if session_id is None:
            rows = self.conn.execute(
                "SELECT * FROM v_trials_flat ORDER BY trial_id, response_index"
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM v_trials_flat WHERE session_id = ? "
                "ORDER BY trial_id, response_index",
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def snapshot_config(self, config_dict: dict[str, Any]) -> str:
        """Serialise a config for ``sessions.config_snapshot``."""
        return json.dumps(config_dict, ensure_ascii=False, sort_keys=True, default=str)

    # -- backup -----------------------------------------------------------

    def backup(self, backup_dir: Path | str, *, label: str = "") -> Path:
        """Write a consistent copy with ``VACUUM INTO`` (never a file copy)."""
        self.conn.commit()
        return backup_database(self.conn, backup_dir, label=label)
