"""Batch mode: import many photos, get one draft per product."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vinted_tool.app.context import AppContext
from vinted_tool.services.batch_service import BatchService
from vinted_tool.ui.widgets.common import Card, heading
from vinted_tool.ui.widgets.drop_zone import DropZone
from vinted_tool.ui.workers import BatchWorker

RESULT_COLUMNS = ["Produkt", "Titel", "Preis", "Kategorie", "Status"]


class BatchPage(QWidget):
    status_message = Signal(str)
    open_listing = Signal(object)
    data_changed = Signal()

    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.ctx = context
        self._paths: list[Path] = []
        self._worker: BatchWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addWidget(
            heading(
                "Batch-Modus",
                "Viele Bilder auf einmal importieren – die App legt daraus fertige Entwürfe an.",
            )
        )

        input_card = Card("Bilder auswählen")
        self.drop_zone = DropZone(
            "Bilder oder Ordner hierher ziehen", "z. B. 20 Produktfotos auf einmal"
        )
        self.drop_zone.images_dropped.connect(self.add_paths)
        input_card.add(self.drop_zone)

        controls = QHBoxLayout()
        btn_files = QPushButton("Dateien wählen")
        btn_files.clicked.connect(self.drop_zone.browse)
        btn_folder = QPushButton("Ordner wählen")
        btn_folder.clicked.connect(self.drop_zone.browse_folder)
        btn_clear = QPushButton("Liste leeren")
        btn_clear.clicked.connect(self.clear)
        controls.addWidget(btn_files)
        controls.addWidget(btn_folder)
        controls.addWidget(btn_clear)
        controls.addStretch(1)
        controls.addWidget(QLabel("Gruppierung:"))
        self.mode_combo = QComboBox()
        for key, label in BatchService.GROUPING_MODES.items():
            self.mode_combo.addItem(label, key)
        self.mode_combo.setCurrentIndex(1)
        self.mode_combo.currentIndexChanged.connect(self._update_preview)
        controls.addWidget(self.mode_combo)
        self.use_ai_check = QCheckBox("KI-Analyse verwenden")
        self.use_ai_check.setChecked(True)
        controls.addWidget(self.use_ai_check)
        input_card.body().addLayout(controls)

        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(130)
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        input_card.add(self.file_list)

        self.preview_label = QLabel("Keine Bilder ausgewählt.")
        self.preview_label.setObjectName("Dim")
        input_card.add(self.preview_label)
        layout.addWidget(input_card)

        run_card = Card("Verarbeitung")
        run_row = QHBoxLayout()
        self.btn_start = QPushButton("Batch starten")
        self.btn_start.setObjectName("Primary")
        self.btn_start.clicked.connect(self.start)
        self.btn_cancel = QPushButton("Abbrechen")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel)
        run_row.addWidget(self.btn_start)
        run_row.addWidget(self.btn_cancel)
        run_row.addStretch(1)
        run_card.body().addLayout(run_row)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        run_card.add(self.progress)
        self.progress_label = QLabel("Bereit.")
        self.progress_label.setObjectName("Dim")
        run_card.add(self.progress_label)
        layout.addWidget(run_card)

        result_card = Card("Ergebnisse")
        self.result_table = QTableWidget(0, len(RESULT_COLUMNS))
        self.result_table.setHorizontalHeaderLabels(RESULT_COLUMNS)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.result_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.result_table.doubleClicked.connect(self._open_selected)
        result_card.add(self.result_table)
        open_row = QHBoxLayout()
        btn_open = QPushButton("Entwurf bearbeiten")
        btn_open.clicked.connect(self._open_selected)
        open_row.addWidget(btn_open)
        open_row.addStretch(1)
        result_card.body().addLayout(open_row)
        layout.addWidget(result_card, 1)

    # -------------------------------------------------------------------- data
    def add_paths(self, paths: list[Path]) -> None:
        known = {str(p) for p in self._paths}
        for path in paths:
            if str(path) not in known:
                self._paths.append(Path(path))
        self.file_list.clear()
        self.file_list.addItems([p.name for p in self._paths])
        self._update_preview()

    def clear(self) -> None:
        self._paths = []
        self.file_list.clear()
        self._update_preview()

    def refresh(self) -> None:
        self._update_preview()

    def _update_preview(self) -> None:
        if not self._paths:
            self.preview_label.setText("Keine Bilder ausgewählt.")
            return
        mode = self.mode_combo.currentData()
        groups = self.ctx.batch_service.group(self._paths, mode)
        self.preview_label.setText(
            f"{len(self._paths)} Bilder → {len(groups)} Produkt(e) werden angelegt."
        )

    # ----------------------------------------------------------------- running
    def start(self) -> None:
        if not self._paths:
            QMessageBox.information(self, "Keine Bilder", "Bitte zuerst Bilder auswählen.")
            return
        if self._worker and self._worker.isRunning():
            return
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress.setValue(0)
        self.result_table.setRowCount(0)
        self._worker = BatchWorker(
            self.ctx.batch_service,
            list(self._paths),
            mode=self.mode_combo.currentData(),
            use_ai=self.use_ai_check.isChecked(),
            parent=self,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._on_thread_done)
        self._worker.start()
        self.status_message.emit("Batch-Verarbeitung gestartet …")

    def cancel(self) -> None:
        if self._worker:
            self._worker.cancel()
            self.progress_label.setText("Abbruch angefordert – der laufende Artikel wird beendet …")

    def _on_progress(self, index: int, total: int, name: str) -> None:
        self.progress.setMaximum(max(total, 1))
        self.progress.setValue(index)
        self.progress_label.setText(f"Verarbeite {index}/{total}: {name}")

    def _on_finished(self, result) -> None:
        self.result_table.setRowCount(len(result.items))
        for row, item in enumerate(result.items):
            listing = item.listing
            status = (
                f"⚠ {item.error}" if item.error
                else f"Duplikat? {item.duplicate_of}" if item.duplicate_of
                else "Entwurf erstellt"
            )
            values = [
                item.label,
                listing.title if listing else "—",
                f"{listing.price:.2f} {listing.currency}" if listing else "—",
                " > ".join(listing.category_path) if listing else "—",
                status,
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 0 and listing:
                    cell.setData(Qt.ItemDataRole.UserRole, listing.id)
                self.result_table.setItem(row, column, cell)
        self.result_table.resizeColumnsToContents()
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.progress_label.setText(
            f"Fertig: {result.created} Entwurf/Entwürfe erstellt, {result.failed} Fehler."
        )
        self.data_changed.emit()
        self.status_message.emit(f"Batch abgeschlossen: {result.created} Entwürfe.")

    def _on_failed(self, user_message: str, detail: str) -> None:
        self.progress_label.setText(f"⚠ {user_message}")
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Batch-Verarbeitung fehlgeschlagen")
        box.setText(user_message)
        box.setDetailedText(detail)
        box.exec()

    def _on_thread_done(self) -> None:
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)

    def _open_selected(self) -> None:
        row = self.result_table.currentRow()
        if row < 0:
            return
        cell = self.result_table.item(row, 0)
        listing_id = cell.data(Qt.ItemDataRole.UserRole) if cell else None
        if listing_id is None:
            QMessageBox.information(self, "Kein Entwurf", "Für diese Zeile wurde kein Entwurf erstellt.")
            return
        listing = self.ctx.listing_repo.get(int(listing_id))
        if listing:
            self.open_listing.emit(listing)
