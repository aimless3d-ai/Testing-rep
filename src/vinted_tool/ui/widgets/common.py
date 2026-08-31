"""Small shared UI helpers."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class Card(QFrame):
    """Rounded surface panel used all over the app."""

    def __init__(self, title: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 14, 16, 14)
        self._layout.setSpacing(10)
        if title:
            label = QLabel(title)
            label.setObjectName("H2")
            self._layout.addWidget(label)

    def body(self) -> QVBoxLayout:
        return self._layout

    def add(self, widget: QWidget) -> QWidget:
        self._layout.addWidget(widget)
        return widget


class StatCard(QFrame):
    """Dashboard tile showing one number."""

    def __init__(self, caption: str, value: str = "0", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(2)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("H1")
        self.caption_label = QLabel(caption)
        self.caption_label.setObjectName("Dim")
        layout.addWidget(self.value_label)
        layout.addWidget(self.caption_label)

    def set_value(self, value: object) -> None:
        self.value_label.setText(str(value))


def heading(text: str, subtitle: str = "") -> QWidget:
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    title = QLabel(text)
    title.setObjectName("H1")
    layout.addWidget(title)
    if subtitle:
        sub = QLabel(subtitle)
        sub.setObjectName("Dim")
        sub.setWordWrap(True)
        layout.addWidget(sub)
    return container


def form_row(label_text: str, widget: QWidget, label_width: int = 110) -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)
    label = QLabel(label_text)
    label.setObjectName("Dim")
    label.setFixedWidth(label_width)
    label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    layout.addWidget(label)
    layout.addWidget(widget, 1)
    return container


def separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color:#2c3140;")
    return line
