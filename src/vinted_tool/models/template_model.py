"""Description templates with ``{{variable}}`` placeholders."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from vinted_tool.models.listing import utcnow


@dataclass(slots=True)
class Template:
    name: str
    body: str
    is_default: bool = False
    created_at: str = ""
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = utcnow()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Template":
        known = set(cls.__slots__)
        return cls(**{k: v for k, v in (raw or {}).items() if k in known})
