"""Admin panel for browsing experiment results (PySide6-based)."""


from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..data.database import Database
from ..data.export import export_participants_csv, export_trials_csv


class AdminPanel(QMainWindow):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.setWindowTitle("McGurk Deney - Admin Paneli")
        self.setMinimumSize(1000, 600)
        self._build_ui()
        self._refresh_data()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Participants tab
        self.participants_tab = QWidget()
        self._build_participants_tab()
        self.tabs.addTab(self.participants_tab, "Katılımcılar")

        # Trials tab
        self.trials_tab = QWidget()
        self._build_trials_tab()
        self.tabs.addTab(self.trials_tab, "Denemeler")

        # Bottom buttons
        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        refresh_btn = QPushButton("Yenile")
        refresh_btn.clicked.connect(self._refresh_data)
        btn_layout.addWidget(refresh_btn)

        export_trials_btn = QPushButton("Denemeleri CSV Olarak Dışa Aktar")
        export_trials_btn.clicked.connect(self._export_trials)
        btn_layout.addWidget(export_trials_btn)

        export_participants_btn = QPushButton("Katılımcıları CSV Olarak Dışa Aktar")
        export_participants_btn.clicked.connect(self._export_participants)
        btn_layout.addWidget(export_participants_btn)

        btn_layout.addStretch()

    def _build_participants_tab(self):
        layout = QVBoxLayout(self.participants_tab)
        self.participants_table = QTableWidget()
        self.participants_table.setColumnCount(7)
        self.participants_table.setHorizontalHeaderLabels(
            ["ID", "Katılımcı Kodu", "Yaş", "Cinsiyet", "Grup", "Tarih", "Notlar"]
        )
        self.participants_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.participants_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        layout.addWidget(self.participants_table)

    def _build_trials_tab(self):
        layout = QVBoxLayout(self.trials_tab)

        # Filter bar
        filter_layout = QHBoxLayout()
        layout.addLayout(filter_layout)

        filter_layout.addWidget(QLabel("Katılımcı:"))
        self.participant_filter = QComboBox()
        self.participant_filter.addItem("Tümü", None)
        self.participant_filter.currentIndexChanged.connect(self._refresh_trials)
        filter_layout.addWidget(self.participant_filter)

        filter_layout.addWidget(QLabel("Bölüm:"))
        self.section_filter = QComboBox()
        self.section_filter.addItem("Tümü", None)
        for s in ["mcgurk", "av_congruent", "audio_only", "visual_only", "dichotic"]:
            self.section_filter.addItem(s, s)
        self.section_filter.currentIndexChanged.connect(self._refresh_trials)
        filter_layout.addWidget(self.section_filter)

        filter_layout.addStretch()

        # Summary label
        self.summary_label = QLabel()
        layout.addWidget(self.summary_label)

        # Trials table
        self.trials_table = QTableWidget()
        self.trials_table.setColumnCount(13)
        self.trials_table.setHorizontalHeaderLabels(
            [
                "ID", "Katılımcı", "Bölüm", "Konuşmacı",
                "Görsel", "İşitsel", "Gürültü", "SNR",
                "Cevap", "Doğru Cevap", "Doğru?",
                "RT (video)", "RT (seçenek)",
            ]
        )
        self.trials_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.trials_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        layout.addWidget(self.trials_table)

    def _refresh_data(self):
        self._refresh_participants()
        self._refresh_trials()

    def _refresh_participants(self):
        participants = self.db.get_all_participants()
        self.participants_table.setRowCount(len(participants))

        # Rebuild the filter combo, restoring the operator's current selection
        # afterwards so pressing "Yenile" does not reset the view.
        current_filter = self.participant_filter.currentData()
        self.participant_filter.blockSignals(True)
        self.participant_filter.clear()
        self.participant_filter.addItem("Tümü", None)
        for p in participants:
            self.participant_filter.addItem(
                f"{p['participant_code']} (ID:{p['participant_id']})",
                p["participant_id"],
            )
        restored_index = self.participant_filter.findData(current_filter)
        if restored_index != -1:
            self.participant_filter.setCurrentIndex(restored_index)
        self.participant_filter.blockSignals(False)

        for row, p in enumerate(participants):
            self.participants_table.setItem(row, 0, QTableWidgetItem(str(p["participant_id"])))
            self.participants_table.setItem(row, 1, QTableWidgetItem(p["participant_code"]))
            self.participants_table.setItem(row, 2, QTableWidgetItem(str(p["age"])))
            self.participants_table.setItem(row, 3, QTableWidgetItem(p["gender"]))
            self.participants_table.setItem(row, 4, QTableWidgetItem(p["group"]))
            self.participants_table.setItem(row, 5, QTableWidgetItem(p["created_at"]))
            self.participants_table.setItem(row, 6, QTableWidgetItem(p.get("notes", "")))

    def _refresh_trials(self):
        trials = self.db.get_all_trials()

        # Apply filters
        pid_filter = self.participant_filter.currentData()
        if pid_filter is not None:
            trials = [t for t in trials if t["participant_id"] == pid_filter]

        section_filter = self.section_filter.currentData()
        if section_filter is not None:
            trials = [t for t in trials if t["section_type"] == section_filter]

        # Summary.  Trials from sections without a correct answer (McGurk,
        # dichotic) store NULL and are excluded from the accuracy figure —
        # counting them as errors would misrepresent the data.
        total = len(trials)
        scored = [t for t in trials if t["is_correct"] is not None]
        correct = sum(1 for t in scored if t["is_correct"])
        pct = (correct / len(scored) * 100) if scored else 0
        self.summary_label.setText(
            f"Toplam: {total} deneme  |  "
            f"Puanlanabilir: {len(scored)}  |  "
            f"Doğru: {correct} ({pct:.1f}%)"
        )

        self.trials_table.setRowCount(total)
        for row, t in enumerate(trials):
            self.trials_table.setItem(row, 0, QTableWidgetItem(str(t["trial_id"])))
            self.trials_table.setItem(row, 1, QTableWidgetItem(t.get("participant_code", "")))
            self.trials_table.setItem(row, 2, QTableWidgetItem(t["section_type"]))
            self.trials_table.setItem(row, 3, QTableWidgetItem(t["speaker"]))
            self.trials_table.setItem(row, 4, QTableWidgetItem(t["visual_syllable"]))
            self.trials_table.setItem(row, 5, QTableWidgetItem(t["audio_syllable"]))
            self.trials_table.setItem(row, 6, QTableWidgetItem(t["noise_condition"]))
            self.trials_table.setItem(row, 7, QTableWidgetItem(str(t["snr_db"] or "")))
            self.trials_table.setItem(row, 8, QTableWidgetItem(t["participant_response"]))
            self.trials_table.setItem(row, 9, QTableWidgetItem(t["correct_answer"]))

            if t["is_correct"] is None:
                correct_marker = "—"  # section has no correct answer
            else:
                correct_marker = "+" if t["is_correct"] else "-"
            correct_item = QTableWidgetItem(correct_marker)
            correct_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.trials_table.setItem(row, 10, correct_item)

            self.trials_table.setItem(
                row, 11, QTableWidgetItem(f"{t['rt_from_video_end_ms']:.1f}")
            )
            self.trials_table.setItem(
                row, 12, QTableWidgetItem(f"{t['rt_from_options_shown_ms']:.1f}")
            )

    def _export_trials(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Denemeleri Kaydet", "trials_export.csv", "CSV (*.csv)"
        )
        if path:
            export_trials_csv(self.db, path)

    def _export_participants(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Katılımcıları Kaydet", "participants_export.csv", "CSV (*.csv)"
        )
        if path:
            export_participants_csv(self.db, path)
