"""Application context – wires repositories and services together."""
from __future__ import annotations

import logging
from pathlib import Path

from vinted_tool.ai.service import AnalysisService
from vinted_tool.core.templates import DEFAULT_TEMPLATES
from vinted_tool.database.db import Database
from vinted_tool.database.repositories import (
    AnalysisCacheRepository,
    ListingRepository,
    ProviderConfigRepository,
    SettingsRepository,
    TemplateRepository,
)
from vinted_tool.models.template_model import Template
from vinted_tool.services.batch_service import BatchService
from vinted_tool.services.image_service import ImageService
from vinted_tool.services.listing_service import ListingService
from vinted_tool.services.settings_service import SettingsService

log = logging.getLogger(__name__)


class AppContext:
    def __init__(self, db_path: Path | str | None = None, image_dir: Path | None = None) -> None:
        self.db = Database(db_path)
        self.listing_repo = ListingRepository(self.db)
        self.template_repo = TemplateRepository(self.db)
        self.settings_repo = SettingsRepository(self.db)
        self.cache_repo = AnalysisCacheRepository(self.db)
        self.provider_repo = ProviderConfigRepository(self.db)

        self.settings_service = SettingsService(self.settings_repo, self.provider_repo)
        self.image_service = ImageService(image_dir)
        self.analysis_service = AnalysisService(self.settings_service, self.cache_repo)
        self.listing_service = ListingService(
            self.listing_repo, self.template_repo, self.settings_service
        )
        self.batch_service = BatchService(
            self.image_service, self.analysis_service, self.listing_service, self.settings_service
        )
        self.seed_templates()

    def seed_templates(self) -> None:
        if self.template_repo.list():
            return
        for name, body, is_default in DEFAULT_TEMPLATES:
            self.template_repo.save(Template(name=name, body=body, is_default=is_default))
        log.info("Standardvorlagen angelegt")

    @property
    def settings(self):
        return self.settings_service.load()

    def close(self) -> None:
        self.db.close()
