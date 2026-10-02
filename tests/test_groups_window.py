"""Groups (issue #18) and trip notes (issue #19) in the main window."""
import json

import pytest
from PySide6.QtWidgets import QMessageBox

from otripy import main
from otripy.journey import Journey
from otripy.location import Group, Location
from otripy.main import MapApp


@pytest.fixture
def window(qtbot, monkeypatch):
    window = MapApp()
    qtbot.addWidget(window)
    window.scripts = []
    monkeypatch.setattr(window.map_page, "setHtml", lambda html: None)
    monkeypatch.setattr(window.map_page, "runJavaScript", window.scripts.append)
    window.answers = []
    monkeypatch.setattr(main.QMessageBox, "question",
                        lambda *args, **kwargs: window.answers.pop(0) if window.answers else QMessageBox.Discard)
    days = [Group({"markdown": "# Day 1"}, id="g1"), Group({"markdown": "# Day 2"}, id="g2")]
    window.set_journey(Journey([Location(48.85, 2.29, {"markdown": "# Eiffel"}, id="eiffel", group="g1"),
                                Location(48.86, 2.33, {"markdown": "# Louvre"}, id="louvre", group="g1"),
                                Location(48.88, 2.34, {"markdown": "# Montmartre"}, id="montmartre", group="g2")],
                               groups=days), None)
    return window


def select(window, entry):
    window.list_widget.select_entry(entry)
    window.on_entry_selected(entry)


def test_trip_notes_are_edited_in_the_note_editor(window, tmp_path):
    """Issue #19."""
    journey = window.list_widget.locations()
    select(window, journey.notes)
    assert window.lat_input.text() == ""
    assert not window.toolbar.marker_icon_button.isEnabled()
    assert not window.toolbar.marker_color_button.isEnabled()
    window.note_input.setPlainText("Paris trip\n\nBuy the museum pass")
    assert journey.notes.label() == "Paris trip"
    assert window.dirty
    path = tmp_path / "trip.json"
    assert window.save_local_file(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["format_version"] == "1.1.0"
    assert data["notes"]["markdown"].startswith("Paris trip")


def test_selecting_a_group_shows_its_locations(window):
    day1 = window.list_widget.locations().groups[0]
    window.scripts.clear()
    select(window, day1)
    assert "fitPoints([[48.85, 2.29], [48.86, 2.33]]);" in window.scripts
    assert not window.toolbar.marker_icon_button.isEnabled()
    window.note_input.setPlainText("Day 1: left bank")
    assert day1.label() == "Day 1: left bank"
    select(window, window.list_widget.locations()[0])
    assert window.toolbar.marker_icon_button.isEnabled()


def test_new_group_then_new_locations_join_it(window):
    window.new_group()
    journey = window.list_widget.locations()
    group = journey.groups[-1]
    assert group.label() == "New group"
    assert window.list_widget.current_entry() is group
    window.note_input.setPlainText("Day 3")
    assert group.label() == "Day 3"
    window.geolocator = type("G", (), {"reverse": lambda self, q: None})()
    window.map_bridge.on_map_clicked(48.84, 2.36)
    window.map_bridge.on_map_clicked(48.85, 2.37)
    assert [loc.lat for loc in journey.group_locations(group)] == [48.84, 48.85], \
        "locations added while the group or one of its locations is selected join it"


def test_location_added_with_trip_notes_selected_is_ungrouped(window):
    journey = window.list_widget.locations()
    select(window, journey.notes)
    window.geolocator = type("G", (), {"reverse": lambda self, q: None})()
    window.map_bridge.on_map_clicked(48.84, 2.36)
    assert [loc.lat for loc in journey.group_locations(None)] == [48.84]


@pytest.mark.parametrize("answer, deleted", [(QMessageBox.Yes, True), (QMessageBox.No, False)])
def test_deleting_a_group_asks_and_keeps_its_locations(window, answer, deleted):
    journey = window.list_widget.locations()
    day1 = journey.groups[0]
    select(window, day1)
    window.answers.append(answer)
    window.delete_item()
    assert (day1 not in journey.groups) == deleted
    assert len(journey) == 3
    if deleted:
        assert [loc.lid for loc in journey.group_locations(None)] == ["eiffel", "louvre"]


def test_trip_notes_are_never_deleted(window):
    journey = window.list_widget.locations()
    select(window, journey.notes)
    window.delete_item()
    assert window.list_widget.model.entry(0) is journey.notes
    assert len(journey.groups) == 2 and len(journey) == 3
