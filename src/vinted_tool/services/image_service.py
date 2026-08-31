"""Image import pipeline: EXIF, rotation, optimisation, thumbnails, fingerprints."""
from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from vinted_tool.app.paths import images_dir, thumbs_dir
from vinted_tool.core.errors import ImageError
from vinted_tool.models.listing import ListingImage
from vinted_tool.utils.files import slugify, unique_path
from vinted_tool.utils.hashing import dhash, sha256_file

log = logging.getLogger(__name__)

THUMB_SIZE = (320, 320)
JPEG_QUALITY = 88


@dataclass(slots=True)
class ImportOptions:
    max_dimension: int = 1600
    name_hint: str = ""
    quality: int = JPEG_QUALITY


class ImageService:
    """Copies user images into the app storage in a normalised form."""

    def __init__(self, storage_dir: Path | None = None, thumb_dir: Path | None = None) -> None:
        self._storage = storage_dir
        self._thumbs = thumb_dir

    @property
    def storage_dir(self) -> Path:
        path = self._storage or images_dir()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def thumb_dir(self) -> Path:
        path = self._thumbs or thumbs_dir()
        path.mkdir(parents=True, exist_ok=True)
        return path

    # ------------------------------------------------------------------ import
    def import_image(
        self, source: Path | str, options: ImportOptions | None = None, index: int = 0
    ) -> ListingImage:
        options = options or ImportOptions()
        source = Path(source)
        if not source.is_file():
            raise ImageError(f"Datei nicht gefunden: {source}")

        stem = slugify(options.name_hint or source.stem, fallback="produkt")
        target = unique_path(self.storage_dir / f"{stem}-{index + 1:02d}.jpg")

        try:
            with Image.open(source) as img:
                img = ImageOps.exif_transpose(img)  # honours the EXIF orientation flag
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                elif img.mode == "L":
                    img = img.convert("RGB")
                max_dim = max(400, options.max_dimension)
                if max(img.size) > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                width, height = img.size
                img.save(target, format="JPEG", quality=options.quality, optimize=True)
                thumb_path = self._write_thumbnail(img, target.stem)
        except UnidentifiedImageError as exc:
            raise ImageError(f"„{source.name}“ ist kein lesbares Bild.") from exc
        except OSError as exc:
            raise ImageError(f"„{source.name}“ konnte nicht verarbeitet werden: {exc}") from exc

        return ListingImage(
            path=str(target),
            original_name=source.name,
            thumbnail_path=str(thumb_path) if thumb_path else None,
            phash=self._safe_dhash(target),
            sha256=sha256_file(target),
            width=width,
            height=height,
            position=index,
            is_primary=index == 0,
        )

    def import_many(
        self, sources: list[Path | str], options: ImportOptions | None = None
    ) -> tuple[list[ListingImage], list[str]]:
        """Import several files; returns ``(images, error_messages)``."""
        images: list[ListingImage] = []
        errors: list[str] = []
        for index, source in enumerate(sources):
            try:
                images.append(self.import_image(source, options, index=len(images)))
            except ImageError as exc:
                log.warning("Bildimport fehlgeschlagen: %s", exc)
                errors.append(exc.user_message)
        self.renumber(images)
        return images, errors

    # ----------------------------------------------------------------- helpers
    def _write_thumbnail(self, img: Image.Image, stem: str) -> Path | None:
        try:
            thumb = img.copy()
            thumb.thumbnail(THUMB_SIZE, Image.Resampling.LANCZOS)
            path = unique_path(self.thumb_dir / f"{stem}-thumb.jpg")
            thumb.save(path, format="JPEG", quality=80, optimize=True)
            return path
        except OSError as exc:  # a missing thumbnail must never break the import
            log.warning("Thumbnail konnte nicht erstellt werden: %s", exc)
            return None

    @staticmethod
    def _safe_dhash(path: Path) -> str | None:
        try:
            return dhash(path)
        except (OSError, ValueError) as exc:
            log.warning("Perceptual hash fehlgeschlagen für %s: %s", path.name, exc)
            return None

    @staticmethod
    def renumber(images: list[ListingImage]) -> list[ListingImage]:
        """Keep positions consecutive and exactly one primary image."""
        for position, image in enumerate(images):
            image.position = position
        if images and not any(i.is_primary for i in images):
            images[0].is_primary = True
        primary_seen = False
        for image in images:
            if image.is_primary:
                if primary_seen:
                    image.is_primary = False
                primary_seen = True
        return images

    @staticmethod
    def set_primary(images: list[ListingImage], index: int) -> None:
        for position, image in enumerate(images):
            image.is_primary = position == index

    @staticmethod
    def move(images: list[ListingImage], index: int, offset: int) -> int:
        new_index = max(0, min(len(images) - 1, index + offset))
        if new_index != index:
            images.insert(new_index, images.pop(index))
        ImageService.renumber(images)
        return new_index

    def rename_for_listing(self, images: list[ListingImage], title: str) -> list[ListingImage]:
        """Give the stored files meaningful names derived from the final title."""
        stem = slugify(title, fallback="anzeige")
        for position, image in enumerate(images):
            old = Path(image.path)
            if not old.exists():
                continue
            new = unique_path(old.with_name(f"{stem}-{position + 1:02d}{old.suffix}"))
            if new == old:
                continue
            try:
                shutil.move(str(old), str(new))
            except OSError as exc:
                log.warning("Umbenennen fehlgeschlagen (%s): %s", old.name, exc)
                continue
            image.path = str(new)
        return images

    @staticmethod
    def delete_files(image: ListingImage) -> None:
        for candidate in (image.path, image.thumbnail_path):
            if not candidate:
                continue
            try:
                Path(candidate).unlink(missing_ok=True)
            except OSError as exc:  # pragma: no cover - permission issues
                log.warning("Datei konnte nicht gelöscht werden: %s", exc)
