import pytest
from PySide6.QtWidgets import QMessageBox

from otripy import main, routing
from otripy.distance_dialog import DistanceDialog
from otripy.journey import Journey
from otripy.location import Location
from otripy.main import MapApp
from otripy.routing import Route, RoutingError

EIFFEL = Location(48.8584, 2.2945, {"markdown": "# Tour Eiffel"}, id="eiffel")
LOUVRE = Location(48.8606, 2.3376, {"markdown": "# Louvre"}, id="louvre")
OPERA = Location(48.8720, 2.3316, {"markdown": "# Opéra"}, id="opera")


class FakeRouting:
    def __init__(self, error=None):
        self.calls, self.error = [], error

    def __call__(self, points, mode):
        self.calls.append((list(points), mode))
        if self.error:
            raise RoutingError(self.error)
        return Route(distance=4304, duration=634, legs=[(4304, 634)] * (len(points) - 1),
                     geometry=[points[0], (48.86, 2.31), points[-1]])


def test_distance_dialog(qtbot):
    """Issue #6: straight distance at once, route length and duration on demand."""
    fake = FakeRouting()
    dialog = DistanceDialog([EIFFEL, LOUVRE, OPERA], first=0, fetch_route=fake)
    qtbot.addWidget(dialog)
    assert (dialog.from_box.currentText(), dialog.to_box.currentText()) == ("Tour Eiffel", "Louvre")
    assert dialog.straight_label.text() == "3.2 km"
    assert fake.calls == [], "no request until asked"
    dialog.mode_box.setCurrentIndex(list(routing.MODES).index("foot"))
    dialog.route_button.click()
    assert fake.calls == [([EIFFEL.location(), LOUVRE.location()], "foot")]
    assert dialog.route_label.text() == "4.3 km, 11 min"
    dialog.to_box.setCurrentIndex(2)
    assert dialog.route_label.text() == "", "the route of other locations is cleared"


def test_distance_dialog_errors(qtbot):
    dialog = DistanceDialog([EIFFEL, LOUVRE], fetch_route=FakeRouting(error="No route found: Impossible route"))
    qtbot.addWidget(dialog)
    dialog.route_button.click()
    assert dialog.route_label.text() == "No route found: Impossible route"
    dialog.to_box.setCurrentIndex(0)
    dialog.route_button.click()
    assert dialog.route_label.text() == "Choose two different locations."


@pytest.fixture
def window(qtbot, monkeypatch):
    monkeypatch.setattr(main.QMessageBox, "question", lambda *a, **k: QMessageBox.Discard)
    messages = []
    monkeypatch.setattr(main.QMessageBox, "critical", lambda parent, title, text: messages.append(text))
    monkeypatch.setattr(main.QMessageBox, "information", lambda parent, title, text: messages.append(text))
    window = MapApp()
    qtbot.addWidget(window)
    window.pages = []
    monkeypatch.setattr(window.map_page, "setHtml", window.pages.append)
    monkeypatch.setattr(window.map_page, "runJavaScript", lambda code: None)
    window.messages = messages
    window.set_journey(Journey([EIFFEL, LOUVRE, OPERA]), None)
    window.fake_routing = FakeRouting()
    monkeypatch.setattr(main.routing, "fetch_route", window.fake_routing)
    window.modes = []  # answers of the mode menu, None to cancel
    monkeypatch.setattr(window, "choose_leg_mode", lambda start, end: window.modes.pop(0) if window.modes else None)
    return window


def select(window, entry):
    window.list_widget.select_entry(entry)
    window.on_entry_selected(entry)


def test_shift_click_on_marker_adds_a_route(window):
    """Issue #50: select a place, Shift-click another, choose the mode."""
    select(window, EIFFEL)
    window.modes.append("foot")
    window.map_bridge.on_marker_shift_clicked(LOUVRE.lid)
    [leg] = window.list_widget.locations().legs
    assert (leg.start, leg.end, leg.mode) == (EIFFEL.lid, LOUVRE.lid, "foot")
    assert window.fake_routing.calls == [([EIFFEL.location(), LOUVRE.location()], "foot")]
    assert window.list_widget.current_entry() is EIFFEL, "the selection stays on the first place"
    assert "L.polyline" in window.pages[-1]
    assert window.dirty


