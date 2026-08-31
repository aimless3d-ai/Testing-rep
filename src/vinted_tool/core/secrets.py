"""Local encryption for API keys.

Keys are stored encrypted with a machine-local Fernet key (file permissions
0600). This protects against casual reading of the database file; it is not a
substitute for OS level secret storage, and the README says so.
"""
from __future__ import annotations

import logging
import os
import stat

from cryptography.fernet import Fernet, InvalidToken

from vinted_tool.app.paths import secret_key_path

log = logging.getLogger(__name__)
_PREFIX = "enc:"


def _load_key() -> bytes:
    path = secret_key_path()
    if path.exists():
        return path.read_bytes().strip()
    key = Fernet.generate_key()
    path.write_bytes(key)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:  # pragma: no cover - Windows/ACL differences
        log.debug("Could not tighten permissions on the key file")
    return key


def encrypt(value: str) -> str:
    if not value:
        return ""
    if value.startswith(_PREFIX):
        return value
    token = Fernet(_load_key()).encrypt(value.encode("utf-8")).decode("ascii")
    return _PREFIX + token


def decrypt(value: str) -> str:
    if not value:
        return ""
    if not value.startswith(_PREFIX):
        return value  # legacy/plain value – returned as-is so nothing breaks
    try:
        return Fernet(_load_key()).decrypt(value[len(_PREFIX):].encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        log.warning("Stored API key could not be decrypted (key file changed?)")
        return ""


def mask(value: str) -> str:
    """Return a display-safe version of a secret."""
    if not value:
        return ""
    if len(value) <= 8:
        return "•" * len(value)
    return f"{value[:4]}{'•' * 8}{value[-4:]}"
