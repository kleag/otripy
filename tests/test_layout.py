import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QCloseEvent

from otripy import main
from otripy.main import MapApp


@pytest.fixture
def make_window(qtbot, monkeypatch):
    monkeypatch.setattr(main.QMessageBox, "question", lambda *a, **k: main.QMessageBox.Discard)

    def make():
        window = MapApp()
        qtbot.addWidget(window)
        monkeypatch.setattr(window.map_page, "setHtml", lambda html: None)
        monkeypatch.setattr(window.map_page, "runJavaScript", lambda code: None)
        window.resize(1000, 700)
        window.show()
        return window
    return make


def test_panels_are_resizable(make_window):
    """Issue #29: the list and note panels are in splitters, which cannot hide them."""
    window = make_window()
    assert window.main_splitter.orientation() == Qt.Horizontal
    assert window.main_splitter.widget(0).isAncestorOf(window.list_widget)
    assert window.main_splitter.widget(1).isAncestorOf(window.map_view)
    assert window.map_splitter.orientation() == Qt.Vertical
    assert window.map_splitter.widget(0) is window.map_view
    assert window.map_splitter.widget(1).isAncestorOf(window.note_input)
    for splitter in (window.main_splitter, window.map_splitter):
        assert not splitter.childrenCollapsible()
    assert window.list_widget.maximumWidth() > 300
    assert window.note_input.maximumHeight() > 200


def test_panel_sizes_are_remembered(make_window):
    window = make_window()
    window.main_splitter.setSizes([400, 600])
    window.map_splitter.setSizes([300, 350])
    wanted = (window.main_splitter.sizes(), window.map_splitter.sizes())
    window.closeEvent(QCloseEvent())
    assert QSettings("Kleag", "Otripy").contains("window/mainSplitter")

    again = make_window()
    assert (again.main_splitter.sizes(), again.map_splitter.sizes()) == wanted
