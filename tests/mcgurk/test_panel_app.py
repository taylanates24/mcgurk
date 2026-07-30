"""Adım 10b — a light smoke test of the PySide6 panel shell.

Not a behavioural GUI test (that is manual, TEST_ADIM_10B.md): this only guards
against the window failing to build and against the session table not being
wired to the read-only browser.  It runs off-screen and is skipped wherever
PySide6 is absent — which is CI, so the Qt shell is never a CI dependency.
"""

from __future__ import annotations

import os

# Must be set before QApplication is created; harmless if PySide6 is missing.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from collections.abc import Iterator  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from mcgurk.config.loader import load_config  # noqa: E402
from mcgurk.db import Block, Database, Participant, SessionRecord, Trial  # noqa: E402
from mcgurk.panel import core  # noqa: E402
from mcgurk.panel.app import PanelWindow  # noqa: E402


@pytest.fixture(scope="module")
def qapp() -> Iterator[QApplication]:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    yield app


@pytest.fixture
def config(write_config: Any, config_dict: dict[str, Any]) -> Any:
    return load_config(write_config(config_dict), check_filesystem=False)


@pytest.fixture
def db_path(tmp_path: Path, config: Any) -> Path:
    path = tmp_path / "data" / "results.sqlite"
    db = Database(path)
    try:
        participant_id = db.add_participant(
            Participant(participant_code="P042", group_code="CTRL", age=33, sex="M")
        )
        session_id = db.start_session(
            SessionRecord(
                participant_id=participant_id,
                seed=5,
                config_snapshot=db.snapshot_config(config.model_dump(mode="json")),
                config_mode="development",
                python_version="3.10.20",
                os_name="Windows 11",
            )
        )
        block_id = db.add_block(
            Block(
                session_id=session_id,
                module="mcgurk",
                block_index=db.next_block_index(session_id),
                n_trials_planned=1,
            )
        )
        db.add_trial(
            Trial(
                block_id=block_id,
                trial_index=0,
                module="mcgurk",
                visual_token="ga",
                audio_token="ba",
                ear="left",
                design_extra={"speaker_id": 1},
            )
        )
        db.finish_block(block_id, status="completed")
    finally:
        db.close()
    return path


@pytest.fixture
def window(
    qapp: QApplication, config: Any, db_path: Path
) -> Iterator[PanelWindow]:
    win = PanelWindow(core.detect_runtime(), config, db_path)
    yield win
    win.close()


def test_window_has_the_expected_action_buttons(window: PanelWindow) -> None:
    labels = {b.text() for b in window.findChildren(QPushButton)}
    for expected in (
        "Oturum başlat",
        "Kontrol listesi",
        "Uyaranları doğrula",
        "Yedek doğrula...",
        "Analiz",
        "QC raporu",
        "Dışa aktar...",
        "Yenile",
    ):
        assert expected in labels


def test_window_lists_sessions_anonymously(window: PanelWindow) -> None:
    assert window._table.rowCount() == 1
    code_item = window._table.item(0, 1)  # anonymous code column
    group_item = window._table.item(0, 2)  # group column
    assert code_item is not None and code_item.text() == "P042"
    assert group_item is not None and group_item.text() == "CTRL"


def test_refresh_is_idempotent(window: PanelWindow) -> None:
    window.refresh_sessions()
    window.refresh_sessions()
    assert window._table.rowCount() == 1


def test_missing_database_leaves_an_empty_table(
    qapp: QApplication, config: Any, tmp_path: Path
) -> None:
    win = PanelWindow(core.detect_runtime(), config, tmp_path / "nope.sqlite")
    try:
        assert win._table.rowCount() == 0
    finally:
        win.close()
