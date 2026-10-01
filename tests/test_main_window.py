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


def test_redrawing_keeps_the_map_view(window):
    """Edits redraw the map: it must stay where the user moved it."""
    window.geolocator = FakeGeolocator("A, Somewhere")
    window.map_bridge.on_map_clicked(48.85, 2.35)
    window.map_bridge.on_view_changed(45.5, 4.25, 9)
    window.map_bridge.on_map_clicked(50.63, 3.06)
    assert "[45.5, 4.25]" in window.rendered_pages[-1]
    assert '"zoom": 9' in window.rendered_pages[-1]


def test_new_journey_resets_the_map_view(window):
    window.map_bridge.on_view_changed(45.5, 4.25, 9)
    window.set_journey(main.Journey(), None)
    assert '"zoom": 9' not in window.rendered_pages[-1]
    assert window.map_view_state is None


def add_and_select(window):
    window.geolocator = FakeGeolocator("Somewhere, Paris")
    window.map_bridge.on_map_clicked(1.0, 2.0)
    window.set_window_title(dirty=False)
    return window.list_widget.locations()[0]


def test_changing_marker_icon_marks_trip_modified(window):
    loc = add_and_select(window)
    window.marker_chosen("bed")
    assert loc.marker == "bed"
    assert window.dirty


def test_changing_marker_color_marks_trip_modified(window, monkeypatch):
    loc = add_and_select(window)
    monkeypatch.setattr(main.LimitedColorPicker, "get_color", staticmethod(lambda: "purple"))
    window.action_marker_color_picker()
    assert loc.color == "purple"
    assert window.dirty


def test_cancelling_color_picker_keeps_color(window, monkeypatch):
    loc = add_and_select(window)
    loc.color = "red"
    monkeypatch.setattr(main.LimitedColorPicker, "get_color", staticmethod(lambda: None))
    window.action_marker_color_picker()
    assert loc.color == "red"
    assert not window.dirty


def test_map_click_adds_without_asking_by_default(window, monkeypatch):
    asked = []
    monkeypatch.setattr(main.QMessageBox, "question", lambda *a, **k: asked.append(a) or QMessageBox.No)
    window.geolocator = FakeGeolocator("Tour Eiffel, Paris")
    window.map_bridge.on_map_clicked(48.8584, 2.2945)
    assert not asked
    assert len(window.list_widget.locations()) == 1


@pytest.mark.parametrize("answer, added", [(QMessageBox.Yes, 1), (QMessageBox.No, 0)])
def test_map_click_confirmation(window, monkeypatch, answer, added):
    """Issue #30: optionally confirm, with the address, before adding a clicked location."""
    asked = []
    monkeypatch.setattr(main.QMessageBox, "question", lambda parent, title, text, *a: asked.append(text) or answer)
    window.confirm_locations_action.setChecked(True)
    window.geolocator = FakeGeolocator("Tour Eiffel, Paris")
    window.map_bridge.on_map_clicked(48.8584, 2.2945)
    assert "Tour Eiffel, Paris" in asked[0]
    assert len(window.list_widget.locations()) == added
    assert (window.lat_input.text() != "") == bool(added)


def test_confirmation_setting_is_remembered(window, qtbot):
    window.confirm_locations_action.setChecked(True)
    again = MapApp()
    qtbot.addWidget(again)
    assert again.confirm_locations_action.isChecked()
