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
    return window


def test_show_route_through_all_locations(window, monkeypatch):
    """Issue #3: the route goes through all the locations, in list order, in one request."""
    fake = FakeRouting()
    monkeypatch.setattr(main.routing, "fetch_route", fake)
    window.show_route("bike")
    assert fake.calls == [([EIFFEL.location(), LOUVRE.location(), OPERA.location()], "bike")]
    assert "L.polyline" in window.pages[-1]
    assert "Bicycle: 4.3 km, 11 min" in window.route_label.text()
    assert "fixthemap" in window.route_label.text(), "the routing service requires its attribution"
    assert window.hide_route_action.isEnabled()


def test_route_survives_redraws_until_locations_change(window, monkeypatch):
    monkeypatch.setattr(main.routing, "fetch_route", FakeRouting())
    window.show_route("car")
    window.update_map()
    assert "L.polyline" in window.pages[-1]
    window.list_widget.addLocation(Location(48.88, 2.34, id="new"))
    window.update_map()
    assert "L.polyline" not in window.pages[-1]
    assert window.route is None and not window.hide_route_action.isEnabled()


def test_hide_route(window, monkeypatch):
    monkeypatch.setattr(main.routing, "fetch_route", FakeRouting())
    window.show_route("car")
    window.hide_route()
    assert "L.polyline" not in window.pages[-1]
    assert window.route_label.text() == ""


def test_route_errors_are_reported(window, monkeypatch):
    monkeypatch.setattr(main.routing, "fetch_route", FakeRouting(error="The routing server could not be reached"))
    window.show_route("foot")
    assert window.messages == ["The routing server could not be reached"]
    assert window.route is None


def test_tools_need_two_locations(window, monkeypatch):
    fake = FakeRouting()
    monkeypatch.setattr(main.routing, "fetch_route", fake)
    window.set_journey(Journey([EIFFEL]), None)
    window.show_route("car")
    window.open_distance_dialog()
    assert len(window.messages) == 2 and fake.calls == []
