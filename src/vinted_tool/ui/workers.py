"""Background workers so the UI never freezes during AI or batch runs."""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from vinted_tool.ai.service import AnalysisOutcome, AnalysisService
from vinted_tool.core.errors import VintedToolError
from vinted_tool.services.batch_service import BatchResult, BatchService

log = logging.getLogger(__name__)


class AnalysisWorker(QThread):
    """Runs one AI analysis off the GUI thread."""

    finished_ok = Signal(object)   # AnalysisOutcome
    failed = Signal(str, str)      # user message, technical detail

    def __init__(
        self,
        service: AnalysisService,
        image_paths: list[str | Path],
        *,
        hint: str = "",
        force_refresh: bool = False,
        offline: bool = False,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.image_paths = list(image_paths)
        self.hint = hint
        self.force_refresh = force_refresh
        self.offline = offline

    def run(self) -> None:  # pragma: no cover - thread body
        try:
            if self.offline:
                outcome: AnalysisOutcome = self.service.analyze_offline(
                    self.image_paths, hint=self.hint
                )
            else:
                outcome = self.service.analyze(
                    self.image_paths, hint=self.hint, force_refresh=self.force_refresh
                )
            self.finished_ok.emit(outcome)
        except VintedToolError as exc:
            log.warning("Analyse fehlgeschlagen: %s", exc)
            self.failed.emit(exc.user_message, str(exc))
        except Exception as exc:  # noqa: BLE001
            log.exception("Unerwarteter Fehler in der Analyse")
            self.failed.emit(
                "Die Analyse ist unerwartet fehlgeschlagen. Details stehen im Log.", str(exc)
            )


class BatchWorker(QThread):
    """Processes a whole batch and reports progress per product."""

    progress = Signal(int, int, str)
    finished_ok = Signal(object)   # BatchResult
    failed = Signal(str, str)

    def __init__(
        self,
        service: BatchService,
        paths: list[Path],
        *,
        mode: str = "prefix",
        use_ai: bool = True,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.paths = paths
        self.mode = mode
        self.use_ai = use_ai
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:  # pragma: no cover - thread body
        try:
            result: BatchResult = self.service.run(
                self.paths,
                mode=self.mode,
                progress=lambda i, total, name: self.progress.emit(i, total, name),
                should_cancel=lambda: self._cancelled,
                use_ai=self.use_ai,
            )
            self.finished_ok.emit(result)
        except VintedToolError as exc:
            self.failed.emit(exc.user_message, str(exc))
        except Exception as exc:  # noqa: BLE001
            log.exception("Unerwarteter Fehler im Batch-Modus")
            self.failed.emit("Der Batch-Lauf ist unerwartet fehlgeschlagen.", str(exc))


class ConnectionTestWorker(QThread):
    """Runs the "API-Verbindung testen" round trip."""

    finished_ok = Signal(bool, str, str)  # ok, message, model

    def __init__(self, service: AnalysisService, kind: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.kind = kind

    def run(self) -> None:  # pragma: no cover - thread body
        try:
            status = self.service.test_connection(self.kind)
            self.finished_ok.emit(status.ok, status.message, status.model)
        except VintedToolError as exc:
            self.finished_ok.emit(False, exc.user_message, "")
        except Exception as exc:  # noqa: BLE001
            log.exception("Verbindungstest fehlgeschlagen")
            self.finished_ok.emit(False, f"Unerwarteter Fehler: {exc}", "")
