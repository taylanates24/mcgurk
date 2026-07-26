"""Database backups.

A 12-month clinical study kept in a single SQLite file is an unacceptable risk
(steps.md Adım 1), and a plain file copy is not a backup: in WAL mode the
``.sqlite`` file alone can be missing the most recent commits, so the copy is
silently inconsistent.  ``VACUUM INTO`` asks SQLite itself for a consistent,
fully checkpointed copy.

An untested backup is not a backup either — ``tools/verify_backup.py`` opens
one and checks it.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

BACKUP_PREFIX = "mcgurk"
BACKUP_SUFFIX = ".sqlite"
_LABEL_RE = re.compile(r"[^A-Za-z0-9_-]+")


class BackupError(RuntimeError):
    """Raised when a backup cannot be written."""


def backup_filename(when: datetime | None = None, label: str = "") -> str:
    """``mcgurk_<timestamp>[_<label>].sqlite``.

    The timestamp is basic-format ISO 8601: extended format uses colons, which
    are illegal in Windows filenames.
    """
    stamp = (when or datetime.now()).strftime("%Y%m%dT%H%M%S")
    clean_label = _LABEL_RE.sub("-", label).strip("-")
    tail = f"_{clean_label}" if clean_label else ""
    return f"{BACKUP_PREFIX}_{stamp}{tail}{BACKUP_SUFFIX}"


def backup_database(
    conn: sqlite3.Connection,
    backup_dir: Path | str,
    *,
    label: str = "",
    when: datetime | None = None,
) -> Path:
    """Write a consistent copy of *conn* into *backup_dir* and return its path."""
    directory = Path(backup_dir)
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BackupError(f"Yedek dizini oluşturulamadı: {directory} ({exc})") from exc

    target = directory / backup_filename(when, label)
    if target.exists():
        raise BackupError(f"Yedek dosyası zaten var: {target}")

    try:
        # VACUUM cannot run inside a transaction, so flush first.
        conn.commit()
        conn.execute("VACUUM INTO ?", (str(target),))
    except sqlite3.Error as exc:
        raise BackupError(f"Yedek alınamadı ({target}): {exc}") from exc

    logger.info("Yedek yazıldı: %s (%d bayt)", target, target.stat().st_size)
    return target


def latest_backup(backup_dir: Path | str) -> Path | None:
    """Most recent backup in *backup_dir*, by filename timestamp."""
    directory = Path(backup_dir)
    if not directory.is_dir():
        return None
    backups = sorted(directory.glob(f"{BACKUP_PREFIX}_*{BACKUP_SUFFIX}"))
    return backups[-1] if backups else None
