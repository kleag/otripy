import pytest
from PySide6.QtCore import QModelIndex, Qt

from otripy.journey import Journey
from otripy.location import Location
from otripy.location_list_view import LocationListModel, LocationListView


def make_model(*names):
    return LocationListModel(Journey([Location(note={"markdown": f"# {n}"}, id=n) for n in names]))


def names(model):
    return [loc.lid for loc in model.get_locations()]


def drag(model, row, to_row=-1, onto=None):
    """Simulate an internal drag of `row`, dropped between items at `to_row` or onto the item at `onto`."""
    data = model.mimeData([model.index(row, 0)])
    parent = model.index(onto, 0) if onto is not None else QModelIndex()
    return model.dropMimeData(data, Qt.MoveAction, to_row, 0, parent)


def test_display_role_is_label():
    model = make_model("a")
    assert model.data(model.index(0, 0), Qt.DisplayRole) == "a"
    assert model.data(model.index(5, 0), Qt.DisplayRole) is None


def test_add_and_delete(qtbot):
    model = make_model("a", "b")
    with qtbot.waitSignal(model.rowsInserted):
        model.addLocation(Location(id="c"))
    assert names(model) == ["a", "b", "c"]
    with qtbot.waitSignal(model.rowsRemoved):
        model.delete_item(model.index(1, 0))
    assert names(model) == ["a", "c"]


def test_find_by_id():
    model = make_model("a", "b")
    assert model.findRowById("b") == 1
    assert model.findRowById("zz") == -1
    assert model.get_location_by_id("a").lid == "a"


def test_update_note_marks_journey_dirty(qtbot):
    view = LocationListView()
    view.setLocations(Journey([Location(id="a")]))
    with qtbot.waitSignal(view.model.locations.dirty):
        view.updateLocationNoteAtIndex(view.model.index(0, 0), {"markdown": "# New title"})
    assert view.model.data(view.model.index(0, 0), Qt.DisplayRole) == "New title"


@pytest.mark.parametrize("row, to_row, expected", [
    (0, 2, ["b", "a", "c"]),   # down, dropped between b and c
    (0, 3, ["b", "c", "a"]),   # down, dropped after the last item
    (2, 0, ["c", "a", "b"]),   # up, dropped before the first item
    (2, 1, ["a", "c", "b"]),   # up, dropped between a and b
])
def test_drop_between_items(row, to_row, expected):
    model = make_model("a", "b", "c")
    assert drag(model, row, to_row=to_row)
    assert names(model) == expected


@pytest.mark.parametrize("row, onto, expected", [
    (0, 2, ["b", "c", "a"]),
    (2, 0, ["c", "a", "b"]),
])
def test_drop_onto_item_takes_its_place(row, onto, expected):
    model = make_model("a", "b", "c")
    assert drag(model, row, onto=onto)
    assert names(model) == expected


def test_drop_on_empty_area_moves_to_end():
    model = make_model("a", "b", "c")
    assert drag(model, 0)
    assert names(model) == ["b", "c", "a"]


@pytest.mark.parametrize("to_row", [1, 2])
def test_drop_in_place_changes_nothing(to_row):
    model = make_model("a", "b", "c")
    assert not drag(model, 1, to_row=to_row)
    assert names(model) == ["a", "b", "c"]


def test_model_keeps_the_given_empty_journey():
    journey = Journey()
    assert LocationListModel(journey).get_locations() is journey


def styled_model(marker=None, color=None):
    return LocationListModel(Journey([Location(note={"markdown": "# a"}, id="a", marker=marker, color=color)]))


def is_blank(icon):
    image = icon.pixmap(32, 32).toImage()
    return all(image.pixelColor(x, y).alpha() == 0 for x in range(image.width()) for y in range(image.height()))


def test_default_marker_has_blank_list_icon(qapp):
    model = styled_model()
    assert is_blank(model.data(model.index(0, 0), Qt.DecorationRole))


def test_custom_marker_icon_in_list_color(qapp):
    """Issue #27: custom markers show their icon, in their color, in the list."""
    model = styled_model("bed", "red")
    icon = model.data(model.index(0, 0), Qt.DecorationRole)
    assert icon is not None and not icon.isNull()
    image = icon.pixmap(32, 32).toImage()
    colors = {image.pixelColor(x, y).name() for x in range(image.width()) for y in range(image.height())
              if image.pixelColor(x, y).alpha() == 255}
    assert colors == {"#ff0000"}


def test_unknown_marker_icon_is_blank(qapp):
    model = styled_model("no-such-icon")
    assert is_blank(model.data(model.index(0, 0), Qt.DecorationRole))


def test_marker_style_change_marks_journey_modified(qtbot):
    view = LocationListView()
    view.setLocations(Journey([Location(id="a")]))
    index = view.model.index(0, 0)
    with qtbot.waitSignal(view.model.locations.dirty) as dirty:
        view.model.setMarkerStyle(index, marker="star")
    assert dirty.args == [True]
    view.model.setMarkerStyle(index, color="purple")
    location = view.model.getLocation(index)
    assert (location.marker, location.color) == ("star", "purple")
