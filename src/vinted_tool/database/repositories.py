"""Repositories: the only place that knows about SQL rows."""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Iterable

from vinted_tool.database.db import Database
from vinted_tool.models.listing import Listing, ListingImage, PriceSuggestion, utcnow
from vinted_tool.models.template_model import Template


def _loads(raw: Any, fallback: Any) -> Any:
    if raw in (None, ""):
        return fallback
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return fallback


class ListingRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ---------------------------------------------------------------- mapping
    def _row_to_listing(self, row: sqlite3.Row, images: list[ListingImage]) -> Listing:
        return Listing(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            category_path=_loads(row["category_path"], []),
            category_candidates=_loads(row["category_candidates"], []),
            brand=row["brand"],
            size=row["size"],
            color=row["color"],
            condition=row["condition"],
            material=row["material"],
            price=row["price"],
            currency=row["currency"],
            keywords=_loads(row["keywords"], []),
            shipping=row["shipping"],
            status=row["status"],
            price_suggestion=PriceSuggestion.from_dict(_loads(row["price_suggestion"], {})),
            analysis=_loads(row["analysis"], {}),
            notes=row["notes"],
            batch_id=row["batch_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            images=images,
        )

    def _images_for(self, listing_id: int) -> list[ListingImage]:
        rows = self.db.query(
            "SELECT * FROM images WHERE listing_id = ? ORDER BY position, id", (listing_id,)
        )
        return [
            ListingImage(
                id=r["id"],
                path=r["path"],
                original_name=r["original_name"],
                thumbnail_path=r["thumbnail_path"],
                phash=r["phash"],
                sha256=r["sha256"],
                width=r["width"],
                height=r["height"],
                position=r["position"],
                is_primary=bool(r["is_primary"]),
            )
            for r in rows
        ]

    # ------------------------------------------------------------------ CRUD
    def save(self, listing: Listing) -> Listing:
        listing.updated_at = utcnow()
        fields = (
            listing.title,
            listing.description,
            json.dumps(listing.category_path, ensure_ascii=False),
            json.dumps(listing.category_candidates, ensure_ascii=False),
            listing.brand,
            listing.size,
            listing.color,
            listing.condition,
            listing.material,
            float(listing.price or 0),
            listing.currency,
            json.dumps(listing.keywords, ensure_ascii=False),
            listing.shipping,
            listing.status,
            json.dumps(listing.price_suggestion.to_dict(), ensure_ascii=False),
            json.dumps(listing.analysis, ensure_ascii=False),
            listing.notes,
            listing.batch_id,
            listing.updated_at,
        )
        conn = self.db.conn
        with conn:
            if listing.id is None:
                cur = conn.execute(
                    """INSERT INTO listings (title, description, category_path,
                        category_candidates, brand, size, color, condition, material,
                        price, currency, keywords, shipping, status, price_suggestion,
                        analysis, notes, batch_id, updated_at, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    fields + (listing.created_at,),
                )
                listing.id = int(cur.lastrowid)
            else:
                conn.execute(
                    """UPDATE listings SET title=?, description=?, category_path=?,
                        category_candidates=?, brand=?, size=?, color=?, condition=?,
                        material=?, price=?, currency=?, keywords=?, shipping=?, status=?,
                        price_suggestion=?, analysis=?, notes=?, batch_id=?, updated_at=?
                       WHERE id=?""",
                    fields + (listing.id,),
                )
            conn.execute("DELETE FROM images WHERE listing_id = ?", (listing.id,))
            for position, image in enumerate(listing.images):
                image.position = position
                cur = conn.execute(
                    """INSERT INTO images (listing_id, path, original_name, thumbnail_path,
                        phash, sha256, width, height, position, is_primary)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        listing.id,
                        image.path,
                        image.original_name,
                        image.thumbnail_path,
                        image.phash,
                        image.sha256,
                        image.width,
                        image.height,
                        position,
                        int(image.is_primary),
                    ),
                )
                image.id = int(cur.lastrowid)
        return listing

    def get(self, listing_id: int) -> Listing | None:
        row = self.db.query_one("SELECT * FROM listings WHERE id = ?", (listing_id,))
        if row is None:
            return None
        return self._row_to_listing(row, self._images_for(listing_id))

    def delete(self, listing_id: int) -> None:
        self.db.execute("DELETE FROM listings WHERE id = ?", (listing_id,))

    def list(
        self,
        *,
        status: str | Iterable[str] | None = None,
        search: str | None = None,
        batch_id: str | None = None,
        limit: int = 500,
    ) -> list[Listing]:
        sql = "SELECT * FROM listings WHERE 1=1"
        params: list[Any] = []
        if status:
            statuses = [status] if isinstance(status, str) else list(status)
            sql += f" AND status IN ({','.join('?' * len(statuses))})"
            params.extend(statuses)
        if batch_id:
            sql += " AND batch_id = ?"
            params.append(batch_id)
        if search:
            needle = f"%{search.strip().lower()}%"
            sql += (
                " AND (lower(title) LIKE ? OR lower(description) LIKE ?"
                " OR lower(brand) LIKE ? OR lower(keywords) LIKE ?)"
            )
            params.extend([needle] * 4)
        sql += " ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)
        rows = self.db.query(sql, tuple(params))
        return [self._row_to_listing(r, self._images_for(r["id"])) for r in rows]

    def counts_by_status(self) -> dict[str, int]:
        rows = self.db.query("SELECT status, COUNT(*) AS n FROM listings GROUP BY status")
        return {r["status"]: r["n"] for r in rows}

    def all_image_fingerprints(self, exclude_listing_id: int | None = None) -> list[dict[str, Any]]:
        sql = (
            "SELECT i.id, i.listing_id, i.phash, i.sha256, i.path, l.title "
            "FROM images i JOIN listings l ON l.id = i.listing_id"
        )
        params: tuple = ()
        if exclude_listing_id is not None:
            sql += " WHERE i.listing_id != ?"
            params = (exclude_listing_id,)
        return [dict(r) for r in self.db.query(sql, params)]


class TemplateRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def save(self, template: Template) -> Template:
        conn = self.db.conn
        with conn:
            if template.is_default:
                conn.execute("UPDATE templates SET is_default = 0")
            if template.id is None:
                cur = conn.execute(
                    "INSERT INTO templates (name, body, is_default, created_at) VALUES (?,?,?,?)",
                    (template.name, template.body, int(template.is_default), template.created_at),
                )
                template.id = int(cur.lastrowid)
            else:
                conn.execute(
                    "UPDATE templates SET name=?, body=?, is_default=? WHERE id=?",
                    (template.name, template.body, int(template.is_default), template.id),
                )
        return template

    def list(self) -> list[Template]:
        rows = self.db.query("SELECT * FROM templates ORDER BY is_default DESC, name")
        return [
            Template(
                id=r["id"],
                name=r["name"],
                body=r["body"],
                is_default=bool(r["is_default"]),
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def get_default(self) -> Template | None:
        return next((t for t in self.list() if t.is_default), None)

    def delete(self, template_id: int) -> None:
        self.db.execute("DELETE FROM templates WHERE id = ?", (template_id,))


class SettingsRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get_all(self) -> dict[str, Any]:
        rows = self.db.query("SELECT key, value FROM settings")
        return {r["key"]: _loads(r["value"], r["value"]) for r in rows}

    def set(self, key: str, value: Any) -> None:
        self.db.execute(
            "INSERT INTO settings(key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value, ensure_ascii=False)),
        )

    def set_many(self, values: dict[str, Any]) -> None:
        conn = self.db.conn
        with conn:
            for key, value in values.items():
                conn.execute(
                    "INSERT INTO settings(key, value) VALUES (?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, json.dumps(value, ensure_ascii=False)),
                )


class AnalysisCacheRepository:
    """Cache of AI results so the same photos are never paid for twice."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def get(self, cache_key: str) -> dict[str, Any] | None:
        row = self.db.query_one(
            "SELECT payload FROM analysis_cache WHERE cache_key = ?", (cache_key,)
        )
        return _loads(row["payload"], None) if row else None

    def put(
        self, cache_key: str, payload: dict[str, Any], provider: str, model: str, tokens: int
    ) -> None:
        self.db.execute(
            "INSERT INTO analysis_cache(cache_key, payload, provider, model, tokens_used, created_at)"
            " VALUES (?,?,?,?,?,?) ON CONFLICT(cache_key) DO UPDATE SET"
            " payload=excluded.payload, provider=excluded.provider, model=excluded.model,"
            " tokens_used=excluded.tokens_used, created_at=excluded.created_at",
            (cache_key, json.dumps(payload, ensure_ascii=False), provider, model, tokens, utcnow()),
        )

    def clear(self) -> int:
        cur = self.db.execute("DELETE FROM analysis_cache")
        return cur.rowcount or 0

    def stats(self) -> dict[str, int]:
        row = self.db.query_one(
            "SELECT COUNT(*) AS entries, COALESCE(SUM(tokens_used),0) AS tokens FROM analysis_cache"
        )
        return {"entries": row["entries"], "tokens": row["tokens"]} if row else {"entries": 0, "tokens": 0}


class ProviderConfigRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get(self, kind: str) -> dict[str, Any] | None:
        row = self.db.query_one("SELECT * FROM provider_configs WHERE kind = ?", (kind,))
        return dict(row) if row else None

    def upsert(self, kind: str, *, model: str, base_url: str, api_key: str, enabled: bool = True) -> None:
        self.db.execute(
            "INSERT INTO provider_configs(kind, model, base_url, api_key, enabled)"
            " VALUES (?,?,?,?,?) ON CONFLICT(kind) DO UPDATE SET"
            " model=excluded.model, base_url=excluded.base_url,"
            " api_key=excluded.api_key, enabled=excluded.enabled",
            (kind, model, base_url, api_key, int(enabled)),
        )

    def all(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self.db.query("SELECT * FROM provider_configs ORDER BY kind")]
