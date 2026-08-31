"""Logging with automatic redaction of anything that looks like an API key."""
from __future__ import annotations

import logging
import logging.handlers
import re
import sys
from pathlib import Path

from vinted_tool.app.paths import logs_dir

_SECRET_PATTERNS = [
    re.compile(r"(sk-[A-Za-z0-9_\-]{8,})"),
    re.compile(r"(sk-or-v1-[A-Za-z0-9_\-]{8,})"),
    re.compile(r"(sk-ant-[A-Za-z0-9_\-]{8,})"),
    re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._\-]{12,})"),
    re.compile(r"(?i)(\"?api[_-]?key\"?\s*[:=]\s*\"?)([^\"\s,}]{8,})"),
]

_registered_secrets: set[str] = set()


def register_secret(value: str | None) -> None:
    """Register a concrete secret so it is masked even if it has an odd shape."""
    if value and len(value) >= 8:
        _registered_secrets.add(value)


def redact(text: str) -> str:
    for secret in _registered_secrets:
        text = text.replace(secret, "***REDACTED***")
    for pattern in _SECRET_PATTERNS:
        if pattern.groups == 2:
            text = pattern.sub(lambda m: f"{m.group(1)}***REDACTED***", text)
        else:
            text = pattern.sub("***REDACTED***", text)
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        try:
            record.msg = redact(str(record.msg))
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: redact(str(v)) for k, v in record.args.items()}
                else:
                    record.args = tuple(redact(str(a)) for a in record.args)
        except Exception:  # never let logging break the app
            pass
        return True


def setup_logging(level: int = logging.INFO, log_file: Path | None = None) -> Path:
    path = log_file or (logs_dir() / "app.log")
    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    redactor = RedactingFilter()

    file_handler = logging.handlers.RotatingFileHandler(
        path, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.addFilter(redactor)
    root.addHandler(file_handler)

    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(fmt)
    stream.addFilter(redactor)
    root.addHandler(stream)
    return path
