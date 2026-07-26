"""Session logging: a verbose file plus a quieter console."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from mcgurk.logging_setup import session_log_path, setup_logging


def test_log_file_is_created_in_the_directory(tmp_path: Path) -> None:
    path = setup_logging(tmp_path / "logs", when=datetime(2026, 7, 26, 15, 31, 49))
    assert path == tmp_path / "logs" / "session_20260726T153149.log"
    assert path.is_file()


def test_directory_is_created(tmp_path: Path) -> None:
    setup_logging(tmp_path / "yeni" / "logs")
    assert (tmp_path / "yeni" / "logs").is_dir()


def test_file_captures_debug_while_console_does_not(tmp_path: Path, capsys) -> None:
    path = setup_logging(tmp_path / "logs", console_level="WARNING", file_level="DEBUG")
    logger = logging.getLogger("mcgurk.test")
    logger.debug("ayrıntı")
    logger.warning("uyarı")
    logging.shutdown()

    contents = path.read_text(encoding="utf-8")
    assert "ayrıntı" in contents
    assert "uyarı" in contents

    console = capsys.readouterr().err
    assert "ayrıntı" not in console
    assert "uyarı" in console


def test_repeated_setup_does_not_duplicate_handlers(tmp_path: Path) -> None:
    setup_logging(tmp_path / "logs", when=datetime(2026, 7, 26, 10, 0, 0))
    setup_logging(tmp_path / "logs", when=datetime(2026, 7, 26, 11, 0, 0))
    assert len(logging.getLogger().handlers) == 2  # one file, one console
    logging.shutdown()


def test_session_log_path_format(tmp_path: Path) -> None:
    path = session_log_path(tmp_path, datetime(2026, 1, 2, 3, 4, 5))
    assert path.name == "session_20260102T030405.log"
