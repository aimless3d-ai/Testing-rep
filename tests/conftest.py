from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    """Every test runs against its own throw-away data directory."""
    target = tmp_path / "appdata"
    target.mkdir()
    monkeypatch.setenv("VINTED_TOOL_DATA_DIR", str(target))
    return target


@pytest.fixture
def context(data_dir):
    from vinted_tool.app.context import AppContext

    ctx = AppContext(db_path=data_dir / "test.sqlite3")
    yield ctx
    ctx.close()


@pytest.fixture
def make_image(tmp_path):
    def _make(name: str = "produkt.jpg", color=(30, 30, 34), size=(800, 1000)) -> Path:
        path = tmp_path / name
        Image.new("RGB", size, color).save(path)
        return path

    return _make
