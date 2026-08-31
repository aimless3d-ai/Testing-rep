"""Manage description templates with ``{{variable}}`` placeholders."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from vinted_tool.app.context import AppContext
from vinted_tool.core import templates as template_engine
from vinted_tool.models.template_model import Template
from vinted_tool.ui.widgets.common import Card, heading

PREVIEW_VALUES = {
    "brand": "Nike",
    "product": "Hoodie",
    "title": "Nike Hoodie Schwarz Gr. M",
    "size": "M",
    "condition": "Sehr gut",
    "color": "Schwarz",
    "material": "Baumwolle",
    "category": "Damen > Kleidung > Pullover & Sweatshirts > Hoodies",
    "price": "24.50",
    "currency": "EUR",
    "keywords": "nike, hoodie, schwarz",
    "features": "Kängurutasche und Kapuze mit Kordel",
    "damages": "leichtes Pilling an den Ärmeln",
    "shipping": "Versand als versichertes Paket.",
}


class TemplatesPage(QWidget):
    status_message = Signal(str)
    data_changed = Signal()

    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.ctx = context
        self._current: Template | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addWidget(
            heading(
                "Vorlagen",
                "Beschreibungsvorlagen mit Variablen wie {{brand}}, {{size}} oder {{condition}}.",
            )
        )

        splitter = QSplitter(Qt.Orientation.Horizontal)

        list_card = Card("Vorlagen")
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._on_selected)
        list_card.add(self.list)
        buttons = QHBoxLayout()
        btn_new = QPushButton("Neu")
        btn_new.clicked.connect(self.create_template)
        btn_default = QPushButton("Als Standard")
        btn_default.clicked.connect(self.make_default)
        btn_delete = QPushButton("Löschen")
        btn_delete.setObjectName("Danger")
        btn_delete.clicked.connect(self.delete_template)
        for button in (btn_new, btn_default, btn_delete):
            buttons.addWidget(button)
        list_card.body().addLayout(buttons)
        splitter.addWidget(list_card)

        editor_card = Card("Vorlage bearbeiten")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name der Vorlage")
        editor_card.add(self.name_input)
        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText(
            "Privatverkauf. {{brand}} {{product}} in Größe {{size}}. Zustand: {{condition}}."
        )
        self.body_input.textChanged.connect(self.update_preview)
        editor_card.add(self.body_input)

        variables = QLabel(
            "Verfügbare Variablen: "
            + ", ".join(f"{{{{{name}}}}}" for name in template_engine.KNOWN_VARIABLES)
            + "\nFallback: {{brand|Marke unbekannt}} · Block: {{#size}}Größe {{size}}{{/size}}"
        )
        variables.setObjectName("Dim")
        variables.setWordWrap(True)
        editor_card.add(variables)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMaximumHeight(150)
        editor_card.add(QLabel("Vorschau mit Beispieldaten:"))
        editor_card.add(self.preview)

        save_row = QHBoxLayout()
        btn_save = QPushButton("Speichern")
        btn_save.setObjectName("Primary")
        btn_save.clicked.connect(self.save_template)
        save_row.addWidget(btn_save)
        save_row.addStretch(1)
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color:#e6a935;")
        save_row.addWidget(self.warning_label)
        editor_card.body().addLayout(save_row)
        splitter.addWidget(editor_card)
        splitter.setSizes([280, 640])
        layout.addWidget(splitter, 1)

    # -------------------------------------------------------------------- data
    def refresh(self) -> None:
        selected = self.list.currentRow()
        self.list.clear()
        for template in self.ctx.template_repo.list():
            label = f"★ {template.name}" if template.is_default else template.name
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, template.id)
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(min(max(selected, 0), self.list.count() - 1))

    def _templates(self) -> list[Template]:
        return self.ctx.template_repo.list()

    def _on_selected(self, row: int) -> None:
        templates = self._templates()
        if 0 <= row < len(templates):
            self._current = templates[row]
            self.name_input.setText(self._current.name)
            self.body_input.setPlainText(self._current.body)
            self.update_preview()

    def update_preview(self) -> None:
        body = self.body_input.toPlainText()
        self.preview.setPlainText(template_engine.render(body, PREVIEW_VALUES))
        unknown = template_engine.unknown_variables(body)
        self.warning_label.setText(
            f"Unbekannte Variablen: {', '.join(unknown)}" if unknown else ""
        )

    # ----------------------------------------------------------------- actions
    def create_template(self) -> None:
        name, ok = QInputDialog.getText(self, "Neue Vorlage", "Name:")
        if not ok or not name.strip():
            return
        template = Template(name=name.strip(), body="{{brand}} {{product}}\nZustand: {{condition}}.")
        try:
            self.ctx.template_repo.save(template)
        except Exception as exc:  # noqa: BLE001 - unique name constraint
            QMessageBox.warning(self, "Nicht gespeichert", f"Vorlage konnte nicht angelegt werden: {exc}")
            return
        self.refresh()
        self.data_changed.emit()
        self.status_message.emit(f"Vorlage „{template.name}“ angelegt.")

    def save_template(self) -> None:
        if self._current is None:
            self.create_template()
            return
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Name fehlt", "Bitte einen Namen für die Vorlage eingeben.")
            return
        self._current.name = name
        self._current.body = self.body_input.toPlainText()
        try:
            self.ctx.template_repo.save(self._current)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Nicht gespeichert", f"Speichern fehlgeschlagen: {exc}")
            return
        self.refresh()
        self.data_changed.emit()
        self.status_message.emit(f"Vorlage „{name}“ gespeichert.")

    def make_default(self) -> None:
        if self._current is None:
            return
        self._current.is_default = True
        self.ctx.template_repo.save(self._current)
        self.refresh()
        self.data_changed.emit()
        self.status_message.emit(f"„{self._current.name}“ ist jetzt die Standardvorlage.")

    def delete_template(self) -> None:
        if self._current is None or self._current.id is None:
            return
        if len(self._templates()) <= 1:
            QMessageBox.information(
                self, "Letzte Vorlage", "Mindestens eine Vorlage muss vorhanden bleiben."
            )
            return
        answer = QMessageBox.question(
            self, "Löschen", f"Vorlage „{self._current.name}“ löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.ctx.template_repo.delete(self._current.id)
        self._current = None
        self.refresh()
        self.data_changed.emit()
