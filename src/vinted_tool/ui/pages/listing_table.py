"""Shared table page used by „Entwürfe“ and „Verlauf“."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vinted_tool.app.context import AppContext
from vinted_tool.automation.vinted_export import export_many
from vinted_tool.core.errors import ExportError
from vinted_tool.models.enums import ListingStatus
from vinted_tool.models.listing import Listing
from vinted_tool.ui.widgets.common import Card, heading

COLUMNS = ["Titel", "Marke", "Größe", "Preis", "Kategorie", "Status", "Qualität", "Geändert"]


class ListingTablePage(QWidget):
    """Searchable, filterable list of stored listings."""

    status_message = Signal(str)
    open_listing = Signal(object)
    data_changed = Signal()

    page_title = "Anzeigen"
    page_subtitle = ""
    statuses: tuple[str, ...] | None = None

    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.ctx = context
        self._listings: list[Listing] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addWidget(heading(self.page_title, self.page_subtitle))

        card = Card()
        filters = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Suchen in Titel, Beschreibung, Marke, Suchbegriffen …")
        self.search_input.textChanged.connect(self.refresh)
        filters.addWidget(self.search_input, 1)

        self.status_filter = QComboBox()
        self.status_filter.addItem("Alle Status", "")
        for status in ListingStatus:
            if self.statuses and status.value not in self.statuses:
                continue
            self.status_filter.addItem(status.label, status.value)
        self.status_filter.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.status_filter)

        self.btn_refresh = QPushButton("Aktualisieren")
        self.btn_refresh.clicked.connect(self.refresh)
        filters.addWidget(self.btn_refresh)
        card.body().addLayout(filters)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.doubleClicked.connect(self._open_selected)
        card.add(self.table)

        actions = QHBoxLayout()
        self.btn_open = QPushButton("Bearbeiten")
        self.btn_open.setObjectName("Primary")
        self.btn_open.clicked.connect(self._open_selected)
        self.btn_export = QPushButton("Auswahl exportieren")
        self.btn_export.clicked.connect(self._export_selected)
        self.btn_duplicate_check = QPushButton("Duplikate prüfen")
        self.btn_duplicate_check.clicked.connect(self._check_duplicates)
        self.btn_delete = QPushButton("Löschen")
        self.btn_delete.setObjectName("Danger")
        self.btn_delete.clicked.connect(self._delete_selected)
        for button in (self.btn_open, self.btn_export, self.btn_duplicate_check, self.btn_delete):
            actions.addWidget(button)
        actions.addStretch(1)
        self.count_label = QLabel("")
        self.count_label.setObjectName("Dim")
        actions.addWidget(self.count_label)
        card.body().addLayout(actions)
        layout.addWidget(card, 1)

    # ------------------------------------------------------------------- data
    def refresh(self) -> None:
        status = self.status_filter.currentData() or (list(self.statuses) if self.statuses else None)
        self._listings = self.ctx.listing_repo.list(
            status=status, search=self.search_input.text().strip() or None
        )
        self.table.setRowCount(len(self._listings))
        for row, listing in enumerate(self._listings):
            quality = self.ctx.listing_service.validate(listing).level.badge
            status_label = (
                ListingStatus(listing.status).label
                if listing.status in {s.value for s in ListingStatus}
                else listing.status
            )
            values = [
                listing.title or "(ohne Titel)",
                listing.brand,
                listing.size,
                f"{listing.price:.2f} {listing.currency}",
                " > ".join(listing.category_path),
                status_label,
                quality,
                listing.updated_at[:16].replace("T", " "),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, listing.id)
                self.table.setItem(row, column, item)
        self.count_label.setText(f"{len(self._listings)} Einträge")
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

    def _selected(self) -> list[Listing]:
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        return [self._listings[row] for row in rows if 0 <= row < len(self._listings)]

    # ---------------------------------------------------------------- actions
    def _open_selected(self) -> None:
        selection = self._selected()
        if not selection:
            QMessageBox.information(self, "Keine Auswahl", "Bitte zuerst eine Anzeige auswählen.")
            return
        self.open_listing.emit(selection[0])

    def _export_selected(self) -> None:
        selection = self._selected()
        if not selection:
            QMessageBox.information(self, "Keine Auswahl", "Bitte zuerst Anzeigen auswählen.")
            return
        try:
            folder = export_many(selection)
        except ExportError as exc:
            QMessageBox.warning(self, "Export fehlgeschlagen", exc.user_message)
            return
        for listing in selection:
            if listing.status == ListingStatus.DRAFT.value:
                self.ctx.listing_service.mark_status(listing, ListingStatus.EXPORTED)
        self.refresh()
        self.data_changed.emit()
        QMessageBox.information(
            self, "Export erstellt",
            f"{len(selection)} Anzeige(n) exportiert nach:\n{folder}",
        )

    def _check_duplicates(self) -> None:
        selection = self._selected() or self._listings
        if not selection:
            return
        lines: list[str] = []
        for listing in selection:
            hits = self.ctx.listing_service.check_duplicates(listing)
            if hits:
                lines.append(
                    f"• {listing.title or listing.id}: " + "; ".join(h.description for h in hits[:2])
                )
        QMessageBox.information(
            self, "Duplikatprüfung",
            "\n".join(lines) if lines else "Keine Duplikate gefunden.",
        )

    def _delete_selected(self) -> None:
        selection = self._selected()
        if not selection:
            return
        answer = QMessageBox.question(
            self, "Löschen bestätigen",
            f"{len(selection)} Anzeige(n) endgültig löschen?\n"
            "Die zugehörigen Bilddateien bleiben im Bilderordner erhalten.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        for listing in selection:
            self.ctx.listing_service.delete(listing)
        self.refresh()
        self.data_changed.emit()
        self.status_message.emit(f"{len(selection)} Anzeige(n) gelöscht.")


class DraftsPage(ListingTablePage):
    page_title = "Entwürfe"
    page_subtitle = "Alle gespeicherten Entwürfe – sie bleiben auch nach dem Neustart erhalten."
    statuses = (ListingStatus.DRAFT.value,)


class HistoryPage(ListingTablePage):
    page_title = "Verlauf"
    page_subtitle = "Jede erstellte Anzeige mit Status, Preis und Datum. Suchen und filtern möglich."
    statuses = None
