"""Dashboard with quick actions, counters and the latest listings."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from vinted_tool.app.context import AppContext
from vinted_tool.models.enums import ListingStatus
from vinted_tool.ui.widgets.common import Card, StatCard, heading
from vinted_tool.ui.widgets.drop_zone import DropZone


class DashboardPage(QWidget):
    navigate = Signal(str)
    images_imported = Signal(list)
    open_listing = Signal(object)

    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.ctx = context

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addWidget(
            heading("Dashboard", "Schnellzugriff auf alles, was du regelmäßig brauchst.")
        )

        stats = QHBoxLayout()
        stats.setSpacing(12)
        self.stat_total = StatCard("Anzeigen gesamt")
        self.stat_drafts = StatCard("Entwürfe")
        self.stat_ready = StatCard("Bereit")
        self.stat_published = StatCard("Veröffentlicht")
        for card in (self.stat_total, self.stat_drafts, self.stat_ready, self.stat_published):
            stats.addWidget(card)
        layout.addLayout(stats)

        actions_card = Card("Schnellstart")
        grid = QGridLayout()
        grid.setSpacing(10)
        buttons = [
            ("➕  Neue Anzeige erstellen", "new", True),
            ("🖼  Bilder importieren", "import", False),
            ("📦  Batch-Verarbeitung", "batch", False),
            ("📝  Entwürfe öffnen", "drafts", False),
        ]
        for index, (label, target, primary) in enumerate(buttons):
            button = QPushButton(label)
            button.setMinimumHeight(46)
            if primary:
                button.setObjectName("Primary")
            button.clicked.connect(lambda _=False, t=target: self._on_action(t))
            grid.addWidget(button, index // 2, index % 2)
        actions_card.body().addLayout(grid)
        layout.addWidget(actions_card)

        drop_card = Card("Direkt loslegen")
        self.drop_zone = DropZone(
            "Produktbilder hierher ziehen", "Die Bilder landen direkt in einer neuen Anzeige"
        )
        self.drop_zone.images_dropped.connect(self.images_imported)
        drop_card.add(self.drop_zone)
        layout.addWidget(drop_card)

        recent_card = Card("Letzte Anzeigen")
        self.recent_list = QListWidget()
        self.recent_list.itemDoubleClicked.connect(self._open_selected)
        recent_card.add(self.recent_list)
        open_row = QHBoxLayout()
        btn_open = QPushButton("Ausgewählte öffnen")
        btn_open.clicked.connect(lambda: self._open_selected(self.recent_list.currentItem()))
        open_row.addWidget(btn_open)
        open_row.addStretch(1)
        recent_card.body().addLayout(open_row)
        layout.addWidget(recent_card, 1)

    def _on_action(self, target: str) -> None:
        if target == "import":
            self.drop_zone.browse()
        else:
            self.navigate.emit(target)

    def refresh(self) -> None:
        counts = self.ctx.listing_repo.counts_by_status()
        self.stat_total.set_value(sum(counts.values()))
        self.stat_drafts.set_value(counts.get(ListingStatus.DRAFT.value, 0))
        self.stat_ready.set_value(
            counts.get(ListingStatus.READY.value, 0) + counts.get(ListingStatus.EXPORTED.value, 0)
        )
        self.stat_published.set_value(counts.get(ListingStatus.PUBLISHED.value, 0))

        self.recent_list.clear()
        for listing in self.ctx.listing_repo.list(limit=12):
            status = ListingStatus(listing.status).label if listing.status in {
                s.value for s in ListingStatus
            } else listing.status
            text = (
                f"{listing.title or '(ohne Titel)'} — {listing.price:.2f} {listing.currency}"
                f"  ·  {status}  ·  {listing.updated_at[:16].replace('T', ' ')}"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, listing.id)
            self.recent_list.addItem(item)

    def _open_selected(self, item: QListWidgetItem | None) -> None:
        if item is None:
            return
        listing_id = item.data(Qt.ItemDataRole.UserRole)
        listing = self.ctx.listing_repo.get(int(listing_id))
        if listing:
            self.open_listing.emit(listing)
