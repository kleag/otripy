from types import SimpleNamespace

import pytest
from geopy.exc import GeocoderUnavailable

from PySide6.QtWidgets import QMessageBox

from otripy import main
from otripy.main import MapApp


class FakeGeolocator:
    def __init__(self, address=None, error=None):
        self.address, self.error = address, error

    def reverse(self, query):
        if self.error:
            raise self.error
        return SimpleNamespace(address=self.address) if self.address else None


@pytest.fixture
def window(qtbot, monkeypatch):
    # Modal dialogs would block the headless test run
    monkeypatch.setattr(main.QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Discard)
    window = MapApp()
    qtbot.addWidget(window)
    window.rendered_pages, window.scripts_run = [], []
    monkeypatch.setattr(window.map_page, "setHtml", window.rendered_pages.append)
    monkeypatch.setattr(window.map_page, "runJavaScript", window.scripts_run.append)
    return window


def test_map_click_adds_location_with_address(window):
    window.geolocator = FakeGeolocator("Tour Eiffel, Avenue Anatole France, Paris")
    window.map_bridge.on_map_clicked(48.8584, 2.2945)
    [loc] = window.list_widget.locations()
    assert (loc.lat, loc.lon) == (48.8584, 2.2945)
    assert loc.label() == "Tour Eiffel"
    assert window.rendered_pages, "map should be redrawn"


@pytest.mark.parametrize("geolocator", [FakeGeolocator(), FakeGeolocator(error=GeocoderUnavailable("offline"))])
def test_unknown_place_keeps_note_editing_working(window, geolocator):
    window.geolocator = geolocator
    window.map_bridge.on_map_clicked(1.5, 2.5)
    [loc] = window.list_widget.locations()
    assert loc.label() == "Unknown place at [1.5, 2.5]"
    # The note editor must still update the selected location
    window.note_input.setPlainText("Renamed")
    assert loc.label() == "Renamed"


def test_marker_click_selects_location(window):
    window.geolocator = FakeGeolocator("A")
    window.map_bridge.on_map_clicked(1.0, 1.0)
    window.geolocator = FakeGeolocator("B")
    window.map_bridge.on_map_clicked(2.0, 2.0)
    first = window.list_widget.locations()[0]
    window.map_bridge.on_marker_clicked(first.lid)
    assert window.list_widget.currentIndex().row() == 0
    assert window.lat_input.text() == "1.0"


def test_editing_title_updates_marker_texts(window):
    """Issue #26: the marker's tooltip and popup follow the note's first line."""
    window.geolocator = FakeGeolocator("Old title, Somewhere")
    window.map_bridge.on_map_clicked(1.0, 2.0)
    [loc] = window.list_widget.locations()
    window.scripts_run.clear()
    window.note_input.setPlainText("New <title>\n\nbody")
    updates = [code for code in window.scripts_run if "setTooltipContent" in code]
    assert updates
    assert '"New <title>"' not in updates[-1], "Leaflet renders tooltips as HTML: the title must be escaped"
    assert updates[-1].count('"New &lt;title&gt;"') == 2


def test_editing_note_body_does_not_touch_marker(window):
    window.geolocator = FakeGeolocator("Title, Somewhere")
    window.map_bridge.on_map_clicked(1.0, 2.0)
    window.note_input.setPlainText("Title\n\nfirst body")
    window.scripts_run.clear()
    window.note_input.setPlainText("Title\n\nsecond body")
    assert not [code for code in window.scripts_run if "setTooltipContent" in code]
