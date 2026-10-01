import re

import pytest
from PySide6.QtCore import QMimeData
from PySide6.QtGui import QImage, QTextCursor

from otripy.journey import Journey
from otripy.note_widget import NoteWidget

IMAGE_REF = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def image_refs(note):
    return IMAGE_REF.findall(note["markdown"])


def red_image():
    image = QImage(8, 8, QImage.Format_RGB32)
    image.fill(0xFF0000)
    return image


@pytest.fixture
def widget(qtbot):
    widget = NoteWidget()
    qtbot.addWidget(widget)
    return widget


def move_cursor_to_end(widget):
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.End)
    widget.setTextCursor(cursor)


def paste_image(widget):
    move_cursor_to_end(widget)
    mime = QMimeData()
    mime.setImageData(red_image())
    widget.insertFromMimeData(mime)


def select_last_character(widget):
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.End)
    cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor)
    widget.setTextCursor(cursor)


def cut(widget):
    mime = widget.createMimeDataFromSelection()
    widget.textCursor().removeSelectedText()
    return mime


def test_markdown_round_trip(widget):
    widget.from_note({"markdown": "# Title\n\nSome **bold** text\n\n- item\n"})
    note = widget.to_note()
    assert note["markdown"].startswith("# Title")
    assert "**bold**" in note["markdown"]
    assert note["images"] == {}


def test_note_without_markdown_warns(widget, monkeypatch):
    warnings = []
    monkeypatch.setattr("otripy.note_widget.QMessageBox.warning", lambda *args: warnings.append(args))
    widget.from_note({"images": {}})
    assert warnings


def test_fixture_images_round_trip(widget, fixture_text):
    journey = Journey.from_json_str(fixture_text("journey-with-images.json"))
    for loc in journey:
        widget.from_note(loc.note)
        note = widget.to_note()
        assert sorted(image_refs(note)) == sorted(loc.note["images"])
        assert sorted(note["images"]) == sorted(loc.note["images"])


def test_pasted_image_is_saved(widget):
    widget.from_note({"markdown": "Title\n\nbody"})
    paste_image(widget)
    note = widget.to_note()
    [ref] = image_refs(note)
    assert list(note["images"]) == [ref]


def test_pasted_image_does_not_clash_with_loaded_images(widget, fixture_text):
    """A new image must not reuse the name of an image already in the note."""
    journey = Journey.from_json_str(fixture_text("journey-with-images.json"))
    widget.from_note(journey[1].note)  # has dropped_image_1 and dropped_image_2
    paste_image(widget)
    note = widget.to_note()
    assert len(image_refs(note)) == 3
    assert len(note["images"]) == 3


def test_deleted_image_is_not_saved_or_restored(widget):
    widget.from_note({"markdown": "Title\n\nbody"})
    paste_image(widget)
    select_last_character(widget)
    widget.textCursor().removeSelectedText()
    note = widget.to_note()
    assert image_refs(note) == []
    assert note["images"] == {}
    widget.from_note(note)
    assert image_refs(widget.to_note()) == []


def test_image_moved_within_note_is_not_duplicated(widget):
    widget.from_note({"markdown": "Title\n\nbody"})
    paste_image(widget)
    select_last_character(widget)
    mime = cut(widget)
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.Start)
    widget.setTextCursor(cursor)
    widget.insertFromMimeData(mime)
    note = widget.to_note()
    assert len(image_refs(note)) == 1
    assert list(note["images"]) == image_refs(note)


def test_image_moved_to_another_note(widget):
    """Issue #21: the app reuses one NoteWidget for all locations."""
    widget.from_note({"markdown": "Note A\n\nbody"})
    paste_image(widget)
    select_last_character(widget)
    mime = cut(widget)
    note_a = widget.to_note()

    widget.from_note({"markdown": "Note B\n\ntext"})
    move_cursor_to_end(widget)
    widget.insertFromMimeData(mime)
    note_b = widget.to_note()

    assert note_a["images"] == {}
    assert len(image_refs(note_b)) == 1
    assert list(note_b["images"]) == image_refs(note_b)
    widget.from_note(note_a)
    assert image_refs(widget.to_note()) == []


def point_at(widget, text):
    """Viewport position in the middle of the first occurrence of text."""
    from PySide6.QtGui import QTextDocument as Doc
    cursor = widget.document().find(text, 0, Doc.FindFlags())
    middle = widget.textCursor()
    middle.setPosition((cursor.selectionStart() + cursor.selectionEnd()) // 2)
    return widget.cursorRect(middle).center()


@pytest.fixture
def opened(monkeypatch):
    urls = []
    monkeypatch.setattr("otripy.note_widget.QDesktopServices.openUrl", lambda url: urls.append(url.toString()))
    return urls


@pytest.mark.parametrize("markdown, target, url", [
    ("See [the museum](https://www.louvre.fr/en) now", "the museum", "https://www.louvre.fr/en"),
    ("Tickets at https://example.org/tickets.", "example.org", "https://example.org/tickets"),
    ("Or www.example.org/plan (map)", "example.org", "http://www.example.org/plan"),
])
def test_ctrl_click_opens_links(widget, opened, markdown, target, url):
    """Issue #5: Ctrl+click opens links and web addresses in notes."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    widget.from_note({"markdown": markdown})
    widget.resize(600, 200)
    widget.show()
    QTest.mouseClick(widget.viewport(), Qt.LeftButton, Qt.ControlModifier, point_at(widget, target))
    assert opened == [url]


def test_plain_click_on_link_only_moves_cursor(widget, opened):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    widget.from_note({"markdown": "Tickets at https://example.org/tickets"})
    widget.resize(600, 200)
    widget.show()
    QTest.mouseClick(widget.viewport(), Qt.LeftButton, Qt.NoModifier, point_at(widget, "example"))
    assert opened == []
    assert widget.textCursor().position() > 0


def test_ctrl_click_outside_links_opens_nothing(widget, opened):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    widget.from_note({"markdown": "No link here https://example.org"})
    widget.resize(600, 200)
    widget.show()
    QTest.mouseClick(widget.viewport(), Qt.LeftButton, Qt.ControlModifier, point_at(widget, "link"))
    assert opened == []


def test_ctrl_click_opens_typed_address(widget, opened):
    """Addresses typed in the editor are plain text until the note is reloaded."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    widget.from_note({"markdown": "Title"})
    widget.resize(600, 200)
    widget.show()
    move_cursor_to_end(widget)
    widget.textCursor().insertText(" see www.example.org/typed, then")
    assert not widget.anchorAt(point_at(widget, "example"))
    QTest.mouseClick(widget.viewport(), Qt.LeftButton, Qt.ControlModifier, point_at(widget, "example"))
    assert opened == ["http://www.example.org/typed"]
