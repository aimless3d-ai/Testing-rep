"""Page „Neue Anzeige“ – thin wrapper around the listing editor."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from vinted_tool.app.context import AppContext
from vinted_tool.models.listing import Listing
from vinted_tool.ui.widgets.common import heading
from vinted_tool.ui.widgets.listing_editor import ListingEditor
from vinted_tool.ui.widgets.publish_dialog import PublishDialog


class NewListingPage(QWidget):
    status_message = Signal(str)
    data_changed = Signal()

    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.ctx = context
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addWidget(
            heading(
                "Neue Anzeige",
                "Bilder importieren, analysieren lassen, Daten prüfen und die Anzeige vorbereiten.",
            )
        )
        self.editor = ListingEditor(context)
        self.editor.status_message.connect(self.status_message)
        self.editor.listing_saved.connect(lambda _l: self.data_changed.emit())
        self.editor.publish_requested.connect(self._publish)
        layout.addWidget(self.editor, 1)

    def refresh(self) -> None:
        self.editor.reload_templates()

    def load_listing(self, listing: Listing) -> None:
        self.editor.reload_templates()
        self.editor.load_listing(listing)

    def start_new(self) -> None:
        self.editor.reload_templates()
        self.editor.reset()

    def import_paths(self, paths: list) -> None:
        self.editor.add_image_files(paths)

    def _publish(self, listing: Listing) -> None:
        dialog = PublishDialog(listing, self.ctx, self)
        dialog.exec()
        self.data_changed.emit()
        self.status_message.emit("Anzeige vorbereitet.")
