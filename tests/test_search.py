
import pytest
from geopy.exc import GeocoderTimedOut
from PySide6.QtCore import Qt

from otripy import main
from otripy.main import MapApp


class FakeGeocoder:
    def __init__(self, results=(), error=None):
        self.results, self.error, self.queries = list(results), error, []

    def geocode(self, query, exactly_one=True):
        self.queries.append(query)
        if self.error:
            raise self.error
        return self.results or None

    def reverse(self, query):
        return None



class Place:
    def __init__(self, address, latitude, longitude):
        self.address, self.latitude, self.longitude = address, latitude, longitude

    def __str__(self):
        return self.address


@pytest.fixture
def window(qtbot, monkeypatch):
    errors = []
    monkeypatch.setattr(main.QMessageBox, "critical", lambda parent, title, text: errors.append(text))
    monkeypatch.setattr(main.QMessageBox, "question", lambda *a, **k: main.QMessageBox.Discard)
    window = MapApp()
    qtbot.addWidget(window)
    monkeypatch.setattr(window.map_page, "setHtml", lambda html: None)
    monkeypatch.setattr(window.map_page, "runJavaScript", lambda code: None)
    window.errors = errors
    return window


def search(window, text):
    window.search_entry.setText(text)
    window.search_location()
    popup = window.search_popup
    return [popup.item(i).text() for i in range(popup.count())]


def test_search_lists_results_and_adds_selected(window):
    window.geolocator = FakeGeocoder([Place("Louvre, Paris", 48.8606, 2.3376), Place("Louvre-Lens", 50.43, 2.80)])
    assert search(window, "  Louvre ") == ["Louvre, Paris", "Louvre-Lens"]
    assert window.geolocator.queries == ["Louvre"]
    popup = window.search_popup
    popup.itemClicked.emit(popup.item(1))
    [loc] = window.list_widget.locations()
    assert (loc.lat, loc.lon) == (50.43, 2.80)
    assert not popup.isVisible()


def test_search_without_result(window):
    window.geolocator = FakeGeocoder()
    assert search(window, "nowhere at all") == ["<No Result>"]
    window.search_popup.itemClicked.emit(window.search_popup.item(0))
    assert len(window.list_widget.locations()) == 0


def test_empty_search_does_not_query(window):
    window.geolocator = FakeGeocoder()
    search(window, "   ")
    assert window.geolocator.queries == []
    assert not window.search_popup.isVisible()


def test_search_error_is_reported(window):
    window.geolocator = FakeGeocoder(error=GeocoderTimedOut("timed out"))
    search(window, "Louvre")
    assert window.errors
    assert not window.search_popup.isVisible()


def test_escape_closes_popup(window, qtbot):
    window.geolocator = FakeGeocoder([Place("Louvre, Paris", 48.8606, 2.3376)])
    search(window, "Louvre")
    qtbot.keyClick(window.search_popup, Qt.Key_Escape)
    assert not window.search_popup.isVisible()
