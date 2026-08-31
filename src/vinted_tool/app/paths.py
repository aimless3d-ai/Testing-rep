"""Central place for every filesystem path the app uses."""
from __future__ import annotations

import os
from pathlib import Path

from platformdirs import PlatformDirs

from vinted_tool import APP_SLUG

_ENV_DATA_DIR = "VINTED_TOOL_DATA_DIR"


def _dirs() -> PlatformDirs:
    return PlatformDirs(appname=APP_SLUG, appauthor=False, roaming=True)


def data_dir() -> Path:
    """Root directory for the database, images, logs and the secret key."""
    override = os.environ.get(_ENV_DATA_DIR)
    base = Path(override).expanduser() if override else Path(_dirs().user_data_dir)
    base.mkdir(parents=True, exist_ok=True)
    return base


def db_path() -> Path:
    return data_dir() / "vinted_tool.sqlite3"


def images_dir() -> Path:
    p = data_dir() / "images"
    p.mkdir(parents=True, exist_ok=True)
    return p


def thumbs_dir() -> Path:
    p = data_dir() / "thumbnails"
    p.mkdir(parents=True, exist_ok=True)
    return p


def exports_dir() -> Path:
    p = data_dir() / "exports"
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    p = data_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def secret_key_path() -> Path:
    return data_dir() / "secret.key"
