"""Settings: AI provider, defaults, price strategy, storage."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from vinted_tool.app.context import AppContext
from vinted_tool.app.paths import data_dir, db_path, exports_dir, images_dir, logs_dir
from vinted_tool.core.config import DEFAULT_BASE_URLS, DEFAULT_MODELS, ENV_KEYS
from vinted_tool.core.secrets import mask
from vinted_tool.models.enums import Condition, PriceStrategy, ProviderKind
from vinted_tool.ui.widgets.common import Card, form_row, heading
from vinted_tool.ui.workers import ConnectionTestWorker
from vinted_tool.utils.files import open_in_explorer

MODEL_SUGGESTIONS = {
    ProviderKind.OPENROUTER: [
        "google/gemini-2.5-flash",
        "openai/gpt-4.1-mini",
        "anthropic/claude-sonnet-4.5",
        "qwen/qwen2.5-vl-72b-instruct",
    ],
    ProviderKind.OPENAI: ["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini"],
    ProviderKind.ANTHROPIC: ["claude-sonnet-4-5", "claude-opus-4-1", "claude-haiku-4-5"],
    ProviderKind.LOCAL: ["llava", "llama3.2-vision", "qwen2.5vl"],
    ProviderKind.OFFLINE: ["heuristik"],
}

ROUNDING_OPTIONS = [
    ("0.50", "Auf 0,50 € runden"),
    ("1.00", "Auf volle Euro runden"),
    ("psychological", "Psychologisch (z. B. 19,99 €)"),
    ("off", "Nicht runden"),
]


class SettingsPage(QWidget):
    status_message = Signal(str)
    settings_changed = Signal()

    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.ctx = context
        self._worker: ConnectionTestWorker | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(14)
        outer.addWidget(
            heading("Einstellungen", "KI-Anbieter, Standardwerte und Speicherorte.")
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(14)

        # ------------------------------------------------------------ provider
        ai_card = Card("KI-Anbieter")
        self.provider_combo = QComboBox()
        for kind in ProviderKind:
            self.provider_combo.addItem(kind.label, kind.value)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        ai_card.body().addWidget(form_row("Provider", self.provider_combo, 130))

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("API-Key eingeben")
        key_row = QHBoxLayout()
        key_row.addWidget(self.api_key_input, 1)
        self.btn_show_key = QPushButton("Anzeigen")
        self.btn_show_key.setCheckable(True)
        self.btn_show_key.toggled.connect(self._toggle_key_visibility)
        key_row.addWidget(self.btn_show_key)
        ai_card.body().addWidget(form_row("API-Key", self._wrap(key_row), 130))

        self.key_hint = QLabel("")
        self.key_hint.setObjectName("Dim")
        self.key_hint.setWordWrap(True)
        ai_card.add(self.key_hint)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        ai_card.body().addWidget(form_row("Modell", self.model_combo, 130))

        self.base_url_input = QLineEdit()
        ai_card.body().addWidget(form_row("API-URL", self.base_url_input, 130))

        test_row = QHBoxLayout()
        self.btn_test = QPushButton("API-Verbindung testen")
        self.btn_test.setObjectName("Primary")
        self.btn_test.clicked.connect(self.test_connection)
        test_row.addWidget(self.btn_test)
        self.test_result = QLabel("")
        self.test_result.setWordWrap(True)
        test_row.addWidget(self.test_result, 1)
        ai_card.body().addLayout(test_row)

        self.cache_check = QCheckBox("Ergebnisse zwischenspeichern (spart Kosten)")
        ai_card.add(self.cache_check)
        self.auto_analyze_check = QCheckBox("Nach dem Import automatisch analysieren")
        ai_card.add(self.auto_analyze_check)

        limits = QHBoxLayout()
        self.image_count_spin = QSpinBox()
        self.image_count_spin.setRange(1, 8)
        self.image_count_spin.setToolTip("Wie viele Bilder je Produkt an die KI gesendet werden.")
        limits.addWidget(QLabel("Bilder an die KI:"))
        limits.addWidget(self.image_count_spin)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 600)
        self.timeout_spin.setSuffix(" s")
        limits.addWidget(QLabel("Timeout:"))
        limits.addWidget(self.timeout_spin)
        self.retries_spin = QSpinBox()
        self.retries_spin.setRange(0, 5)
        limits.addWidget(QLabel("Wiederholungen:"))
        limits.addWidget(self.retries_spin)
        limits.addStretch(1)
        ai_card.body().addLayout(limits)

        cache_row = QHBoxLayout()
        self.cache_label = QLabel("")
        self.cache_label.setObjectName("Dim")
        btn_clear_cache = QPushButton("Cache leeren")
        btn_clear_cache.clicked.connect(self.clear_cache)
        cache_row.addWidget(self.cache_label, 1)
        cache_row.addWidget(btn_clear_cache)
        ai_card.body().addLayout(cache_row)
        layout.addWidget(ai_card)

        # ------------------------------------------------------------ defaults
        defaults_card = Card("Standardwerte")
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Deutsch", "English"])
        defaults_card.body().addWidget(form_row("Sprache", self.language_combo, 130))

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["EUR", "CHF", "PLN", "CZK", "GBP"])
        defaults_card.body().addWidget(form_row("Währung", self.currency_combo, 130))

        self.strategy_combo = QComboBox()
        for strategy in PriceStrategy:
            self.strategy_combo.addItem(strategy.label, strategy.value)
        defaults_card.body().addWidget(form_row("Preisstrategie", self.strategy_combo, 130))

        self.rounding_combo = QComboBox()
        for value, label in ROUNDING_OPTIONS:
            self.rounding_combo.addItem(label, value)
        defaults_card.body().addWidget(form_row("Preisrundung", self.rounding_combo, 130))

        self.condition_combo = QComboBox()
        self.condition_combo.addItems(Condition.values())
        defaults_card.body().addWidget(form_row("Zustand", self.condition_combo, 130))

        self.seller_style_combo = QComboBox()
        self.seller_style_combo.addItems(["sachlich", "freundlich", "knapp"])
        defaults_card.body().addWidget(form_row("Verkäuferstil", self.seller_style_combo, 130))

        self.shipping_input = QLineEdit()
        defaults_card.body().addWidget(form_row("Versandtext", self.shipping_input, 130))

        self.default_description = QTextEdit()
        self.default_description.setMaximumHeight(80)
        self.default_description.setPlaceholderText(
            "Text, der an jede Beschreibung angehängt wird (optional)."
        )
        defaults_card.body().addWidget(form_row("Zusatztext", self.default_description, 130))

        self.preferred_categories = QLineEdit()
        self.preferred_categories.setPlaceholderText(
            "Bevorzugte Kategorien, durch Semikolon getrennt"
        )
        defaults_card.body().addWidget(form_row("Kategorien", self.preferred_categories, 130))
        layout.addWidget(defaults_card)

        # ------------------------------------------------------------- storage
        storage_card = Card("Bilder, Duplikate und Speicherorte")
        self.max_dimension_spin = QSpinBox()
        self.max_dimension_spin.setRange(600, 4000)
        self.max_dimension_spin.setSingleStep(100)
        self.max_dimension_spin.setSuffix(" px")
        storage_card.body().addWidget(form_row("Max. Bildgröße", self.max_dimension_spin, 130))

        self.duplicate_spin = QSpinBox()
        self.duplicate_spin.setRange(0, 20)
        self.duplicate_spin.setToolTip(
            "Je höher der Wert, desto mehr Bilder gelten als mögliches Duplikat."
        )
        storage_card.body().addWidget(form_row("Duplikat-Toleranz", self.duplicate_spin, 130))

        export_row = QHBoxLayout()
        self.export_dir_input = QLineEdit()
        self.export_dir_input.setPlaceholderText(str(exports_dir()))
        btn_browse = QPushButton("Wählen …")
        btn_browse.clicked.connect(self._choose_export_dir)
        export_row.addWidget(self.export_dir_input, 1)
        export_row.addWidget(btn_browse)
        storage_card.body().addWidget(form_row("Exportordner", self._wrap(export_row), 130))

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dunkel", "dark")
        self.theme_combo.addItem("Hell", "light")
        storage_card.body().addWidget(form_row("Design", self.theme_combo, 130))

        paths_label = QLabel(
            f"Datenordner: {data_dir()}\nDatenbank: {db_path()}\n"
            f"Bilder: {images_dir()}\nLogs: {logs_dir()}"
        )
        paths_label.setObjectName("Dim")
        paths_label.setWordWrap(True)
        storage_card.add(paths_label)
        folder_row = QHBoxLayout()
        btn_open_data = QPushButton("Datenordner öffnen")
        btn_open_data.clicked.connect(lambda: open_in_explorer(data_dir()))
        btn_open_logs = QPushButton("Logordner öffnen")
        btn_open_logs.clicked.connect(lambda: open_in_explorer(logs_dir()))
        folder_row.addWidget(btn_open_data)
        folder_row.addWidget(btn_open_logs)
        folder_row.addStretch(1)
        storage_card.body().addLayout(folder_row)
        layout.addWidget(storage_card)

        save_row = QHBoxLayout()
        self.btn_save = QPushButton("Einstellungen speichern")
        self.btn_save.setObjectName("Primary")
        self.btn_save.clicked.connect(self.save)
        save_row.addWidget(self.btn_save)
        save_row.addStretch(1)
        layout.addLayout(save_row)
        layout.addStretch(1)

        scroll.setWidget(container)
        outer.addWidget(scroll, 1)

    @staticmethod
    def _wrap(layout) -> QWidget:
        widget = QWidget()
        widget.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        return widget

    # -------------------------------------------------------------------- data
    def refresh(self) -> None:
        settings = self.ctx.settings
        index = self.provider_combo.findData(settings.provider_kind)
        self.provider_combo.setCurrentIndex(max(index, 0))
        self._populate_models(settings.kind)
        self.model_combo.setCurrentText(settings.model or DEFAULT_MODELS[settings.kind])
        self.base_url_input.setText(settings.base_url or DEFAULT_BASE_URLS[settings.kind])
        self.api_key_input.setText(self.ctx.settings_service.get_api_key(settings.provider_kind))
        self._update_key_hint(settings.kind)

        self.cache_check.setChecked(settings.cache_enabled)
        self.auto_analyze_check.setChecked(settings.auto_analyze_on_import)
        self.image_count_spin.setValue(settings.ai_image_count)
        self.timeout_spin.setValue(settings.request_timeout)
        self.retries_spin.setValue(settings.max_retries)

        self.language_combo.setCurrentText(settings.language)
        self.currency_combo.setCurrentText(settings.currency)
        self.strategy_combo.setCurrentIndex(
            max(self.strategy_combo.findData(settings.price_strategy), 0)
        )
        self.rounding_combo.setCurrentIndex(
            max(self.rounding_combo.findData(settings.price_rounding), 0)
        )
        self.condition_combo.setCurrentText(settings.default_condition)
        self.seller_style_combo.setCurrentText(settings.seller_style)
        self.shipping_input.setText(settings.default_shipping)
        self.default_description.setPlainText(settings.default_description)
        self.preferred_categories.setText("; ".join(settings.preferred_categories))

        self.max_dimension_spin.setValue(settings.max_image_dimension)
        self.duplicate_spin.setValue(settings.duplicate_threshold)
        self.export_dir_input.setText(settings.last_export_dir)
        self.theme_combo.setCurrentIndex(max(self.theme_combo.findData(settings.theme), 0))
        self._update_cache_label()

    def _populate_models(self, kind: ProviderKind) -> None:
        current = self.model_combo.currentText()
        self.model_combo.clear()
        self.model_combo.addItems(MODEL_SUGGESTIONS.get(kind, []))
        if current:
            self.model_combo.setCurrentText(current)

    def _on_provider_changed(self) -> None:
        kind = ProviderKind(self.provider_combo.currentData())
        self._populate_models(kind)
        self.model_combo.setCurrentText(DEFAULT_MODELS[kind])
        self.base_url_input.setText(DEFAULT_BASE_URLS[kind])
        self.api_key_input.setText(self.ctx.settings_service.get_api_key(kind.value))
        self._update_key_hint(kind)
        offline = kind == ProviderKind.OFFLINE
        self.api_key_input.setEnabled(not offline)
        self.model_combo.setEnabled(not offline)
        self.base_url_input.setEnabled(not offline)

    def _update_key_hint(self, kind: ProviderKind) -> None:
        env_name = ENV_KEYS.get(kind)
        stored = self.ctx.settings_service.get_api_key(kind.value)
        parts = []
        if stored:
            parts.append(f"Gespeichert: {mask(stored)} (verschlüsselt in der lokalen Datenbank)")
        if env_name:
            parts.append(f"Alternativ per Umgebungsvariable {env_name} (siehe .env.example).")
        if kind == ProviderKind.OFFLINE:
            parts = [
                "Die Offline-Analyse braucht keinen Key: Farben werden lokal erkannt, "
                "alle übrigen Felder füllst du selbst aus."
            ]
        if kind == ProviderKind.LOCAL:
            parts.append("Lokale Server (Ollama, LM Studio) brauchen meist keinen Key.")
        self.key_hint.setText(" ".join(parts))

    def _toggle_key_visibility(self, visible: bool) -> None:
        self.api_key_input.setEchoMode(
            QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        )
        self.btn_show_key.setText("Verbergen" if visible else "Anzeigen")

    def _update_cache_label(self) -> None:
        stats = self.ctx.analysis_service.cache_stats()
        self.cache_label.setText(
            f"Cache: {stats['entries']} gespeicherte Analysen, "
            f"{stats['tokens']} eingesparte Tokens bei Wiederholungen."
        )

    def _choose_export_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Exportordner wählen")
        if folder:
            self.export_dir_input.setText(folder)

    # ----------------------------------------------------------------- actions
    def collect_and_save(self) -> None:
        kind = ProviderKind(self.provider_combo.currentData())
        service = self.ctx.settings_service
        service.set_api_key(kind.value, self.api_key_input.text().strip())
        service.remember_provider_details(
            kind.value, self.model_combo.currentText().strip(), self.base_url_input.text().strip()
        )
        service.update(
            provider_kind=kind.value,
            model=self.model_combo.currentText().strip(),
            base_url=self.base_url_input.text().strip(),
            cache_enabled=self.cache_check.isChecked(),
            auto_analyze_on_import=self.auto_analyze_check.isChecked(),
            ai_image_count=self.image_count_spin.value(),
            request_timeout=self.timeout_spin.value(),
            max_retries=self.retries_spin.value(),
            language=self.language_combo.currentText(),
            currency=self.currency_combo.currentText(),
            price_strategy=self.strategy_combo.currentData(),
            price_rounding=self.rounding_combo.currentData(),
            default_condition=self.condition_combo.currentText(),
            seller_style=self.seller_style_combo.currentText(),
            default_shipping=self.shipping_input.text().strip(),
            default_description=self.default_description.toPlainText().strip(),
            preferred_categories=[
                c.strip() for c in self.preferred_categories.text().split(";") if c.strip()
            ],
            max_image_dimension=self.max_dimension_spin.value(),
            duplicate_threshold=self.duplicate_spin.value(),
            last_export_dir=self.export_dir_input.text().strip(),
            theme=self.theme_combo.currentData(),
        )

    def save(self) -> None:
        self.collect_and_save()
        self._update_key_hint(ProviderKind(self.provider_combo.currentData()))
        self.settings_changed.emit()
        self.status_message.emit("Einstellungen gespeichert.")
        QMessageBox.information(self, "Gespeichert", "Die Einstellungen wurden übernommen.")

    def test_connection(self) -> None:
        if self._worker and self._worker.isRunning():
            return
        self.collect_and_save()
        kind = self.provider_combo.currentData()
        self.btn_test.setEnabled(False)
        self.test_result.setText("Verbindung wird getestet …")
        self._worker = ConnectionTestWorker(self.ctx.analysis_service, kind, parent=self)
        self._worker.finished_ok.connect(self._on_test_done)
        self._worker.finished.connect(lambda: self.btn_test.setEnabled(True))
        self._worker.start()

    def _on_test_done(self, ok: bool, message: str, model: str) -> None:
        prefix = "✔" if ok else "⚠"
        color = "#3fbf7f" if ok else "#e5544b"
        self.test_result.setText(f"{prefix} {message}" + (f" (Modell: {model})" if model else ""))
        self.test_result.setStyleSheet(f"color:{color};")

    def clear_cache(self) -> None:
        removed = self.ctx.analysis_service.clear_cache()
        self._update_cache_label()
        self.status_message.emit(f"{removed} zwischengespeicherte Analysen gelöscht.")
