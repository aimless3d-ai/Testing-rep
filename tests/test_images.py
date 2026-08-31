from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from vinted_tool.core.errors import ImageError
from vinted_tool.services.image_service import ImageService, ImportOptions
from vinted_tool.utils.files import collect_images, is_image, slugify, unique_path
from vinted_tool.utils.hashing import dhash, sha256_file


@pytest.fixture
def service(tmp_path):
    return ImageService(tmp_path / "store", tmp_path / "thumbs")


def test_import_normalises_and_shrinks(service, tmp_path):
    source = tmp_path / "Bild Übergröße.png"
    Image.new("RGB", (3000, 2000), (10, 120, 200)).save(source)
    image = service.import_image(source, ImportOptions(max_dimension=1200))
    assert Path(image.path).suffix == ".jpg"
    assert max(image.width, image.height) == 1200
    assert image.is_primary is True
    assert image.original_name == "Bild Übergröße.png"
    assert Path(image.thumbnail_path).exists()
    assert image.sha256 and image.phash


def test_exif_rotation_is_applied(service, tmp_path):
    source = tmp_path / "rotated.jpg"
    img = Image.new("RGB", (400, 200), (200, 30, 30))
    exif = img.getexif()
    exif[274] = 6  # orientation: rotate 90°
    img.save(source, exif=exif)
    image = service.import_image(source)
    assert (image.width, image.height) == (200, 400)


def test_import_many_reports_broken_files(service, tmp_path):
    good = tmp_path / "ok.jpg"
    Image.new("RGB", (100, 100)).save(good)
    broken = tmp_path / "broken.jpg"
    broken.write_text("not an image")
    images, errors = service.import_many([good, broken])
    assert len(images) == 1
    assert len(errors) == 1
    assert "broken.jpg" in errors[0]


def test_missing_file_raises(service, tmp_path):
    with pytest.raises(ImageError):
        service.import_image(tmp_path / "nope.jpg")


def test_reorder_and_primary(service, tmp_path):
    paths = []
    for index in range(3):
        path = tmp_path / f"p{index}.jpg"
        Image.new("RGB", (60, 60), (index * 40, 10, 10)).save(path)
        paths.append(path)
    images, _ = service.import_many(paths)
    ImageService.set_primary(images, 2)
    assert [i.is_primary for i in images] == [False, False, True]
    ImageService.move(images, 2, -1)
    assert images[1].is_primary is True
    assert [i.position for i in images] == [0, 1, 2]


def test_rename_for_listing(service, tmp_path):
    source = tmp_path / "irgendwas.jpg"
    Image.new("RGB", (80, 80)).save(source)
    images, _ = service.import_many([source])
    service.rename_for_listing(images, "Nike Hoodie Größe M")
    assert Path(images[0].path).name.startswith("nike-hoodie-groesse-m-01")
    assert Path(images[0].path).exists()


def test_hashes_are_stable_and_differ(tmp_path):
    a = tmp_path / "a.jpg"
    b = tmp_path / "b.jpg"
    Image.new("RGB", (200, 200), (0, 0, 0)).save(a)
    img = Image.new("RGB", (200, 200), (0, 0, 0))
    for x in range(100):
        for y in range(200):
            img.putpixel((x, y), (255, 255, 255))
    img.save(b)
    assert dhash(a) == dhash(a)
    assert dhash(a) != dhash(b)
    assert sha256_file(a) != sha256_file(b)


def test_file_helpers(tmp_path):
    assert slugify("Nike Hoodie Größe M!") == "nike-hoodie-groesse-m"
    assert slugify("") == "produkt"
    assert is_image("x.JPG") and not is_image("x.txt")
    (tmp_path / "a.jpg").write_bytes(b"x")
    assert unique_path(tmp_path / "a.jpg").name == "a-2.jpg"
    (tmp_path / "sub").mkdir()
    Image.new("RGB", (10, 10)).save(tmp_path / "sub" / "c.png")
    found = collect_images([tmp_path])
    assert any(p.name == "c.png" for p in found)
