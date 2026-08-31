"""Drag & drop area for product photos."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import QFileDialog, QFrame, QLabel, QVBoxLayout

from vinted_tool.utils.files import collect_images

IMAGE_FILTER = "Bilder (*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.gif);;Alle Dateien (*.*)"


class DropZone(QFrame):
    """Accepts dropped files/folders and emits the contained image paths."""

    images_dropped = Signal(list)

    def __init__(
        self,
        title: str = "Bilder hierher ziehen",
        subtitle: str = "oder klicken, um Dateien auszuwählen",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(4)

        icon = QLabel("🖼")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 28px;")
        self.title_label = QLabel(title)
        self.title_label.setObjectName("H2")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("Dim")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)

    # ------------------------------------------------------------------ events
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setObjectName("DropZoneActive")
            self._refresh_style()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:  # noqa: N802
        self.setObjectName("DropZone")
        self._refresh_style()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        self.setObjectName("DropZone")
        self._refresh_style()
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        images = collect_images(paths)
        if images:
            self.images_dropped.emit(images)
            event.acceptProposedAction()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.browse()
        super().mouseReleaseEvent(event)

    # ------------------------------------------------------------------ public
    def browse(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Bilder auswählen", "", IMAGE_FILTER)
        images = collect_images([Path(f) for f in files])
        if images:
            self.images_dropped.emit(images)

    def browse_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Ordner mit Bildern auswählen")
        if folder:
            images = collect_images([Path(folder)])
            if images:
                self.images_dropped.emit(images)

    def _refresh_style(self) -> None:
        self.style().unpolish(self)
        self.style().polish(self)
