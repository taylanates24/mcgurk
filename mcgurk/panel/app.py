"""Operator panel — the PyQt6 shell (Adım 10b).

A thin Qt layer over :mod:`mcgurk.panel.core`.  The window is a button-driven
front end for a Python-illiterate operator: start a session, run the checklist,
verify the stimuli/backups, browse results and export/measure/QC a session.  All
the logic — building the launch commands, reading the database, formatting the
reports — lives in ``core``; this file only wires it to widgets (§A10.3).

Two rules shape the wiring:

* **The panel never shares a process with PsychoPy (§A10.1).**  The experiment
  and the hardware checklist are launched as *separate processes*.  The
  experiment is launched *detached* — a session is ~75 minutes and writes to the
  database at block boundaries, so the panel closing must never kill it; the
  short report tools run attached so their output streams into the panel.
* **Long work never freezes the UI (§C10 10b).**  Subprocesses run through
  ``QProcess`` (asynchronous); the in-process analysis calls run on a worker
  thread.  While either is busy the action buttons are disabled.

This module imports PyQt6 but **no PsychoPy** (§A10.2, enforced by the package
boundary test's AST scan, which never has to import this file).  PyQt6 is the one
Qt binding the whole app uses: PsychoPy's own dialogs (``psychopy.gui``) support
only PyQt, and PyInstaller cannot bundle two Qt bindings, so the panel uses PyQt6
too rather than PySide6.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import QProcess, QProcessEnvironment, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..config.loader import resolve_path
from ..config.schema import ExperimentConfig
from . import core

logger = logging.getLogger(__name__)

_SESSION_COLUMNS = ("Oturum", "Katılımcı", "Grup", "Başlangıç", "Durum", "Deneme")


class _Worker(QThread):
    """Run one callable off the GUI thread and report the outcome.

    ``done`` carries ``(ok, result_or_exception)``.  The catch-all is
    deliberate: an analysis error (a degenerate fit, a missing session) must
    reach the operator as a message, never crash the panel.  It is logged too,
    so the traceback is not lost.
    """

    done = pyqtSignal(bool, object)

    def __init__(self, fn: Callable[[], object]) -> None:
        super().__init__()
        self._fn = fn

    def run(self) -> None:
        try:
            result = self._fn()
        except Exception as exc:  # noqa: BLE001 - surfaced to the operator, logged
            logger.exception("Panel işçisi başarısız")
            self.done.emit(False, exc)
        else:
            self.done.emit(True, result)


class PanelWindow(QMainWindow):
    """The operator panel's main window."""

    def __init__(
        self,
        runtime: core.Runtime,
        config: ExperimentConfig,
        db_path: Path,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._runtime = runtime
        self._config = config
        self._db_path = db_path
        self._proc: QProcess | None = None
        self._worker: _Worker | None = None
        self._sessions: list[core.SessionRow] = []
        self._action_buttons: list[QPushButton] = []

        self.setWindowTitle(
            f"McGurk / SSD Operatör Paneli - {config.experiment.name} "
            f"v{config.experiment.version} ({config.experiment.mode})"
        )
        self.setMinimumSize(1000, 640)
        self._build_ui()
        self.refresh_sessions()

    # -- construction -----------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        layout.addLayout(self._build_action_bar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_results_panel())
        splitter.addWidget(self._build_output_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, stretch=1)

        self._show_status("Hazır")

    def _button(self, text: str, handler: Callable[[], None]) -> QPushButton:
        button = QPushButton(text)
        button.clicked.connect(handler)
        self._action_buttons.append(button)
        return button

    def _build_action_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.addWidget(self._button("Oturum başlat", self.start_session))
        bar.addWidget(self._button("Kontrol listesi", self.run_checklist))
        bar.addWidget(self._button("Uyaranları doğrula", self.verify_stimuli))
        bar.addWidget(self._button("Yedek doğrula...", self.verify_backup))
        bar.addStretch()
        return bar

    def _build_results_panel(self) -> QWidget:
        group = QGroupBox("Sonuçlar (anonim)")
        layout = QVBoxLayout(group)

        self._table = QTableWidget(0, len(_SESSION_COLUMNS))
        self._table.setHorizontalHeaderLabels(list(_SESSION_COLUMNS))
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self._table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, stretch=1)

        row = QHBoxLayout()
        row.addWidget(self._button("Yenile", self.refresh_sessions))
        row.addWidget(self._button("Analiz", self.show_measures))
        row.addWidget(self._button("QC raporu", self.show_qc))
        row.addWidget(self._button("Dışa aktar...", self.export_selected))
        row.addWidget(self._button("Sil...", self.delete_selected))
        row.addStretch()
        layout.addLayout(row)
        return group

    def _build_output_panel(self) -> QWidget:
        group = QGroupBox("Çıktı")
        layout = QVBoxLayout(group)
        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setPlaceholderText(
            "İşlem çıktıları ve raporlar burada görünür."
        )
        # Monospace so the checklist/verify report columns line up (the status
        # words are replaced with coloured dots, padded to the same width).
        font = QFont("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._output.setFont(font)
        layout.addWidget(self._output)
        return group

    # -- helpers ----------------------------------------------------------

    def _append(self, text: str) -> None:
        # appendHtml so a leading YESIL/UYARI/KIRMIZI becomes a coloured dot;
        # core.status_html escapes everything else, so there is no injection.
        self._output.appendHtml(core.status_html(text))
        scrollbar = self._output.verticalScrollBar()
        if scrollbar is not None:
            scrollbar.setValue(scrollbar.maximum())

    def _show_status(self, text: str) -> None:
        # QMainWindow.statusBar() is typed Optional; it is created on first call.
        bar = self.statusBar()
        if bar is not None:
            bar.showMessage(text)

    def _set_busy(self, busy: bool, label: str = "") -> None:
        for button in self._action_buttons:
            button.setEnabled(not busy)
        self._show_status(f"Çalışıyor: {label}" if busy else "Hazır")

    def _is_busy(self) -> bool:
        if self._proc is not None or (
            self._worker is not None and self._worker.isRunning()
        ):
            QMessageBox.information(
                self, "Meşgul", "Bir işlem sürüyor; bitmesini bekleyin."
            )
            return True
        return False

    def _selected_session_id(self) -> int | None:
        # Annotated: QTableWidget.currentRow() is Any where PyQt6 is absent
        # (CI), which would make the returned session_id Any (no-any-return).
        row: int = self._table.currentRow()
        if row < 0 or row >= len(self._sessions):
            QMessageBox.information(
                self, "Oturum seçin", "Önce listeden bir oturum seçin."
            )
            return None
        return self._sessions[row].session_id

    # -- results browsing -------------------------------------------------

    def refresh_sessions(self) -> None:
        """Reload the session table from the database (read-only, anonymous)."""
        try:
            self._sessions = core.list_sessions(self._db_path)
        except core.PanelError as exc:
            self._sessions = []
            self._show_status(str(exc))
        self._table.setRowCount(len(self._sessions))
        for row, session in enumerate(self._sessions):
            values = (
                str(session.session_id),
                session.participant_code,
                session.group_code,
                session.started_at,
                session.status,
                str(session.n_trials),
            )
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(value))
        if self._sessions:
            self._show_status(f"{len(self._sessions)} oturum")

    # -- subprocess launches (§A10.1) -------------------------------------

    def start_session(self) -> None:
        """Launch a full session as a detached process (survives panel close)."""
        command = core.session_command(self._runtime, db=self._db_path)
        self._append(f"\n$ Oturum baslatiliyor: {' '.join(command)}")
        ok, pid = QProcess.startDetached(
            command[0], command[1:], str(self._runtime.resource_root)
        )
        if ok:
            self._append(
                f"Oturum ayri surecte basladi (PID {pid}). "
                "Deney penceresini izleyin; panel acik kalabilir."
            )
        else:
            self._append("HATA: oturum sureci baslatilamadi.")
            QMessageBox.critical(
                self, "Başlatılamadı", "Oturum süreci başlatılamadı."
            )

    def run_checklist(self) -> None:
        self._launch_captured(
            core.checklist_command(self._runtime), "Kontrol listesi"
        )

    def verify_stimuli(self) -> None:
        self._launch_captured(
            core.verify_stimuli_command(self._runtime), "Uyaran doğrulama"
        )

    def verify_backup(self) -> None:
        if self._is_busy():
            return
        start_dir = str(self._runtime.writable_root / "backups")
        path, _ = QFileDialog.getOpenFileName(
            self, "Yedek dosyası seçin", start_dir, "SQLite (*.sqlite);;Tümü (*)"
        )
        if not path:
            return
        self._launch_captured(
            core.verify_backup_command(
                self._runtime, path, compare_with=self._db_path
            ),
            "Yedek doğrulama",
        )

    def _launch_captured(self, command: list[str], label: str) -> None:
        """Run a short report tool attached, streaming its output to the panel."""
        if self._is_busy():
            return
        self._append(f"\n$ {label}: {' '.join(command)}")
        self._set_busy(True, label)
        proc = QProcess(self)
        proc.setWorkingDirectory(str(self._runtime.resource_root))
        # Force the child's stdio to UTF-8 so its Turkish output decodes cleanly
        # in the panel: a redirected pipe otherwise uses the Windows ANSI code
        # page (cp1254), which _drain would then mis-read as UTF-8.
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONIOENCODING", "utf-8")
        proc.setProcessEnvironment(env)
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(lambda: self._drain(proc))
        proc.finished.connect(lambda code, _status: self._captured_finished(label, code))
        proc.errorOccurred.connect(lambda _err: self._captured_error(label))
        self._proc = proc
        proc.start(command[0], command[1:])

    def _drain(self, proc: QProcess) -> None:
        chunk = bytes(proc.readAllStandardOutput().data()).decode("utf-8", "replace")
        if chunk:
            self._append(chunk.rstrip("\n"))

    def _captured_finished(self, label: str, code: int) -> None:
        self._drain(self._proc) if self._proc is not None else None
        verdict = "tamam (0)" if code == 0 else f"KIRMIZI (çıkış {code})"
        self._append(f"[{label}] bitti: {verdict}")
        self._proc = None
        self._set_busy(False)

    def _captured_error(self, label: str) -> None:
        self._append(f"[{label}] HATA: süreç başlatılamadı veya çöktü.")
        self._proc = None
        self._set_busy(False)

    # -- in-process analysis (worker thread) ------------------------------

    def show_measures(self) -> None:
        session_id = self._selected_session_id()
        if session_id is None:
            return
        self._run_worker(
            lambda: core.measures_text(self._db_path, session_id),
            f"Analiz (oturum {session_id})",
        )

    def show_qc(self) -> None:
        session_id = self._selected_session_id()
        if session_id is None:
            return
        self._run_worker(
            lambda: core.qc_text(self._db_path, session_id),
            f"QC raporu (oturum {session_id})",
        )

    def export_selected(self) -> None:
        session_id = self._selected_session_id()
        if session_id is None:
            return
        if self._is_busy():
            return
        out_dir = QFileDialog.getExistingDirectory(
            self, "Dışa aktarım klasörü seçin", str(self._runtime.writable_root)
        )
        if not out_dir:
            return
        self._run_worker(
            lambda: core.export_session(self._db_path, out_dir, session_id),
            f"Dışa aktarım (oturum {session_id})",
        )

    def delete_selected(self) -> None:
        """Delete the selected session, after an explicit confirmation (§A10.5).

        A fresh backup is taken before the delete (in ``core.delete_session``),
        so the operator can recover from a mistaken deletion.
        """
        session_id = self._selected_session_id()
        if session_id is None:
            return
        if self._is_busy():
            return
        row = next(
            (s for s in self._sessions if s.session_id == session_id), None
        )
        who = (
            f"{row.participant_code} ({row.group_code}), {row.n_trials} deneme"
            if row is not None
            else f"oturum {session_id}"
        )
        answer = QMessageBox.warning(
            self,
            "Oturumu sil",
            f"Oturum {session_id} — {who}\n\n"
            "Bu oturum ve TÜM denemeleri kalıcı olarak silinecek.\n"
            "Silmeden önce otomatik bir yedek alınır. Emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        backup_dir = resolve_path(
            self._runtime.writable_root, self._config.paths.backups
        )

        def _do() -> str:
            result = core.delete_session(
                self._db_path, session_id, backup_dir=backup_dir
            )
            return (
                f"Oturum {session_id} silindi: {result.deleted}. "
                f"Silmeden önceki yedek: {result.backup_path}"
            )

        self._run_worker(_do, f"Oturum {session_id} silme")

    def _run_worker(self, fn: Callable[[], object], label: str) -> None:
        if self._is_busy():
            return
        self._append(f"\n$ {label}...")
        self._set_busy(True, label)
        worker = _Worker(fn)
        worker.done.connect(lambda ok, res: self._worker_done(label, ok, res))
        self._worker = worker
        worker.start()

    def _worker_done(self, label: str, ok: bool, result: object) -> None:
        if ok:
            if isinstance(result, list):  # export -> file paths
                self._append(f"[{label}] yazıldı:")
                for path in result:
                    self._append(f"  {path}")
            else:
                self._append(str(result))
        else:
            self._append(f"[{label}] HATA: {result}")
        self._worker = None
        self._set_busy(False)
        # Cheap and harmless after read-only ops; after a delete it drops the
        # removed session from the table.
        self.refresh_sessions()

    # -- lifecycle --------------------------------------------------------

    def closeEvent(self, event: QCloseEvent | None) -> None:
        """A captured tool blocks close; a detached session does not.

        The experiment runs detached, so it keeps going regardless.  Only an
        attached report tool or a worker would be cut off, so closing is
        refused while one is running rather than killing it mid-write.

        ``event`` is typed Optional to match ``QWidget.closeEvent``; in practice
        Qt always passes one.
        """
        if self._proc is not None or (
            self._worker is not None and self._worker.isRunning()
        ):
            answer = QMessageBox.question(
                self,
                "İşlem sürüyor",
                "Bir işlem sürüyor. Yine de kapatılsın mı?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                if event is not None:
                    event.ignore()
                return
        if event is not None:
            event.accept()
