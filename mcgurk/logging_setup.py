"""Structured logging: a per-session file plus a quieter console.

The file gets everything (DEBUG by default) because a timing anomaly is
usually only diagnosable after the session; the console gets what the operator
can act on while a participant is sitting in front of the screen.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

FILE_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
CONSOLE_FORMAT = "%(levelname)-8s %(message)s"


def session_log_path(log_dir: Path | str, when: datetime | None = None) -> Path:
    stamp = (when or datetime.now()).strftime("%Y%m%dT%H%M%S")
    return Path(log_dir) / f"session_{stamp}.log"


def setup_logging(
    log_dir: Path | str,
    *,
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    when: datetime | None = None,
) -> Path:
    """Configure root logging and return the log file path.

    Existing handlers are replaced, so calling this twice in one process (tests,
    a relaunched session) does not duplicate every line.
    """
    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    log_path = session_log_path(directory, when)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(getattr(logging, file_level.upper()))
    file_handler.setFormatter(logging.Formatter(FILE_FORMAT))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, console_level.upper()))
    console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))

    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    # The root level has to be the more permissive of the two, otherwise it
    # filters records before the handlers ever see them.
    root.setLevel(
        min(
            getattr(logging, file_level.upper()),
            getattr(logging, console_level.upper()),
        )
    )
    root.addHandler(file_handler)
    root.addHandler(console_handler)
    return log_path
