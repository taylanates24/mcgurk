"""Adım 10b/11b — a light smoke test of the PyQt6 panel shell.

Not a behavioural GUI test (that is manual, TEST_ADIM_10B.md / TEST_ADIM_11.md):
this only guards against the window failing to build, against the session table
not being wired to the read-only browser, and — since Adım 11b — against the
Ayarlar tab losing its wiring to ``core``.  It runs off-screen and is skipped
wherever PyQt6 is absent, which is CI, so the Qt shell is never a CI dependency.

Every window here is built with an explicit ``config_path`` pointing into
``tmp_path``.  Without it the panel would resolve the repository's own
``config/experiment.yaml``, and a test that clicks Kaydet would edit the shipped
design.
"""

from __future__ import annotations

import os

# Must be set before QApplication is created; harmless if PyQt6 is missing.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from collections.abc import Iterator  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import (  # noqa: E402
    QApplication,
    QMessageBox,
    QPushButton,
    QTabWidget,
)

from mcgurk.config.loader import load_config  # noqa: E402
from mcgurk.db import Block, Database, Participant, SessionRecord, Trial  # noqa: E402
from mcgurk.panel import core  # noqa: E402
from mcgurk.panel.app import PanelWindow  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def qapp() -> Iterator[QApplication]:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    yield app


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    """A byte copy of the shipped config, so Kaydet writes here and not in git."""
    path = tmp_path / "config" / "experiment.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((PROJECT_ROOT / "config" / "experiment.yaml").read_bytes())
    return path


