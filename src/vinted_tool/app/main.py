"""Application entry point."""
from __future__ import annotations

import logging
import sys
import traceback
from types import TracebackType

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from vinted_tool import APP_NAME, __version__
from vinted_tool.app.context import AppContext
from vinted_tool.app.logging_setup import setup_logging
from vinted_tool.app.paths import logs_dir
from vinted_tool.app.resources import icon_path
from vinted_tool.ui.main_window import MainWindow
from vinted_tool.ui.theme import stylesheet

log = logging.getLogger(__name__)


def _install_excepthook(app: QApplication) -> None:
    """Show unexpected errors instead of letting the app die silently."""

    def hook(exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        detail = "".join(traceback.format_exception(exc_type, exc, tb))
        log.error("Unbehandelte Ausnahme:\n%s", detail)
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("Unerwarteter Fehler")
        box.setText(
            "Es ist ein unerwarteter Fehler aufgetreten. Die Anwendung läuft weiter.\n"
            f"Details stehen im Log: {logs_dir() / 'app.log'}"
        )
        box.setDetailedText(detail)
        box.exec()

    sys.excepthook = hook


def main(argv: list[str] | None = None) -> int:
    log_path = setup_logging()
    log.info("%s %s startet – Log: %s", APP_NAME, __version__, log_path)

    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("VintedAutoListingTool")
    icon = icon_path()
    if icon:
        app.setWindowIcon(QIcon(str(icon)))
    _install_excepthook(app)

    try:
        context = AppContext()
    except Exception as exc:  # noqa: BLE001
        log.exception("Start fehlgeschlagen")
        QMessageBox.critical(
            None,
            "Start fehlgeschlagen",
            f"Die Datenbank konnte nicht geöffnet werden:\n{exc}",
        )
        return 1

    app.setStyleSheet(stylesheet(context.settings.theme))
    window = MainWindow(context)
    window.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
