"""The listing editor: images on the left, all fields on the right."""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from vinted_tool.app.context import AppContext
from vinted_tool.core.categories import all_labels, find_by_path, size_options
from vinted_tool.core.category_data import COLORS, MATERIALS
from vinted_tool.models.analysis import ImageAnalysis
from vinted_tool.models.enums import UNKNOWN, Condition, ListingStatus
from vinted_tool.models.listing import Listing, ListingImage
from vinted_tool.services.image_service import ImportOptions
from vinted_tool.ui.widgets.common import Card, form_row
from vinted_tool.ui.widgets.drop_zone import DropZone
from vinted_tool.ui.widgets.image_strip import ImageStrip
from vinted_tool.ui.widgets.quality_badge import QualityBadge
from vinted_tool.ui.workers import AnalysisWorker

log = logging.getLogger(__name__)


class ListingEditor(QWidget):
    """Edits one listing end to end. Used for new listings and for drafts."""

    status_message = Signal(str)
    listing_saved = Signal(object)
    publish_requested = Signal(object)

    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.ctx = context
        self.listing = Listing()
        self.analysis = ImageAnalysis()
        self._worker: AnalysisWorker | None = None
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_right())
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([460, 620])
        root.addWidget(splitter, 1)
        root.addWidget(self._build_footer())
        self._refresh_validation()

    # ------------------------------------------------------------------- build
    def _build_left(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(12)

        card = Card("Produktbilder")
        self.drop_zone = DropZone(
            "Bilder hierher ziehen", "oder klicken – mehrere Bilder sind möglich"
        )
        self.drop_zone.images_dropped.connect(self.add_image_files)
        card.add(self.drop_zone)

        buttons = QHBoxLayout()
        btn_files = QPushButton("Dateien wählen")
        btn_folder = QPushButton("Ordner wählen")
        btn_files.clicked.connect(self.drop_zone.browse)
        btn_folder.clicked.connect(self.drop_zone.browse_folder)
        buttons.addWidget(btn_files)
        buttons.addWidget(btn_folder)
        buttons.addStretch(1)
        card.body().addLayout(buttons)

        self.image_strip = ImageStrip()
        self.image_strip.changed.connect(self._on_images_changed)
        card.add(self.image_strip)
        layout.addWidget(card, 1)

        analysis_card = Card("KI-Analyse")
        hint_row = QHBoxLayout()
        self.hint_input = QLineEdit()
        self.hint_input.setPlaceholderText(
            "Optionale eigene Angabe, z. B. „Größe M, Etikett fehlt“"
        )
        hint_row.addWidget(self.hint_input)
        analysis_card.body().addLayout(hint_row)

        actions = QHBoxLayout()
        self.btn_analyze = QPushButton("Bilder analysieren")
        self.btn_analyze.setObjectName("Primary")
        self.btn_analyze.clicked.connect(lambda: self.run_analysis(force=False))
        self.btn_reanalyze = QPushButton("Erneut (ohne Cache)")
        self.btn_reanalyze.clicked.connect(lambda: self.run_analysis(force=True))
        self.btn_offline = QPushButton("Ohne KI ausfüllen")
        self.btn_offline.setToolTip(
            "Analysiert nur lokal: Farben aus den Bildern, Hinweise aus den Dateinamen."
        )
        self.btn_offline.clicked.connect(lambda: self.run_analysis(offline=True))
        for button in (self.btn_analyze, self.btn_reanalyze, self.btn_offline):
            actions.addWidget(button)
        actions.addStretch(1)
        analysis_card.body().addLayout(actions)

        self.analysis_status = QLabel("Noch keine Analyse durchgeführt.")
        self.analysis_status.setObjectName("Dim")
        self.analysis_status.setWordWrap(True)
        analysis_card.add(self.analysis_status)

        self.missing_label = QLabel("")
        self.missing_label.setWordWrap(True)
        self.missing_label.setStyleSheet("color:#e6a935;")
        self.missing_label.setVisible(False)
        analysis_card.add(self.missing_label)

        self.duplicate_label = QLabel("")
        self.duplicate_label.setWordWrap(True)
        self.duplicate_label.setStyleSheet("color:#e5544b;")
        self.duplicate_label.setVisible(False)
        analysis_card.add(self.duplicate_label)

        layout.addWidget(analysis_card)
        return panel

    def _build_right(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 0, 0, 0)
        layout.setSpacing(12)

        details = Card("Anzeigendaten")
        self.title_input = QLineEdit()
        self.title_input.setMaxLength(100)
        self.title_input.setPlaceholderText("z. B. Nike Hoodie Schwarz Gr. M")
        self.title_input.textChanged.connect(self._on_field_changed)
        details.body().addWidget(form_row("Titel", self.title_input))

        self.description_input = QTextEdit()
        self.description_input.setMinimumHeight(150)
        self.description_input.setPlaceholderText(
            "Beschreibung – wird aus der gewählten Vorlage erzeugt und kann frei bearbeitet werden."
        )
        self.description_input.textChanged.connect(self._on_field_changed)
        details.body().addWidget(form_row("Beschreibung", self.description_input))

        template_row = QHBoxLayout()
        self.template_combo = QComboBox()
        self.btn_apply_template = QPushButton("Vorlage anwenden")
        self.btn_apply_template.clicked.connect(self.apply_template)
        template_row.addWidget(self.template_combo, 1)
        template_row.addWidget(self.btn_apply_template)
        details.body().addWidget(form_row("Vorlage", self._wrap(template_row)))

        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        details.body().addWidget(form_row("Kategorie", self.category_combo))

        self.brand_input = QLineEdit()
        self.brand_input.setPlaceholderText("Marke – leer lassen, wenn nicht erkennbar")
        self.brand_input.textChanged.connect(self._on_field_changed)
        details.body().addWidget(form_row("Marke", self.brand_input))

        self.size_combo = QComboBox()
        self.size_combo.setEditable(True)
        self.size_combo.currentTextChanged.connect(self._on_field_changed)
        details.body().addWidget(form_row("Größe", self.size_combo))

        self.color_combo = QComboBox()
        self.color_combo.setEditable(True)
        self.color_combo.addItems([""] + COLORS)
        self.color_combo.currentTextChanged.connect(self._on_field_changed)
        details.body().addWidget(form_row("Farbe", self.color_combo))

        self.condition_combo = QComboBox()
        self.condition_combo.addItems([""] + Condition.values())
        self.condition_combo.currentTextChanged.connect(self._on_condition_changed)
        details.body().addWidget(form_row("Zustand", self.condition_combo))

        self.material_combo = QComboBox()
        self.material_combo.setEditable(True)
        self.material_combo.addItems([""] + MATERIALS)
        self.material_combo.currentTextChanged.connect(self._on_field_changed)
        details.body().addWidget(form_row("Material", self.material_combo))

        self.keywords_input = QLineEdit()
        self.keywords_input.setPlaceholderText("Suchbegriffe, durch Komma getrennt")
        self.keywords_input.textChanged.connect(self._on_field_changed)
        details.body().addWidget(form_row("Suchbegriffe", self.keywords_input))
        layout.addWidget(details)

        price_card = Card("Preis")
        price_row = QHBoxLayout()
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0.0, 100000.0)
        self.price_input.setDecimals(2)
        self.price_input.setSingleStep(0.5)
        self.price_input.setSuffix(" €")
        self.price_input.valueChanged.connect(self._on_field_changed)
        price_row.addWidget(self.price_input)
        self.btn_recalc = QPushButton("Neu berechnen")
        self.btn_recalc.clicked.connect(self.recalculate_price)
        price_row.addWidget(self.btn_recalc)
        price_row.addStretch(1)
        price_card.body().addWidget(form_row("Preis", self._wrap(price_row)))

        suggestions = QHBoxLayout()
        self.btn_price_quick = QPushButton("Schnellverkauf –")
        self.btn_price_reco = QPushButton("Empfohlen –")
        self.btn_price_reco.setObjectName("Primary")
        self.btn_price_high = QPushButton("Höher –")
        self.btn_price_quick.clicked.connect(lambda: self._apply_price("quick"))
        self.btn_price_reco.clicked.connect(lambda: self._apply_price("recommended"))
        self.btn_price_high.clicked.connect(lambda: self._apply_price("high"))
        for button in (self.btn_price_quick, self.btn_price_reco, self.btn_price_high):
            suggestions.addWidget(button)
        price_card.body().addLayout(suggestions)

        self.price_rationale = QLabel("")
        self.price_rationale.setObjectName("Dim")
        self.price_rationale.setWordWrap(True)
        price_card.add(self.price_rationale)

        research_row = QHBoxLayout()
        self.btn_research = QPushButton("Ähnliche Artikel auf Vinted ansehen")
        self.btn_research.setToolTip(
            "Öffnet eine normale Vinted-Suche im Browser, damit du Preise selbst vergleichen kannst."
        )
        self.btn_research.clicked.connect(self._open_research)
        research_row.addWidget(self.btn_research)
        research_row.addStretch(1)
        price_card.body().addLayout(research_row)
        layout.addWidget(price_card)
        layout.addStretch(1)

        scroll.setWidget(panel)
        return scroll

    def _build_footer(self) -> QWidget:
        footer = QWidget()
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.quality_badge = QualityBadge()
        layout.addWidget(self.quality_badge)
        self.validation_label = QLabel("")
        self.validation_label.setObjectName("Dim")
        self.validation_label.setWordWrap(True)
        layout.addWidget(self.validation_label, 1)

        self.btn_new = QPushButton("Zurücksetzen")
        self.btn_new.clicked.connect(self.reset)
        self.btn_draft = QPushButton("Als Entwurf speichern")
        self.btn_draft.clicked.connect(self.save_draft)
        self.btn_create = QPushButton("Anzeige erstellen")
        self.btn_create.setObjectName("Primary")
        self.btn_create.clicked.connect(self.create_listing)
        for button in (self.btn_new, self.btn_draft, self.btn_create):
            layout.addWidget(button)
        return footer

    @staticmethod
    def _wrap(layout) -> QWidget:
        widget = QWidget()
        widget.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        return widget

    # -------------------------------------------------------------- data flow
    def reload_templates(self) -> None:
        current = self.template_combo.currentText()
        self.template_combo.clear()
        for template in self.ctx.template_repo.list():
            self.template_combo.addItem(template.name, template.body)
        index = self.template_combo.findText(current)
        if index >= 0:
            self.template_combo.setCurrentIndex(index)

    def load_listing(self, listing: Listing) -> None:
        self._loading = True
        try:
            self.listing = listing
            self.analysis = ImageAnalysis.from_dict(listing.analysis or {})
            self.image_strip.set_images(listing.images)
            self._fill_categories(listing.category_candidates)
            self.title_input.setText(listing.title)
            self.description_input.setPlainText(listing.description)
            self.category_combo.setCurrentText(" > ".join(listing.category_path))
            self.brand_input.setText(listing.brand)
            self._fill_sizes(listing.category_path)
            self.size_combo.setCurrentText(listing.size)
            self.color_combo.setCurrentText(listing.color)
            self.condition_combo.setCurrentText(listing.condition)
            self.material_combo.setCurrentText(listing.material)
            self.keywords_input.setText(", ".join(listing.keywords))
            self.price_input.setValue(float(listing.price or 0))
            self._update_price_buttons(listing.price_suggestion)
            self._update_analysis_labels()
        finally:
            self._loading = False
        self._refresh_validation()

    def reset(self) -> None:
        self.load_listing(Listing())
        self.hint_input.clear()
        self.analysis_status.setText("Noch keine Analyse durchgeführt.")
        self.duplicate_label.setVisible(False)
        self.status_message.emit("Neue Anzeige gestartet.")

    def collect(self) -> Listing:
        """Read every widget back into the listing object."""
        listing = self.listing
        listing.images = self.image_strip.images
        listing.title = self.title_input.text().strip()
        listing.description = self.description_input.toPlainText().strip()
        label = self.category_combo.currentText().strip()
        entry = find_by_path(label)
        listing.category_path = list(entry.path) if entry else (
            [p.strip() for p in label.split(">") if p.strip()] if label else []
        )
        listing.brand = self.brand_input.text().strip()
        listing.size = self.size_combo.currentText().strip()
        listing.color = self.color_combo.currentText().strip()
        listing.condition = self.condition_combo.currentText().strip()
        listing.material = self.material_combo.currentText().strip()
        listing.keywords = [
            k.strip() for k in self.keywords_input.text().split(",") if k.strip()
        ]
        listing.price = round(float(self.price_input.value()), 2)
        listing.analysis = self.analysis.to_dict()
        listing.currency = self.ctx.settings.currency
        return listing

    # -------------------------------------------------------------- image flow
    def add_image_files(self, paths: list[Path]) -> None:
        settings = self.ctx.settings
        options = ImportOptions(
            max_dimension=settings.max_image_dimension,
            name_hint=self.title_input.text() or Path(paths[0]).stem,
        )
        images, errors = self.ctx.image_service.import_many(list(paths), options)
        for image in images:
            image.is_primary = False
        self.image_strip.add_images(images)
        if errors:
            QMessageBox.warning(
                self, "Nicht alle Bilder konnten importiert werden", "\n".join(errors)
            )
        self.status_message.emit(f"{len(images)} Bild(er) importiert.")
        self._check_duplicates()
        if images and settings.auto_analyze_on_import and not self.title_input.text().strip():
            self.run_analysis(force=False)

    def _on_images_changed(self) -> None:
        self.listing.images = self.image_strip.images
        self._refresh_validation()

    def _check_duplicates(self) -> None:
        listing = self.collect()
        hits = self.ctx.listing_service.check_duplicates(listing)
        if hits:
            text = "⚠ Mögliches Duplikat: " + "; ".join(h.description for h in hits[:3])
            self.duplicate_label.setText(text)
            self.duplicate_label.setVisible(True)
        else:
            self.duplicate_label.setVisible(False)

    # ----------------------------------------------------------------- analysis
    def run_analysis(self, *, force: bool = False, offline: bool = False) -> None:
        images = self.image_strip.images
        if not images:
            QMessageBox.information(
                self, "Keine Bilder", "Bitte zuerst mindestens ein Produktbild importieren."
            )
            return
        if self._worker and self._worker.isRunning():
            self.status_message.emit("Es läuft bereits eine Analyse.")
            return

        self._set_analysis_running(True)
        self.analysis_status.setText("Analyse läuft …")
        self._worker = AnalysisWorker(
            self.ctx.analysis_service,
            [i.path for i in images],
            hint=self.hint_input.text().strip(),
            force_refresh=force,
            offline=offline,
            parent=self,
        )
        self._worker.finished_ok.connect(self._on_analysis_done)
        self._worker.failed.connect(self._on_analysis_failed)
        self._worker.finished.connect(lambda: self._set_analysis_running(False))
        self._worker.start()

    def _set_analysis_running(self, running: bool) -> None:
        for button in (self.btn_analyze, self.btn_reanalyze, self.btn_offline):
            button.setEnabled(not running)

    def _on_analysis_done(self, outcome) -> None:
        self.analysis = outcome.analysis
        template_body = self.template_combo.currentData()
        listing = self.ctx.listing_service.build_listing(
            outcome.analysis, self.image_strip.images,
            template_body=template_body, existing=self.listing,
        )
        self.load_listing(listing)
        source = outcome.analysis.source
        cached = " (aus dem Cache – keine Kosten)" if outcome.from_cache else ""
        tokens = (
            f" · {outcome.analysis.tokens_used} Tokens" if outcome.analysis.tokens_used else ""
        )
        self.analysis_status.setText(
            f"Analyse abgeschlossen über „{source}“{cached}{tokens}."
            + (f" Hinweis: {outcome.analysis.notes}" if outcome.analysis.notes else "")
        )
        self.status_message.emit("Analyse abgeschlossen.")
        self._check_duplicates()

    def _on_analysis_failed(self, user_message: str, detail: str) -> None:
        log.warning("Analyse fehlgeschlagen: %s", detail)
        self.analysis_status.setText(f"⚠ {user_message}")
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("KI-Analyse konnte nicht durchgeführt werden")
        box.setText(user_message)
        box.setDetailedText(detail)
        retry = box.addButton("Erneut versuchen", QMessageBox.ButtonRole.AcceptRole)
        offline = box.addButton("Ohne KI ausfüllen", QMessageBox.ButtonRole.ActionRole)
        box.addButton("Manuell ausfüllen", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is retry:
            self.run_analysis(force=True)
        elif box.clickedButton() is offline:
            self.run_analysis(offline=True)

    def _update_analysis_labels(self) -> None:
        missing = self.analysis.missing_fields()
        if missing and (self.analysis.source or self.analysis.product_type):
            self.missing_label.setText(f"{UNKNOWN} → {', '.join(missing)}")
            self.missing_label.setVisible(True)
        else:
            self.missing_label.setVisible(False)

    # -------------------------------------------------------------- field logic
    def _fill_categories(self, candidates: list[str]) -> None:
        current = self.category_combo.currentText()
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        seen: list[str] = []
        for label in list(candidates) + all_labels():
            if label and label not in seen:
                seen.append(label)
                self.category_combo.addItem(label)
        self.category_combo.setCurrentText(current)
        self.category_combo.blockSignals(False)

    def _fill_sizes(self, category_path: list[str]) -> None:
        entry = find_by_path(category_path) if category_path else None
        current = self.size_combo.currentText()
        self.size_combo.blockSignals(True)
        self.size_combo.clear()
        self.size_combo.addItems([""] + size_options(entry))
        self.size_combo.setCurrentText(current)
        self.size_combo.blockSignals(False)

    def _on_category_changed(self, text: str) -> None:
        if self._loading:
            return
        entry = find_by_path(text)
        self._fill_sizes(list(entry.path) if entry else [])
        self._on_field_changed()

    def _on_condition_changed(self, _text: str) -> None:
        if self._loading:
            return
        self.recalculate_price(apply_value=False)
        self._on_field_changed()

    def _on_field_changed(self) -> None:
        if self._loading:
            return
        self._refresh_validation()

    def recalculate_price(self, *, apply_value: bool = True) -> None:
        listing = self.collect()
        suggestion = self.ctx.listing_service.suggest_price(listing, self.analysis)
        listing.price_suggestion = suggestion
        self._update_price_buttons(suggestion)
        if apply_value:
            self.price_input.setValue(suggestion.recommended)
            self.status_message.emit("Preisvorschlag aktualisiert.")

    def _update_price_buttons(self, suggestion) -> None:
        currency = suggestion.currency or "EUR"
        symbol = "€" if currency == "EUR" else currency
        self.btn_price_quick.setText(f"Schnellverkauf {suggestion.quick:.2f} {symbol}")
        self.btn_price_reco.setText(f"Empfohlen {suggestion.recommended:.2f} {symbol}")
        self.btn_price_high.setText(f"Höher {suggestion.high:.2f} {symbol}")
        self.price_rationale.setText(suggestion.rationale)
        self.listing.price_suggestion = suggestion

    def _apply_price(self, which: str) -> None:
        suggestion = self.listing.price_suggestion
        value = {"quick": suggestion.quick, "recommended": suggestion.recommended,
                 "high": suggestion.high}.get(which, 0.0)
        if value:
            self.price_input.setValue(value)

    def apply_template(self) -> None:
        body = self.template_combo.currentData()
        if not body:
            return
        listing = self.collect()
        self.description_input.setPlainText(
            self.ctx.listing_service.render_description(listing, self.analysis, body)
        )
        self.status_message.emit(f"Vorlage „{self.template_combo.currentText()}“ angewendet.")

    def _open_research(self) -> None:
        from vinted_tool.automation.vinted_assist import open_price_research

        listing = self.collect()
        if not open_price_research(listing):
            QMessageBox.information(
                self, "Keine Suche möglich",
                "Bitte zuerst einen Titel oder eine Marke eintragen.",
            )

    # ------------------------------------------------------------- validation
    def _refresh_validation(self):
        listing = self.collect()
        result = self.ctx.listing_service.validate(listing)
        self.quality_badge.set_result(result)
        issues = result.blocking or result.warnings
        self.validation_label.setText(
            "Alle Pflichtangaben vorhanden."
            if not issues
            else " · ".join(i.message for i in issues[:3])
        )
        self.btn_create.setEnabled(result.is_publishable)
        return result

    # ----------------------------------------------------------------- actions
    def save_draft(self) -> Listing:
        listing = self.collect()
        saved = self.ctx.listing_service.save_as_draft(listing)
        self.listing = saved
        self.listing_saved.emit(saved)
        self.status_message.emit(f"Entwurf gespeichert (#{saved.id}).")
        return saved

    def create_listing(self) -> None:
        listing = self.collect()
        result = self.ctx.listing_service.validate(listing)
        if not result.is_publishable:
            QMessageBox.warning(
                self, "Anzeige unvollständig",
                "Folgende Angaben fehlen noch:\n\n" + result.summary(),
            )
            return
        if result.warnings:
            answer = QMessageBox.question(
                self, "Überprüfung empfohlen",
                "Es gibt Hinweise zur Anzeige:\n\n" + result.summary()
                + "\n\nTrotzdem fortfahren?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.ctx.image_service.rename_for_listing(listing.images, listing.title)
        listing.status = ListingStatus.READY.value
        saved = self.ctx.listing_service.save(listing)
        self.listing = saved
        self.listing_saved.emit(saved)
        self.publish_requested.emit(saved)