@pytest.fixture
def config(config_path: Path, tmp_path: Path) -> Any:
    return load_config(config_path, project_root=tmp_path, check_filesystem=False)


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
def no_dialogs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Answer the modal dialogs instead of showing them.

    A ``QMessageBox`` blocks on the event loop even under the offscreen
    platform plugin, so an unpatched ``critical()`` hangs the test run rather
    than failing it.  ``question`` answers Yes — the tests that use it are the
    ones exercising what happens *after* a confirmation.
    """
    monkeypatch.setattr(
        QMessageBox, "critical", staticmethod(lambda *a, **k: None)
    )
    monkeypatch.setattr(
        QMessageBox, "information", staticmethod(lambda *a, **k: None)
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )


@pytest.fixture
def window(
    qapp: QApplication, config: Any, db_path: Path, config_path: Path
) -> Iterator[PanelWindow]:
    win = PanelWindow(core.detect_runtime(), config, db_path, config_path=config_path)
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
        "Sil...",
        "Yenile",
        # Adım 11b
        "Kaydet",
        "Varsayılana dön",
    ):
        assert expected in labels


def test_window_has_a_panel_a_speaker_and_a_settings_tab(window: PanelWindow) -> None:
    tabs = window.findChildren(QTabWidget)
    assert len(tabs) == 1
    assert [tabs[0].tabText(i) for i in range(tabs[0].count())] == [
        "Panel",
        "Konuşmacı",
        "Ayarlar",
    ]


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
    qapp: QApplication, config: Any, tmp_path: Path, config_path: Path
) -> None:
    win = PanelWindow(
        core.detect_runtime(),
        config,
        tmp_path / "nope.sqlite",
        config_path=config_path,
    )
    try:
        assert win._table.rowCount() == 0
    finally:
        win.close()


# ------------------------------------------------------- Ayarlar (Adım 11b)


def test_settings_fields_start_at_the_config_values(
    window: PanelWindow, config: Any
) -> None:
    spins = window._spins
    assert spins["modules.tbw.reps_per_soa"].value() == config.modules.tbw.reps_per_soa
    assert spins["session.practice_trials"].value() == config.session.practice_trials
    # GIN is read-only, so it has no spin box at all.
    assert not any("gin" in key for key in spins)


def test_settings_total_updates_live_without_writing(
    window: PanelWindow, config_path: Path
) -> None:
    before = config_path.read_bytes()
    assert "TOPLAM: 797 deneme" in window._design_label.text()

    window._spins["modules.dichotic.reps"].setValue(10)
    assert "TOPLAM: 827 deneme" in window._design_label.text()
    # Live means in memory: nothing has reached the disk yet.
    assert config_path.read_bytes() == before


def test_settings_report_an_impossible_value_instead_of_a_total(
    window: PanelWindow,
) -> None:
    window._spins["modules.oddball.n_trials"].setValue(1)
    assert window._design_label.text().startswith("Geçersiz değer")


def test_save_settings_writes_the_config_and_keeps_comments(
    window: PanelWindow, config_path: Path
) -> None:
    window._spins["modules.tbw.reps_per_soa"].setValue(12)
    window.save_settings()

    text = config_path.read_text(encoding="utf-8")
    assert "reps_per_soa: 12" in text
    assert "reps is PER CELL" in text  # a comment next to an edited field
    assert window._config.modules.tbw.reps_per_soa == 12


def test_save_settings_rolls_back_an_invalid_design(
    window: PanelWindow, config_path: Path, no_dialogs: None
) -> None:
    before = config_path.read_bytes()
    window._spins["modules.oddball.n_trials"].setValue(2)
    window.save_settings()
    assert config_path.read_bytes() == before
    assert window._config.modules.oddball.n_trials == 300


def test_reset_puts_the_factory_values_in_the_spin_boxes(
    window: PanelWindow, config_path: Path, no_dialogs: None
) -> None:
    before = config_path.read_bytes()
    window._spins["modules.dichotic.reps"].setValue(9)
    window.reset_settings()  # no_dialogs answers the confirmation with Yes
    assert window._spins["modules.dichotic.reps"].value() == 5
    # A reset does not save: the operator sees the cost first (§C11 11b).
    assert config_path.read_bytes() == before


# ---------------------------------------------------- Konuşmacı (Adım 12c-ii)


def test_speaker_tab_offers_every_prepared_speaker(
    window: PanelWindow, config: Any
) -> None:
    buttons = window._speaker_buttons.buttons()
    assert len(buttons) == len(config.stimulus_prep.speaker_ids())
    assert sorted(window._speaker_buttons.id(b) for b in buttons) == (
        config.stimulus_prep.speaker_ids()
    )


def test_speaker_tab_ticks_the_configured_speaker(
    window: PanelWindow, config: Any
) -> None:
    """Default ticked: the operator confirms rather than re-chooses."""
    assert window._speaker_buttons.checkedId() == config.speaker_selection.fixed_id


def test_speaker_tab_shows_how_many_sessions_each_has(window: PanelWindow) -> None:
    """The db fixture ran one session with speaker 1."""
    labels = {b.text() for b in window._speaker_buttons.buttons()}
    assert any("(1 oturum)" in text for text in labels)
    assert any("(0 oturum)" in text for text in labels)


def test_saving_a_speaker_writes_it_to_the_config(
    window: PanelWindow, config_path: Path, tmp_path: Path, no_dialogs: None
) -> None:
    button = next(
        b for b in window._speaker_buttons.buttons()
        if window._speaker_buttons.id(b) == 6
    )
    button.setChecked(True)
    window.save_speaker()

    written = load_config(config_path, project_root=tmp_path, check_filesystem=False)
    assert written.speaker_selection.fixed_id == 6
    assert written.modules.dichotic.speaker_id == 6
    # And the tab now reports the new one.
    assert window._speaker_buttons.checkedId() == 6


def test_saving_the_same_speaker_leaves_the_file_untouched(
    window: PanelWindow, config_path: Path, no_dialogs: None
) -> None:
    before = config_path.read_bytes()
    window.save_speaker()
    assert config_path.read_bytes() == before


def test_the_speaker_button_is_locked_while_a_tool_runs(window: PanelWindow) -> None:
    labels = {b.text() for b in window._action_buttons}
    assert "Konuşmacıyı kaydet" in labels
