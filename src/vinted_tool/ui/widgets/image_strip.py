"""Thumbnail list with sorting, deleting and primary-image selection."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from vinted_tool.models.listing import ListingImage
from vinted_tool.services.image_service import ImageService

THUMB = QSize(112, 112)


class ImageStrip(QWidget):
    """Shows the images of one listing and lets the user curate them."""

    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._images: list[ListingImage] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.list = QListWidget()
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setIconSize(THUMB)
        self.list.setGridSize(QSize(THUMB.width() + 26, THUMB.height() + 40))
        self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list.setMovement(QListWidget.Movement.Static)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setWordWrap(True)
        self.list.setMinimumHeight(170)
        layout.addWidget(self.list)

        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        self.btn_left = QPushButton("◀ Nach vorne")
        self.btn_right = QPushButton("Nach hinten ▶")
        self.btn_primary = QPushButton("★ Als Hauptbild")
        self.btn_delete = QPushButton("Entfernen")
        self.btn_delete.setObjectName("Danger")
        for button in (self.btn_left, self.btn_right, self.btn_primary, self.btn_delete):
            buttons.addWidget(button)
        buttons.addStretch(1)
        self.count_label = QLabel("Keine Bilder")
        self.count_label.setObjectName("Dim")
        buttons.addWidget(self.count_label)
        layout.addLayout(buttons)

        self.btn_left.clicked.connect(lambda: self._move(-1))
        self.btn_right.clicked.connect(lambda: self._move(1))
        self.btn_primary.clicked.connect(self._make_primary)
        self.btn_delete.clicked.connect(self._delete)
        self.list.itemSelectionChanged.connect(self._update_buttons)
        self._update_buttons()

    # ------------------------------------------------------------------ public
    @property
    def images(self) -> list[ListingImage]:
        return self._images

    def set_images(self, images: list[ListingImage]) -> None:
        self._images = ImageService.renumber(list(images))
        self.refresh()

    def add_images(self, images: list[ListingImage]) -> None:
        self._images.extend(images)
        ImageService.renumber(self._images)
        self.refresh()
        self.changed.emit()

    def clear(self) -> None:
        self._images = []
        self.refresh()

    def refresh(self) -> None:
        selected = self.list.currentRow()
        self.list.clear()
        for position, image in enumerate(self._images):
            source = image.thumbnail_path or image.path
            pixmap = QPixmap(source)
            if pixmap.isNull():
                pixmap = QPixmap(THUMB)
                pixmap.fill(Qt.GlobalColor.darkGray)
            item = QListWidgetItem(QIcon(pixmap), self._caption(position, image))
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
            item.setToolTip(f"{image.original_name or Path(image.path).name}\n"
                            f"{image.width}×{image.height} px")
            self.list.addItem(item)
        if self._images:
            self.list.setCurrentRow(min(max(selected, 0), len(self._images) - 1))
        count = len(self._images)
        self.count_label.setText(
            "Keine Bilder" if not count else f"{count} Bild{'er' if count != 1 else ''}"
        )
        self._update_buttons()

    # ----------------------------------------------------------------- helpers
    @staticmethod
    def _caption(position: int, image: ListingImage) -> str:
        star = "★ " if image.is_primary else ""
        return f"{star}{position + 1}"

    def _current(self) -> int:
        return self.list.currentRow()

    def _move(self, offset: int) -> None:
        index = self._current()
        if index < 0:
            return
        new_index = ImageService.move(self._images, index, offset)
        self.refresh()
        self.list.setCurrentRow(new_index)
        self.changed.emit()

    def _make_primary(self) -> None:
        index = self._current()
        if index < 0:
            return
        ImageService.set_primary(self._images, index)
        self.refresh()
        self.changed.emit()

    def _delete(self) -> None:
        index = self._current()
        if index < 0:
            return
        self._images.pop(index)
        ImageService.renumber(self._images)
        self.refresh()
        self.changed.emit()

    def _update_buttons(self) -> None:
        has_selection = self._current() >= 0 and bool(self._images)
        for button in (self.btn_left, self.btn_right, self.btn_primary, self.btn_delete):
            button.setEnabled(has_selection)
