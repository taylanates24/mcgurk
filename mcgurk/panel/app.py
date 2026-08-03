"""Operator panel — the PyQt6 shell (Adım 10b, Ayarlar tab in Adım 11b).

A thin Qt layer over :mod:`mcgurk.panel.core`.  The window has two tabs:

* **Panel** — the button-driven front end for a Python-illiterate operator:
  start a session, run the checklist, verify the stimuli/backups, browse
  results and export/measure/QC a session.
* **Ayarlar** — the per-module repetition counts, as spin boxes over
  ``config/experiment.yaml`` (Adım 11).  Until now raising a trial count meant
  hand-editing a 450-line commented YAML file.

All the logic — building the launch commands, reading the database, formatting
the reports, writing the config — lives in ``core``; this file only wires it to
widgets (§A10.3).

Three rules shape the wiring:

* **The panel never shares a process with PsychoPy (§A10.1).**  The experiment
  and the hardware checklist are launched as *separate processes*.  The
  experiment is launched *detached* — a session is ~75 minutes and writes to the
  database at block boundaries, so the panel closing must never kill it; the
  short report tools run attached so their output streams into the panel.
* **Long work never freezes the UI (§C10 10b).**  Subprocesses run through
  ``QProcess`` (asynchronous); the in-process analysis calls run on a worker
  thread.  While either is busy the action buttons are disabled.
* **A settings change only reaches the next session (§A11.5).**  Every session
  stores its own config in ``sessions.config_snapshot``, so nothing already
  collected moves; the tab says so on screen, because an operator who thinks
  otherwise would avoid a change they are entitled to make.

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
from PyQt6.QtGui import QCloseEvent, QFont, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..config.loader import resolve_path
from ..config.schema import ExperimentConfig
from . import core

logger = logging.getLogger(__name__)

_SESSION_COLUMNS = ("Oturum", "Katılımcı", "Grup", "Başlangıç", "Durum", "Deneme")

#: Group titles for the Ayarlar tab, keyed by ``RepField.module``.  Turkish and
#: cp1254-safe (the em dash is 0x97 there); a module with no entry falls back to
#: its own name, so adding one to the config cannot leave a nameless group box.
_MODULE_TITLES = {
    "practice": "Alıştırma",
    "mcgurk": "Modül 1 — McGurk",
    "avsr": "Modül 2 — AVSR",
    "tbw": "Modül 3 — TBW (zamansal bağlama penceresi)",
    "oddball": "Modül 4 — Oddball (dikkat kontrolü)",
    "dichotic": "Modül 5 — Dikotik dinleme",
    "cross_hearing": "Çapraz dinleme kontrolü",
}

#: Speaker tile geometry.  The prepared stills are the recording's own size
#: (640x480); these are how big this window draws them.
_SPEAKER_TILE_WIDTH = 240
_SPEAKER_TILE_HEIGHT = 180
_SPEAKER_COLUMNS = 4

#: Shown above the speaker grid.  The warning matters because the choice is
#: silent otherwise: nothing on the session screens says which face is being
#: presented, and a participant measured with two of them across sessions is a
#: broken within-subject comparison that the numbers will not reveal.
_SPEAKER_NOTICE = (
    "Oturumlarda sunulacak konuşmacıyı buradan seçin. Seçim "
    "config/experiment.yaml'a yazılır ve BUNDAN SONRAKİ oturumlar için "
    "geçerlidir; geçmiş veriler değişmez (her oturum kendi ayarını kaydeder).\n"
    "Bir katılımcının bütün modülleri AYNI konuşmacıyla ölçülmelidir — farklı "
    "yüzlerle ölçmek denek-içi karşılaştırmayı bozar. Katılımcı daha önce başka "
    "bir konuşmacıyla ölçülmüşse oturum başlarken uyarı çıkar."
)

#: Shown above the spin boxes.  §A11.5: the operator has to know that raising a
#: count is safe for the data already collected — and that it is *not* safe for
#: the comparability of a study half-run at one design and half at another.
_SETTINGS_NOTICE = (
    "Buradaki değişiklikler yalnızca BUNDAN SONRAKİ oturumları etkiler: her "
    "oturum kendi ayarlarını veritabanına kaydeder, geçmiş veriler değişmez.\n"
    "Veri toplama başladıktan sonra tekrar sayısını değiştirmek oturumları "
    "birbiriyle karşılaştırılamaz hâle getirebilir — değiştirmeden önce "
    "danışmanla konuşun."
)


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
        config_path: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._runtime = runtime
        self._config = config
        self._db_path = db_path
        # The file the Ayarlar tab edits.  Frozen this is the writable copy
        # beside the .exe, not the read-only one inside the bundle (§A10.6);
        # ``ensure_writable_config`` is the one authority on which.  Passed in
        # by ``__main__`` so a caller can point the panel somewhere else — a
        # test must never be able to rewrite the repository's own config by
        # default.
        self._config_path = config_path or core.ensure_writable_config(runtime)
        self._proc: QProcess | None = None
        self._worker: _Worker | None = None
        self._sessions: list[core.SessionRow] = []
        self._action_buttons: list[QPushButton] = []
        self._spins: dict[str, QSpinBox] = {}

        self.setWindowTitle(
            f"McGurk / SSD Operatör Paneli - {config.experiment.name} "
            f"v{config.experiment.version} ({config.experiment.mode})"
        )
        self.setMinimumSize(1000, 640)
        self._build_ui()
        self.refresh_sessions()

    # -- construction -----------------------------------------------------

    def _build_ui(self) -> None:
        tabs = QTabWidget()
        tabs.addTab(self._build_panel_tab(), "Panel")
        tabs.addTab(self._build_speaker_tab(), "Konuşmacı")
        tabs.addTab(self._build_settings_tab(), "Ayarlar")
        self.setCentralWidget(tabs)
        self._tabs = tabs
        self._show_status("Hazır")

    def _build_panel_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addLayout(self._build_action_bar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_results_panel())
        splitter.addWidget(self._build_output_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, stretch=1)
        return page

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

    # -- Ayarlar tab (Adım 11b) -------------------------------------------

    def _build_speaker_tab(self) -> QWidget:
        """The prepared speakers as photographs, one of them ticked.

        A face is what "konuşmacı 5" means to the person choosing; an id is not,
        and neither is a folder name.  The choice is written into
        ``config/experiment.yaml`` rather than asked at the start of each
        session: one participant is measured with one face, so this is a
        property of the installation, not of the sitting (Adım 12c-ii).
        """
        page = QWidget()
        layout = QVBoxLayout(page)

        notice = QLabel(_SPEAKER_NOTICE)
        notice.setWordWrap(True)
        layout.addWidget(notice)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        self._speaker_grid = QGridLayout(inner)
        self._speaker_buttons = QButtonGroup(self)
        self._speaker_buttons.setExclusive(True)
        scroll.setWidget(inner)
        layout.addWidget(scroll, stretch=1)

        row = QHBoxLayout()
        row.addWidget(self._button("Konuşmacıyı kaydet", self.save_speaker))
        row.addStretch()
        layout.addLayout(row)

        self._speaker_status = QLabel()
        self._speaker_status.setWordWrap(True)
        layout.addWidget(self._speaker_status)

        self._reload_speaker_tiles()
        return page

    def _reload_speaker_tiles(self) -> None:
        """Rebuild the grid from the config and the prepared stills."""
        for button in list(self._speaker_buttons.buttons()):
            self._speaker_buttons.removeButton(button)
        while self._speaker_grid.count():
            item = self._speaker_grid.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

        try:
            options = core.speaker_options(
                self._config, self._runtime, db_path=self._db_path
            )
        except core.PanelError as exc:  # pragma: no cover - unreadable database
            self._speaker_status.setText(f"Konuşmacılar okunamadı: {exc}")
            return

        for index, option in enumerate(options):
            tile = QGroupBox()
            tile_layout = QVBoxLayout(tile)

            picture = QLabel()
            picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if option.image is not None:
                pixmap = QPixmap(str(option.image))
                if not pixmap.isNull():
                    # Scaled to fit rather than written small: the prepared still
                    # is the recording's own resolution, and how big to draw it
                    # is this window's business (Adım 12c-ii).
                    picture.setPixmap(
                        pixmap.scaled(
                            _SPEAKER_TILE_WIDTH,
                            _SPEAKER_TILE_HEIGHT,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
            if picture.pixmap() is None or picture.pixmap().isNull():
                picture.setText("(resim yok)")
                picture.setFixedSize(_SPEAKER_TILE_WIDTH, _SPEAKER_TILE_HEIGHT)
            tile_layout.addWidget(picture)

            choice = QRadioButton(f"{option.label}  ({option.n_sessions} oturum)")
            choice.setChecked(option.selected)
            self._speaker_buttons.addButton(choice, option.speaker_id)
            tile_layout.addWidget(choice)

            self._speaker_grid.addWidget(
                tile, index // _SPEAKER_COLUMNS, index % _SPEAKER_COLUMNS
            )

        current = self._speaker_buttons.checkedId()
        if current < 0:
            self._speaker_status.setText(
                "Config'te sabit bir konuşmacı yok (speaker_selection.strategy "
                "'fixed' değil). Birini seçip kaydedin."
            )
        else:
            self._speaker_status.setText(
                f"Şu anki konuşmacı: {current}. Oturumlar bunu kullanır."
            )

    def save_speaker(self) -> None:
        """Write the ticked speaker into the config, validate, roll back on error."""
        if self._is_busy():
            return
        speaker_id = self._speaker_buttons.checkedId()
        if speaker_id < 0:
            QMessageBox.information(
                self, "Konuşmacı", "Önce bir konuşmacı seçin."
            )
            return
        try:
            config = core.save_speaker(
                self._config_path, self._runtime.writable_root, speaker_id
            )
        except core.ConfigError as exc:
            self._append(f"[Konuşmacı] HATA: {exc}")
            QMessageBox.critical(self, "Konuşmacı kaydedilemedi", str(exc))
            return
        self._config = config
        self._reload_speaker_tiles()
        self._append(
            f"\n[Konuşmacı] kaydedildi: konuşmacı {speaker_id} "
            f"({self._config_path}). Bundan sonraki oturumlar bu yüzü kullanır."
        )
        self._show_status(f"Konuşmacı kaydedildi - {speaker_id}")

    def _build_settings_tab(self) -> QWidget:
        """Spin boxes over the editable trial counts, with a live total."""
        page = QWidget()
        layout = QVBoxLayout(page)

        notice = QLabel(_SETTINGS_NOTICE)
        notice.setWordWrap(True)
        layout.addWidget(notice)

        # Scrolled: seven group boxes do not fit a small laptop screen, and a
        # settings pane that hides its Kaydet button below the fold is worse
        # than no settings pane.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        for group in self._build_settings_groups():
            inner_layout.addWidget(group)
        inner_layout.addWidget(self._build_readonly_note())
        inner_layout.addStretch()
        scroll.setWidget(inner)
        layout.addWidget(scroll, stretch=1)

        self._design_label = QLabel()
        self._design_label.setWordWrap(True)
        font = QFont("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._design_label.setFont(font)
        layout.addWidget(self._design_label)

        row = QHBoxLayout()
        row.addWidget(self._button("Kaydet", self.save_settings))
        row.addWidget(self._button("Varsayılana dön", self.reset_settings))
        row.addStretch()
        layout.addLayout(row)

        # Which file the two buttons above act on.  Frozen this is not the path
        # the operator would guess (it is beside the .exe, not inside it), and
        # a support question about "the config" needs an answer on screen.
        path_label = QLabel(f"Düzenlenen dosya: {self._config_path}")
        path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        path_label.setEnabled(False)
        layout.addWidget(path_label)

        self._refresh_design_preview()
        return page

    def _build_settings_groups(self) -> list[QGroupBox]:
        """One group box per module, in the order the fields come back in."""
        groups: list[QGroupBox] = []
        current: QFormLayout | None = None
        current_module = ""
        for field in core.rep_fields(self._config):
            if current is None or field.module != current_module:
                box = QGroupBox(_MODULE_TITLES.get(field.module, field.module))
                current = QFormLayout(box)
                current_module = field.module
                groups.append(box)
            spin = QSpinBox()
            spin.setRange(field.minimum, field.maximum)
            spin.setValue(field.value)
            # A four-digit counter stretched across the pane reads as a text
            # field; kept narrow, the row reads as "label -> number".
            spin.setMaximumWidth(90)
            if field.note:
                spin.setToolTip(field.note)
            spin.valueChanged.connect(self._refresh_design_preview)
            self._spins[field.key] = spin
            row = QHBoxLayout()
            row.addWidget(spin)
            if field.note:
                note = QLabel(field.note)
                note.setEnabled(False)
                row.addWidget(note)
            row.addStretch()
            current.addRow(field.label, row)
        return groups

    def _build_readonly_note(self) -> QGroupBox:
        """Why GIN has no spin box — otherwise its absence reads as an omission.

        A group box like the others, disabled: "this module exists and is not
        editable" is a different message from "this module was forgotten".
        """
        gin = self._config.modules.gin
        box = QGroupBox("Modül 6 — GIN (değiştirilemez)")
        layout = QVBoxLayout(box)
        label = QLabel(
            f"{gin.total_trials()} segment, boşluk başına {gin.reps_per_gap} "
            "sunum. Segmentler hazır uyaran setinden gelir ve sunum sayısı "
            f"{gin.threshold_criterion} eşik kuralına bağlıdır; buradan "
            "değiştirmek klinik normları geçersiz kılardı."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        box.setEnabled(False)
        return box

    def _current_changes(self) -> dict[str, int]:
        return {key: spin.value() for key, spin in self._spins.items()}

    def _refresh_design_preview(self) -> None:
        """Recompute "Toplam: N deneme / ~X dk" from the spin boxes.

        In memory only — nothing is written until Kaydet.  The numbers come
        from ``config.trial_counts()`` on a preview copy, so they are produced
        by the same code the session runs rather than by arithmetic repeated
        here.
        """
        try:
            preview = core.preview_reps(self._config, self._current_changes())
        except core.ConfigError as exc:
            self._design_label.setText(f"Geçersiz değer: {exc}")
            return
        rows = core.design_rows(preview)
        per_module = "  ".join(f"{row.module} {row.n_trials}" for row in rows)
        total = sum(row.n_trials for row in rows)
        minutes = preview.estimated_duration_s() / 60
        self._design_label.setText(
            f"{per_module}\n"
            f"TOPLAM: {total} deneme  /  yaklaşık {minutes:.1f} dk "
            "(alt sınır: yönergeler ve geçişler sayılmaz)"
        )

    def _reload_settings_fields(self) -> None:
        """Put the saved config's values back into the spin boxes."""
        self._set_spin_values(
            {field.key: field.value for field in core.rep_fields(self._config)}
        )

    def _set_spin_values(self, values: dict[str, int]) -> list[str]:
        """Set the named spin boxes, refreshing the total once at the end.

        Signals are blocked during the loop: without that, setting seven values
        would rebuild the preview config seven times, and the intermediate
        states can be invalid designs whose error message flashes past.
        Returns the keys that had no value to set.
        """
        missing: list[str] = []
        for key, spin in self._spins.items():
            if key not in values:
                missing.append(key)
                continue
            spin.blockSignals(True)
            spin.setValue(values[key])
            spin.blockSignals(False)
        self._refresh_design_preview()
        return missing

    def save_settings(self) -> None:
        """Write the spin-box values to the config, validate, roll back on error."""
        if self._is_busy():
            return
        try:
            config = core.save_reps(
                self._config_path, self._runtime.writable_root, self._current_changes()
            )
        except core.ConfigError as exc:
            self._append(f"[Ayarlar] HATA: {exc}")
            QMessageBox.critical(self, "Ayarlar kaydedilemedi", str(exc))
            return
        self._config = config
        self._reload_settings_fields()
        total = sum(row.n_trials for row in core.design_rows(config))
        # No confirmation dialog on the happy path: the status bar, the changed
        # total and the output line already say it worked, and a modal the
        # operator has to dismiss after every save trains them to click through
        # dialogs — including the one that reports a rollback.
        self._append(
            f"\n[Ayarlar] kaydedildi: {self._config_path} "
            f"({total} deneme). Bundan sonraki oturumlar bu tasarımı kullanır."
        )
        self._show_status(f"Ayarlar kaydedildi - {total} deneme")

    def reset_settings(self) -> None:
        """Put the factory counts into the spin boxes — without saving them.

        Deliberately not a save: the operator sees what the defaults would cost
        (the live total updates) and then decides.  A reset that wrote straight
        to disk would be an undoable click.
        """
        answer = QMessageBox.question(
            self,
            "Varsayılana dön",
            "Tüm tekrar sayıları fabrika değerlerine dönecek.\n\n"
            "Bu işlem dosyaya YAZMAZ; değerleri görüp Kaydet'e basmanız "
            "gerekir. Devam edilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            defaults = core.default_reps(self._runtime)
        except core.ConfigError as exc:
            self._append(f"[Ayarlar] HATA: {exc}")
            QMessageBox.critical(self, "Varsayılanlar okunamadı", str(exc))
            return
        missing = self._set_spin_values(defaults)
        if missing:
            # A field the defaults file does not know about (a newly enabled
            # stimulus set, say).  Left untouched rather than guessed at, and
            # said out loud: a silent partial reset is the worst outcome here.
            self._append(
                "[Ayarlar] varsayilan dosyasinda karsiligi olmayan alanlar "
                "degistirilmedi: " + ", ".join(missing)
            )
        self._show_status("Varsayılan değerler yüklendi - kaydetmek için Kaydet")

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
