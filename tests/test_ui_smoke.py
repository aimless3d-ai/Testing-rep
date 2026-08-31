"""Headless UI smoke tests – they run with Qt's offscreen platform plugin."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtWidgets import QApplication  # noqa: E402

from vinted_tool.models.enums import ListingStatus  # noqa: E402


@pytest.fixture(autouse=True)
def no_modal_dialogs(monkeypatch):
    """Modal message boxes would block a headless run – answer them automatically."""
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **kw: None))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **kw: None))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **kw: None))
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.Yes),
    )


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def window(qapp, context):
    try:
        from vinted_tool.ui.main_window import MainWindow
    except ImportError as exc:  # pragma: no cover - missing Qt system libs
        pytest.skip(f"Qt-Bibliotheken nicht verfügbar: {exc}")
    win = MainWindow(context)
    yield win
    # clear the editor so closing does not open the "save draft?" dialog
    win.new_listing.editor.image_strip.clear()
    win.new_listing.editor.listing.images = []
    win.close()


def test_every_page_opens(window):
    for key in ("dashboard", "new", "batch", "drafts", "history", "templates", "settings"):
        window.navigate(key)
        assert window.stack.currentWidget() is window.pages[key]


def test_full_editor_workflow(window, context, make_image, qapp):
    editor = window.new_listing.editor
    editor.reload_templates()
    editor.add_image_files([make_image("nike_hoodie_1.jpg"), make_image("nike_hoodie_2.jpg")])
    assert len(editor.image_strip.images) == 2

    editor.run_analysis(offline=True)
    editor._worker.wait(15000)
    qapp.processEvents()

    assert editor.title_input.text()
    assert editor.category_combo.currentText()
    assert editor.price_input.value() > 0
    assert "Empfohlen" in editor.btn_price_reco.text()

    editor.size_combo.setCurrentText("M")
    editor.condition_combo.setCurrentText("Sehr gut")
    result = editor._refresh_validation()
    assert result.is_publishable

    saved = editor.save_draft()
    assert saved.id is not None
    assert saved.status == ListingStatus.DRAFT.value

    window.drafts.refresh()
    assert window.drafts.table.rowCount() == 1


def test_image_strip_actions(window, make_image):
    editor = window.new_listing.editor
    editor.reset()
    editor.add_image_files([make_image("a.jpg"), make_image("b.jpg"), make_image("c.jpg")])
    strip = editor.image_strip
    strip.list.setCurrentRow(2)
    strip._make_primary()
    assert strip.images[2].is_primary
    strip._move(-1)
    assert strip.images[1].is_primary
    strip.list.setCurrentRow(0)
    strip._delete()
    assert len(strip.images) == 2


def test_price_buttons_apply_the_suggestion(window, make_image):
    editor = window.new_listing.editor
    editor.reset()
    editor.add_image_files([make_image("nike_hoodie_1.jpg")])
    editor.category_combo.setCurrentText("Damen > Kleidung > Pullover & Sweatshirts > Hoodies")
    editor.condition_combo.setCurrentText("Sehr gut")
    editor.recalculate_price()
    editor._apply_price("quick")
    assert editor.price_input.value() == editor.listing.price_suggestion.quick
    editor._apply_price("high")
    assert editor.price_input.value() == editor.listing.price_suggestion.high


def test_templates_page_preview(window):
    page = window.templates
    page.refresh()
    page.body_input.setPlainText("{{brand}} {{product}} {{unbekannt}}")
    page.update_preview()
    assert "Nike Hoodie" in page.preview.toPlainText()
    assert "unbekannt" in page.warning_label.text()


def test_settings_page_saves_values(window, context):
    page = window.settings_page
    page.refresh()
    page.currency_combo.setCurrentText("CHF")
    page.api_key_input.setText("sk-or-v1-testkey12345")
    page.save()
    assert context.settings.currency == "CHF"
    assert context.settings_service.get_api_key(context.settings.provider_kind) \
        == "sk-or-v1-testkey12345"


def test_batch_page_preview_and_run(window, context, make_image, qapp):
    page = window.batch
    page.add_paths([make_image("kleid_1.jpg"), make_image("kleid_2.jpg"), make_image("hose_1.jpg")])
    page.mode_combo.setCurrentIndex(1)  # group by file name
    page._update_preview()
    assert "2 Produkt" in page.preview_label.text()

    page.use_ai_check.setChecked(False)
    page.start()
    page._worker.wait(30000)
    qapp.processEvents()
    assert page.result_table.rowCount() == 2


def test_dashboard_counters(window, context, make_image):
    from vinted_tool.models.listing import Listing

    context.listing_repo.save(Listing(title="A", status=ListingStatus.PUBLISHED.value))
    window.dashboard.refresh()
    assert window.dashboard.stat_total.value_label.text() != "0"
    assert window.dashboard.recent_list.count() >= 1
