PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS listings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    title               TEXT    NOT NULL DEFAULT '',
    description         TEXT    NOT NULL DEFAULT '',
    category_path       TEXT    NOT NULL DEFAULT '[]',
    category_candidates TEXT    NOT NULL DEFAULT '[]',
    brand               TEXT    NOT NULL DEFAULT '',
    size                TEXT    NOT NULL DEFAULT '',
    color               TEXT    NOT NULL DEFAULT '',
    condition           TEXT    NOT NULL DEFAULT '',
    material            TEXT    NOT NULL DEFAULT '',
    price               REAL    NOT NULL DEFAULT 0,
    currency            TEXT    NOT NULL DEFAULT 'EUR',
    keywords            TEXT    NOT NULL DEFAULT '[]',
    shipping            TEXT    NOT NULL DEFAULT '',
    status              TEXT    NOT NULL DEFAULT 'draft',
    price_suggestion    TEXT    NOT NULL DEFAULT '{}',
    analysis            TEXT    NOT NULL DEFAULT '{}',
    notes               TEXT    NOT NULL DEFAULT '',
    batch_id            TEXT,
    created_at          TEXT    NOT NULL,
    updated_at          TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_listings_status  ON listings(status);
CREATE INDEX IF NOT EXISTS idx_listings_created ON listings(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_listings_batch   ON listings(batch_id);

CREATE TABLE IF NOT EXISTS images (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id     INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    path           TEXT    NOT NULL,
    original_name  TEXT    NOT NULL DEFAULT '',
    thumbnail_path TEXT,
    phash          TEXT,
    sha256         TEXT,
    width          INTEGER NOT NULL DEFAULT 0,
    height         INTEGER NOT NULL DEFAULT 0,
    position       INTEGER NOT NULL DEFAULT 0,
    is_primary     INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_images_listing ON images(listing_id, position);
CREATE INDEX IF NOT EXISTS idx_images_phash   ON images(phash);
CREATE INDEX IF NOT EXISTS idx_images_sha     ON images(sha256);

CREATE TABLE IF NOT EXISTS templates (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    body       TEXT    NOT NULL,
    is_default INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_cache (
    cache_key   TEXT PRIMARY KEY,
    payload     TEXT NOT NULL,
    provider    TEXT NOT NULL DEFAULT '',
    model       TEXT NOT NULL DEFAULT '',
    tokens_used INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS provider_configs (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    kind     TEXT NOT NULL UNIQUE,
    model    TEXT NOT NULL DEFAULT '',
    base_url TEXT NOT NULL DEFAULT '',
    api_key  TEXT NOT NULL DEFAULT '',
    enabled  INTEGER NOT NULL DEFAULT 1
);