def test_each_leg_has_its_own_mode(window):
    select(window, EIFFEL)
    window.modes += ["car", "bike"]
    window.map_bridge.on_marker_shift_clicked(LOUVRE.lid)
    select(window, LOUVRE)
    window.map_bridge.on_marker_shift_clicked(OPERA.lid)
    assert [(leg.start, leg.mode) for leg in window.list_widget.locations().legs] == [
        (EIFFEL.lid, "car"), (LOUVRE.lid, "bike")]
    assert "Routes: 2, 8.6 km, 21 min" in window.route_label.text()
    assert "fixthemap" in window.route_label.text(), "the routing service requires its attribution"


def test_cancelled_mode_menu_adds_nothing(window):
    select(window, EIFFEL)
    window.map_bridge.on_marker_shift_clicked(LOUVRE.lid)
    assert window.list_widget.locations().legs == []
    assert window.fake_routing.calls == []


def test_shift_click_needs_a_selected_place(window):
    select(window, window.list_widget.locations().notes)
    window.modes.append("car")
    window.map_bridge.on_marker_shift_clicked(LOUVRE.lid)
    assert window.list_widget.locations().legs == []
    assert "Shift-click" in window.statusBar().currentMessage()


def test_shift_click_in_the_list_adds_a_route(window, qtbot):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    window.resize(1000, 700)
    window.show()
    select(window, EIFFEL)
    window.modes.append("bike")
    view = window.list_widget
    QTest.mouseClick(view.viewport(), Qt.LeftButton, Qt.ShiftModifier,
                     view.visualRect(view.model.index(view.model.findRowById(OPERA.lid), 0)).center())
    [leg] = window.list_widget.locations().legs
    assert (leg.start, leg.end, leg.mode) == (EIFFEL.lid, OPERA.lid, "bike")
    assert view.current_entry() is EIFFEL


def test_route_popup_changes_mode_or_removes(window):
    select(window, EIFFEL)
    window.modes.append("car")
    window.map_bridge.on_marker_shift_clicked(LOUVRE.lid)
    [leg] = window.list_widget.locations().legs
    window.map_bridge.on_leg_action(leg.leg_id, "foot")
    [leg] = window.list_widget.locations().legs
    assert leg.mode == "foot", "the route is replaced, not duplicated"
    window.map_bridge.on_leg_action(leg.leg_id, "remove")
    assert window.list_widget.locations().legs == []
    assert "L.polyline" not in window.pages[-1]
    assert window.route_label.text() == ""


def test_remove_all_routes(window):
    select(window, EIFFEL)
    window.modes += ["car", "car"]
    window.map_bridge.on_marker_shift_clicked(LOUVRE.lid)
    window.map_bridge.on_marker_shift_clicked(OPERA.lid)
    assert window.remove_routes_action.isEnabled()
    window.remove_routes_action.trigger()
    assert window.list_widget.locations().legs == []
    assert not window.remove_routes_action.isEnabled()


def test_deleting_a_place_removes_its_routes(window):
    select(window, EIFFEL)
    window.modes.append("car")
    window.map_bridge.on_marker_shift_clicked(LOUVRE.lid)
    select(window, LOUVRE)
    window.delete_item()
    assert window.list_widget.locations().legs == []
    assert "L.polyline" not in window.pages[-1]


def test_route_errors_are_reported(window, monkeypatch):
    monkeypatch.setattr(main.routing, "fetch_route", FakeRouting(error="The routing server could not be reached"))
    select(window, EIFFEL)
    window.modes.append("foot")
    window.map_bridge.on_marker_shift_clicked(LOUVRE.lid)
    assert window.messages == ["The routing server could not be reached"]
    assert window.list_widget.locations().legs == []


def test_distances_need_two_locations(window):
    window.set_journey(Journey([EIFFEL]), None)
    window.open_distance_dialog()
    assert len(window.messages) == 1
