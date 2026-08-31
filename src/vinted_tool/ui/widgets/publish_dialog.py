"""Assisted publishing dialog – exports the listing and guides the upload."""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)
from PySide6.QtGui import QGuiApplication

from vinted_tool.automation.vinted_assist import PublishStep, build_publish_steps, open_upload_page
from vinted_tool.automation.vinted_export import ExportResult, export_listing
from vinted_tool.core.errors import ExportError
from vinted_tool.models.enums import ListingStatus
from vinted_tool.models.listing import Listing
from vinted_tool.utils.files import open_in_explorer

log = logging.getLogger(__name__)


class PublishDialog(QDialog):
    """Vinted has no public listing API, so the app prepares everything and the
    user finishes the upload in their own browser session."""

    def __init__(self, listing: Listing, context, parent=None) -> None:
        super().__init__(parent)
        self.listing = listing
        self.ctx = context
        self.export: ExportResult | None = None
        self.setWindowTitle("Anzeige veröffentlichen")
        self.resize(760, 620)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel(f"„{listing.title}“ vorbereiten")
        title.setObjectName("H1")
        layout.addWidget(title)

        info = QLabel(
            "Vinted bietet keine offizielle Schnittstelle zum Einstellen von Artikeln. "
            "Die App bereitet deshalb alle Daten und Bilder vor und begleitet dich Schritt "
            "für Schritt – die Veröffentlichung schließt du in deinem eigenen Browser ab. "
            "Es werden keine Zugangsdaten gespeichert und keine Schutzmechanismen umgangen."
        )
        info.setObjectName("Dim")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.export_label = QLabel("Export wird erstellt …")
        self.export_label.setWordWrap(True)
        layout.addWidget(self.export_label)

        self.steps_list = QListWidget()
        self.steps_list.currentRowChanged.connect(self._on_step_selected)
        layout.addWidget(self.steps_list, 1)

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMaximumHeight(120)
        layout.addWidget(self.detail)

        buttons = QHBoxLayout()
        self.btn_action = QPushButton("Schritt ausführen")
        self.btn_action.setObjectName("Primary")
        self.btn_action.clicked.connect(self._run_step)
        self.btn_open_folder = QPushButton("Exportordner öffnen")
        self.btn_open_folder.clicked.connect(self._open_folder)
        self.btn_open_vinted = QPushButton("Vinted öffnen")
        self.btn_open_vinted.clicked.connect(lambda: open_upload_page())
        self.btn_published = QPushButton("Als veröffentlicht markieren")
        self.btn_published.clicked.connect(self._mark_published)
        self.btn_close = QPushButton("Schließen")
        self.btn_close.clicked.connect(self.accept)
        for button in (self.btn_action, self.btn_open_folder, self.btn_open_vinted,
                       self.btn_published):
            buttons.addWidget(button)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_close)
        layout.addLayout(buttons)

        self._steps: list[PublishStep] = []
        self._prepare()

    # ------------------------------------------------------------------ setup
    def _prepare(self) -> None:
        settings = self.ctx.settings
        target = Path(settings.last_export_dir) if settings.last_export_dir else None
        try:
            self.export = export_listing(self.listing, target)
        except ExportError as exc:
            self.export_label.setText(f"⚠ {exc.user_message}")
            log.warning("Export fehlgeschlagen: %s", exc)
        else:
            self.export_label.setText(
                f"✔ Export erstellt: {self.export.folder}\n"
                f"  {len(self.export.image_paths)} Bilder, anzeige.txt, anzeige.json, anzeige.csv"
            )
            self.ctx.listing_service.mark_status(self.listing, ListingStatus.EXPORTED)

        folder = self.export.folder if self.export else None
        self._steps = build_publish_steps(self.listing, folder)
        for step in self._steps:
            item = QListWidgetItem(f"{step.number}. {step.title}")
            self.steps_list.addItem(item)
        if self._steps:
            self.steps_list.setCurrentRow(0)

    # ----------------------------------------------------------------- actions
    def _current_step(self) -> PublishStep | None:
        index = self.steps_list.currentRow()
        if 0 <= index < len(self._steps):
            return self._steps[index]
        return None

    def _on_step_selected(self, _row: int) -> None:
        step = self._current_step()
        if step is None:
            return
        text = step.detail
        if step.has_clipboard:
            text += f"\n\nInhalt:\n{step.clipboard_text}"
        self.detail.setPlainText(text)
        self.btn_action.setText(
            "Seite öffnen" if step.action == "open_url"
            else "Ordner öffnen" if step.action == "open_folder"
            else "In Zwischenablage kopieren" if step.has_clipboard
            else "Erledigt markieren"
        )

    def _run_step(self) -> None:
        step = self._current_step()
        if step is None:
            return
        if step.action == "open_url":
            open_upload_page()
        elif step.action == "open_folder":
            open_in_explorer(Path(step.payload))
        elif step.has_clipboard:
            QGuiApplication.clipboard().setText(step.clipboard_text)
        item = self.steps_list.currentItem()
        if item and not item.text().startswith("✔"):
            item.setText("✔ " + item.text())
        next_row = self.steps_list.currentRow() + 1
        if next_row < self.steps_list.count():
            self.steps_list.setCurrentRow(next_row)

    def _open_folder(self) -> None:
        if self.export and not open_in_explorer(self.export.folder):
            QMessageBox.information(
                self, "Ordner", f"Der Export liegt hier:\n{self.export.folder}"
            )

    def _mark_published(self) -> None:
        self.ctx.listing_service.mark_status(self.listing, ListingStatus.PUBLISHED)
        QMessageBox.information(
            self, "Status aktualisiert",
            "Die Anzeige ist jetzt als „Veröffentlicht“ im Verlauf gespeichert.",
        )
        self.accept()
