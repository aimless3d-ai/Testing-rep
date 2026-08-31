"""Traffic-light badge for the validation result."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from vinted_tool.core.validation import ValidationResult
from vinted_tool.models.enums import QualityLevel

_COLORS = {
    QualityLevel.READY: ("#3fbf7f", "rgba(63,191,127,0.14)"),
    QualityLevel.REVIEW: ("#e6a935", "rgba(230,169,53,0.14)"),
    QualityLevel.INCOMPLETE: ("#e5544b", "rgba(229,84,75,0.14)"),
}


class QualityBadge(QLabel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.set_result(None)

    def set_result(self, result: ValidationResult | None) -> None:
        if result is None:
            self.setText("Noch nicht geprüft")
            self.setStyleSheet(
                "border-radius:10px;padding:6px 12px;border:1px solid #2c3140;color:#9aa1b2;"
            )
            self.setToolTip("")
            return
        color, background = _COLORS[result.level]
        self.setText(result.level.badge)
        self.setStyleSheet(
            f"border-radius:10px;padding:6px 12px;border:1px solid {color};"
            f"background-color:{background};color:{color};font-weight:600;"
        )
        self.setToolTip(result.summary())
