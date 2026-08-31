"""Main window: sidebar navigation plus the stacked pages."""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from vinted_tool import APP_NAME, __version__
from vinted_tool.app.context import AppContext
from vinted_tool.models.enums import ProviderKind
from vinted_tool.ui.pages.batch import BatchPage
from vinted_tool.ui.pages.dashboard import DashboardPage
from vinted_tool.ui.pages.drafts import DraftsPage
from vinted_tool.ui.pages.history import HistoryPage
from vinted_tool.ui.pages.new_listing import NewListingPage
from vinted_tool.ui.pages.settings_page import SettingsPage
from vinted_tool.ui.pages.templates_page import TemplatesPage
from vinted_tool.ui.theme import stylesheet

log = logging.getLogger(__name__)

NAV_ITEMS = [
    ("dashboard", "🏠  Dashboard"),
    ("new", "➕  Neue Anzeige"),
    ("batch", "📦  Batch-Modus"),
    ("drafts", "📝  Entwürfe"),
    ("history", "🕘  Verlauf"),
    ("templates", "📄  Vorlagen"),
    ("settings", "⚙  Einstellungen"),
]


class MainWindow(QMainWindow):
    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.ctx = context
        self.setWindowTitle(f"{APP_NAME} V2  ·  {__version__}")
        self.resize(1360, 900)
        self.setMinimumSize(1060, 700)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self.pages: dict[str, QWidget] = {}
        self._build_pages()
        self._build_shortcuts()

        self.status = self.statusBar()
        self.provider_label = QLabel("")
        self.status.addPermanentWidget(self.provider_label)
        self.show_status("Bereit.")
        self.navigate("dashboard")
        self.apply_theme()

    # ------------------------------------------------------------------ build
    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(230)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 18, 14, 18)
        layout.setSpacing(6)

        title = QLabel("Vinted\nAuto Listing")
        title.setObjectName("H2")
        layout.addWidget(title)
        version = QLabel(f"Version {__version__}")
        version.setObjectName("Dim")
        layout.addWidget(version)
        layout.addSpacing(14)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: dict[str, QPushButton] = {}
        for key, label in NAV_ITEMS:
            button = QPushButton(label)
            button.setObjectName("Nav")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _=False, k=key: self.navigate(k))
            layout.addWidget(button)
            self.nav_group.addButton(button)
            self.nav_buttons[key] = button

        layout.addStretch(1)
        hint = QLabel(
            "Vinted hat keine offizielle Schnittstelle zum Einstellen von Artikeln. "
            "Die App bereitet alles vor – veröffentlicht wird im Browser."
        )
        hint.setObjectName("Dim")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        return sidebar

    def _build_pages(self) -> None:
        self.dashboard = DashboardPage(self.ctx)
        self.new_listing = NewListingPage(self.ctx)
        self.batch = BatchPage(self.ctx)
        self.drafts = DraftsPage(self.ctx)
        self.history = HistoryPage(self.ctx)
        self.templates = TemplatesPage(self.ctx)
        self.settings_page = SettingsPage(self.ctx)

        for key, page in [
            ("dashboard", self.dashboard),
            ("new", self.new_listing),
            ("batch", self.batch),
            ("drafts", self.drafts),
            ("history", self.history),
            ("templates", self.templates),
            ("settings", self.settings_page),
        ]:
            self.pages[key] = page
            self.stack.addWidget(page)
            if hasattr(page, "status_message"):
                page.status_message.connect(self.show_status)
            if hasattr(page, "data_changed"):
                page.data_changed.connect(self.refresh_all)
            if hasattr(page, "open_listing"):
                page.open_listing.connect(self.open_listing)

        self.dashboard.navigate.connect(self.navigate)
        self.dashboard.images_imported.connect(self._import_from_dashboard)
        self.settings_page.settings_changed.connect(self._on_settings_changed)

    def _build_shortcuts(self) -> None:
        shortcuts = [
            ("Neue Anzeige", "Ctrl+N", lambda: self.navigate("new", fresh=True)),
            ("Dashboard", "Ctrl+1", lambda: self.navigate("dashboard")),
            ("Batch-Modus", "Ctrl+B", lambda: self.navigate("batch")),
            ("Entwürfe", "Ctrl+D", lambda: self.navigate("drafts")),
            ("Verlauf", "Ctrl+H", lambda: self.navigate("history")),
            ("Einstellungen", "Ctrl+,", lambda: self.navigate("settings")),
        ]
        for name, sequence, slot in shortcuts:
            action = QAction(name, self)
            action.setShortcut(QKeySequence(sequence))
            action.triggered.connect(slot)
            self.addAction(action)

    # --------------------------------------------------------------- behaviour
    def navigate(self, key: str, *, fresh: bool = False) -> None:
        page = self.pages.get(key)
        if page is None:
            return
        if key == "new" and fresh:
            self.new_listing.start_new()
        if hasattr(page, "refresh"):
            page.refresh()
        self.stack.setCurrentWidget(page)
        button = self.nav_buttons.get(key)
        if button:
            button.setChecked(True)

    def open_listing(self, listing) -> None:
        self.new_listing.load_listing(listing)
        self.navigate("new")
        self.show_status(f"Anzeige „{listing.title or listing.id}“ geöffnet.")

    def _import_from_dashboard(self, paths: list) -> None:
        self.new_listing.start_new()
        self.navigate("new")
        self.new_listing.import_paths(paths)

    def refresh_all(self) -> None:
        for key in ("dashboard", "drafts", "history"):
            page = self.pages[key]
            if hasattr(page, "refresh"):
                page.refresh()
        self.new_listing.refresh()
        self._update_provider_label()

    def _on_settings_changed(self) -> None:
        self.apply_theme()
        self.refresh_all()

    def apply_theme(self) -> None:
        theme = self.ctx.settings.theme
        instance = QApplication.instance()
        if instance is not None:
            instance.setStyleSheet(stylesheet(theme))
        self._update_provider_label()

    def _update_provider_label(self) -> None:
        settings = self.ctx.settings
        try:
            label = ProviderKind(settings.provider_kind).label
        except ValueError:
            label = settings.provider_kind
        model = settings.model or "Standardmodell"
        self.provider_label.setText(f"KI: {label} · {model}")

    def show_status(self, message: str, timeout: int = 6000) -> None:
        self.status.showMessage(message, timeout)

    def closeEvent(self, event) -> None:  # noqa: N802
        unsaved = self.new_listing.editor.image_strip.images and self.new_listing.editor.listing.id is None
        if unsaved:
            answer = QMessageBox.question(
                self,
                "Nicht gespeicherte Anzeige",
                "Die aktuelle Anzeige wurde noch nicht gespeichert. Als Entwurf sichern?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.StandardButton.Yes:
                try:
                    self.new_listing.editor.save_draft()
                except Exception:  # noqa: BLE001
                    log.exception("Entwurf konnte beim Schließen nicht gespeichert werden")
        self.ctx.close()
        event.accept()
