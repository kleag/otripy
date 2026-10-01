import pytest
from PySide6.QtCore import QModelIndex, Qt

from otripy.journey import Journey
from otripy.location import Group, Location
from otripy.location_list_view import INDENT_ROLE, LocationListModel, LocationListView

# Row 0 is the trip's notes: location i of an ungrouped journey is at row i + 1
FIRST = 1


def make_model(*names):
    return LocationListModel(Journey([Location(note={"markdown": f"# {n}"}, id=n) for n in names]))


def names(model):
    return [loc.lid for loc in model.get_locations()]


def drag(model, row, to_row=-1, onto=None):
    """Simulate an internal drag of `row`, dropped between rows at `to_row` or onto the row `onto`."""
    data = model.mimeData([model.index(row, 0)])
    parent = model.index(onto, 0) if onto is not None else QModelIndex()
    return model.dropMimeData(data, Qt.MoveAction, to_row, 0, parent)


def loc_drag(model, position, to_position=-1, onto=None):
    """drag() with location positions of an ungrouped journey instead of rows."""
    return drag(model, position + FIRST, to_position + FIRST if to_position != -1 else -1,
                onto + FIRST if onto is not None else None)


def rows(model):
    """Each row as text: the trip's notes, group titles and location ids."""
    return [model.data(model.index(r, 0), Qt.DisplayRole) if not model.getLocation(model.index(r, 0))
            else model.getLocation(model.index(r, 0)).lid for r in range(model.rowCount())]


def test_display_role_is_label():
    model = make_model("a")
    assert model.data(model.index(FIRST, 0), Qt.DisplayRole) == "a"
    assert model.data(model.index(5, 0), Qt.DisplayRole) is None


def test_trip_notes_come_first(qapp):
    """Issue #19: the first row holds the trip's general notes."""
    model = make_model("a")
    assert model.data(model.index(0, 0), Qt.DisplayRole) == "Trip notes"
    assert model.getEntry(model.index(0, 0)) is model.locations.notes
    assert model.getLocation(model.index(0, 0)) is None
    assert not model.flags(model.index(0, 0)) & Qt.ItemIsDragEnabled


def test_add_and_delete(qtbot):
    model = make_model("a", "b")
    with qtbot.waitSignal(model.modelReset):
        model.addLocation(Location(id="c"))
    assert names(model) == ["a", "b", "c"]
    with qtbot.waitSignal(model.rowsRemoved):
        model.delete_item(model.index(1 + FIRST, 0))
    assert names(model) == ["a", "c"]


def test_trip_notes_cannot_be_deleted():
    model = make_model("a")
    model.delete_item(model.index(0, 0))
    assert model.rowCount() == 2


def test_find_by_id():
    model = make_model("a", "b")
    assert model.findRowById("b") == 1 + FIRST
    assert model.findRowById("zz") == -1
    assert model.get_location_by_id("a").lid == "a"


def test_update_note_marks_journey_dirty(qtbot):
    view = LocationListView()
    view.setLocations(Journey([Location(id="a")]))
    with qtbot.waitSignal(view.model.locations.dirty):
        view.updateLocationNoteAtIndex(view.model.index(FIRST, 0), {"markdown": "# New title"})
    assert view.model.data(view.model.index(FIRST, 0), Qt.DisplayRole) == "New title"


def test_trip_notes_can_be_edited(qtbot):
    view = LocationListView()
    view.setLocations(Journey([Location(id="a")]))
    with qtbot.waitSignal(view.model.locations.dirty):
        view.updateLocationNoteAtIndex(view.model.index(0, 0), {"markdown": "# Trip\n\nVisa", "images": {}})
    assert view.model.locations.notes.preview() == "Visa"


@pytest.mark.parametrize("row, to_row, expected", [
    (0, 2, ["b", "a", "c"]),   # down, dropped between b and c
    (0, 3, ["b", "c", "a"]),   # down, dropped after the last item
    (2, 0, ["c", "a", "b"]),   # up, dropped before the first item
    (2, 1, ["a", "c", "b"]),   # up, dropped between a and b
])
def test_drop_between_items(row, to_row, expected):
    model = make_model("a", "b", "c")
    assert loc_drag(model, row, to_position=to_row)
    assert names(model) == expected


@pytest.mark.parametrize("row, onto, expected", [
    (0, 2, ["b", "c", "a"]),
    (2, 0, ["c", "a", "b"]),
])
def test_drop_onto_item_takes_its_place(row, onto, expected):
    model = make_model("a", "b", "c")
    assert loc_drag(model, row, onto=onto)
    assert names(model) == expected


def test_drop_on_empty_area_moves_to_end():
    model = make_model("a", "b", "c")
    assert loc_drag(model, 0)
    assert names(model) == ["b", "c", "a"]


@pytest.mark.parametrize("to_row", [1, 2])
def test_drop_in_place_changes_nothing(to_row):
    model = make_model("a", "b", "c")
    assert not loc_drag(model, 1, to_position=to_row)
    assert names(model) == ["a", "b", "c"]


def test_nothing_goes_above_trip_notes():
    model = make_model("a", "b")
    assert drag(model, 2, to_row=0)
    assert rows(model) == ["Trip notes", "b", "a"]
    assert not drag(model, 0, to_row=3), "the trip's notes do not move"


def test_model_keeps_the_given_empty_journey():
    journey = Journey()
    assert LocationListModel(journey).get_locations() is journey


# Groups (issue #18)

def grouped_model():
    """Rows: Trip notes, u, Day 1, a, b, Day 2, c."""
    days = [Group({"markdown": "# Day 1"}, id="g1"), Group({"markdown": "# Day 2"}, id="g2")]
    locations = [Location(note={"markdown": "# u"}, id="u"),
                 Location(note={"markdown": "# a"}, id="a", group="g1"),
                 Location(note={"markdown": "# b"}, id="b", group="g1"),
                 Location(note={"markdown": "# c"}, id="c", group="g2")]
    return LocationListModel(Journey(locations, groups=days))


def groups_of(model):
    return {loc.lid: loc.group for loc in model.get_locations()}


def test_group_rows():
    model = grouped_model()
    assert rows(model) == ["Trip notes", "u", "▾ Day 1 (2)", "a", "b", "▾ Day 2 (1)", "c"]
    assert model.data(model.index(3, 0), INDENT_ROLE) is True
    assert not model.data(model.index(1, 0), INDENT_ROLE)
    assert model.data(model.index(2, 0), Qt.FontRole).bold()


def test_location_dropped_in_a_group_joins_it(qtbot):
    model = grouped_model()
    with qtbot.waitSignal(model.arranged):
        assert drag(model, 1, to_row=4)  # u, between a and b
    assert rows(model) == ["Trip notes", "▾ Day 1 (3)", "a", "u", "b", "▾ Day 2 (1)", "c"]
    assert groups_of(model)["u"] == "g1"


def test_location_dropped_under_a_group_title_comes_first_in_it():
    model = grouped_model()
    assert drag(model, 6, to_row=3)  # c, just under Day 1's title
    assert rows(model) == ["Trip notes", "u", "▾ Day 1 (3)", "c", "a", "b", "▾ Day 2 (0)"]
    assert groups_of(model)["c"] == "g1"


def test_location_dropped_above_groups_leaves_its_group():
    model = grouped_model()
    assert drag(model, 3, to_row=1)  # a, above u
    assert rows(model) == ["Trip notes", "a", "u", "▾ Day 1 (1)", "b", "▾ Day 2 (1)", "c"]
    assert groups_of(model)["a"] is None


def test_group_moves_with_its_locations():
    model = grouped_model()
    assert drag(model, 5, to_row=2)  # Day 2, above Day 1
    assert rows(model) == ["Trip notes", "u", "▾ Day 2 (1)", "c", "▾ Day 1 (2)", "a", "b"]
    assert [loc.lid for loc in model.get_locations()] == ["u", "c", "a", "b"], "routes follow the list"


def test_group_cannot_go_above_ungrouped_locations():
    model = grouped_model()
    assert drag(model, 5, to_row=1)  # Day 2, above u
    assert rows(model)[1] == "u"


def test_collapsing_hides_a_group_locations(qtbot):
    model = grouped_model()
    with qtbot.assertNotEmitted(model.locations.dirty):
        model.setCollapsed(model.locations.groups[0], True)
    assert rows(model) == ["Trip notes", "u", "▸ Day 1 (2)", "▾ Day 2 (1)", "c"]
    assert model.findRowById("a") == -1


def test_adding_to_a_collapsed_group_expands_it():
    model = grouped_model()
    day1 = model.locations.groups[0]
    model.setCollapsed(day1, True)
    model.addLocation(Location(note={"markdown": "# d"}, id="d"), day1)
    assert rows(model) == ["Trip notes", "u", "▾ Day 1 (3)", "a", "b", "d", "▾ Day 2 (1)", "c"]


def test_add_group_at_the_end():
    model = grouped_model()
    model.addGroup(Group({"markdown": "# Day 3"}, id="g3"))
    assert rows(model)[-1] == "▾ Day 3 (0)"


def test_deleting_a_group_keeps_its_locations(qtbot):
    model = grouped_model()
    with qtbot.waitSignal(model.locations.dirty):
        model.delete_item(model.index(2, 0))
    assert rows(model) == ["Trip notes", "u", "a", "b", "▾ Day 2 (1)", "c"]
    assert groups_of(model)["a"] is None


def test_view_keeps_selection_when_rows_change(qtbot):
    view = LocationListView()
    qtbot.addWidget(view)
    view.model.setLocations(grouped_model().locations)
    view.selectById("c")
    view.model.setCollapsed(view.model.locations.groups[0], True)
    assert view.current_entry().lid == "c"
    assert view.current_group().gid == "g2"


def test_selecting_a_location_of_a_collapsed_group_expands_it(qtbot):
    view = LocationListView()
    qtbot.addWidget(view)
    view.model.setLocations(grouped_model().locations)
    day1 = view.model.locations.groups[0]
    view.model.setCollapsed(day1, True)
    view.selectById("a")
    assert not day1.collapsed
    assert view.current_entry().lid == "a"


def test_double_click_toggles_a_group(qtbot):
    view = LocationListView()
    qtbot.addWidget(view)
    view.model.setLocations(grouped_model().locations)
    day1 = view.model.locations.groups[0]
    view.on_item_double_clicked(view.model.index(2, 0))
    assert day1.collapsed
    view.on_item_double_clicked(view.model.index(2, 0))
    assert not day1.collapsed


def test_clicks_report_entries(qtbot):
    view = LocationListView()
    qtbot.addWidget(view)
    view.model.setLocations(grouped_model().locations)
    with qtbot.waitSignal(view.entryClicked) as clicked, qtbot.assertNotEmitted(view.locationClicked):
        view.on_item_clicked(view.model.index(2, 0))
    assert clicked.args[0].gid == "g1"
    with qtbot.waitSignal(view.locationClicked) as clicked:
        view.on_item_clicked(view.model.index(3, 0))
    assert clicked.args[0].lid == "a"


# Marker icons and hovering

def styled_model(marker=None, color=None):
    return LocationListModel(Journey([Location(note={"markdown": "# a"}, id="a", marker=marker, color=color)]))


def is_blank(icon):
    image = icon.pixmap(32, 32).toImage()
    return all(image.pixelColor(x, y).alpha() == 0 for x in range(image.width()) for y in range(image.height()))


def test_default_marker_has_blank_list_icon(qapp):
    model = styled_model()
    assert is_blank(model.data(model.index(FIRST, 0), Qt.DecorationRole))


def test_custom_marker_icon_in_list_color(qapp):
    """Issue #27: custom markers show their icon, in their color, in the list."""
    model = styled_model("bed", "red")
    icon = model.data(model.index(FIRST, 0), Qt.DecorationRole)
    assert icon is not None and not icon.isNull()
    image = icon.pixmap(32, 32).toImage()
    colors = {image.pixelColor(x, y).name() for x in range(image.width()) for y in range(image.height())
              if image.pixelColor(x, y).alpha() == 255}
    assert colors == {"#ff0000"}


def test_unknown_marker_icon_is_blank(qapp):
    model = styled_model("no-such-icon")
    assert is_blank(model.data(model.index(FIRST, 0), Qt.DecorationRole))


def test_marker_style_change_marks_journey_modified(qtbot):
    view = LocationListView()
    view.setLocations(Journey([Location(id="a")]))
    index = view.model.index(FIRST, 0)
    with qtbot.waitSignal(view.model.locations.dirty) as dirty:
        view.model.setMarkerStyle(index, marker="star")
    assert dirty.args == [True]
    view.model.setMarkerStyle(index, color="purple")
    location = view.model.getLocation(index)
    assert (location.marker, location.color) == ("star", "purple")


def test_hovered_marker_highlights_list_row_without_modifying(qtbot):
    """Issue #22: hovering a marker on the map highlights its list entry."""
    view = LocationListView()
    view.setLocations(Journey([Location(id="a"), Location(id="b")]))
    model = view.model
    with qtbot.assertNotEmitted(model.locations.dirty):
        model.setHovered("b")
    assert model.data(model.index(FIRST, 0), Qt.BackgroundRole) is None
    assert model.data(model.index(1 + FIRST, 0), Qt.BackgroundRole) is not None
    model.setHovered(None)
    assert model.data(model.index(1 + FIRST, 0), Qt.BackgroundRole) is None


def test_list_tooltip_previews_note(qapp):
    model = LocationListModel(Journey([Location(note={"markdown": "# Louvre\n\nOpen 9:00"}, id="a")]))
    assert model.data(model.index(FIRST, 0), Qt.ToolTipRole) == "Louvre\nOpen 9:00"


def test_list_reports_hovered_location(qtbot):
    from PySide6.QtCore import QEvent
    from PySide6.QtTest import QTest
    view = LocationListView()
    qtbot.addWidget(view)
    view.setLocations(Journey([Location(note={"markdown": "# a"}, id="a"), Location(note={"markdown": "# b"}, id="b")]))
    view.resize(200, 200)
    view.show()
    with qtbot.waitSignal(view.locationHovered) as hovered:
        QTest.mouseMove(view.viewport(), view.visualRect(view.model.index(1 + FIRST, 0)).center())
    assert hovered.args == ["b"]
    with qtbot.waitSignal(view.locationHovered) as hovered:
        view.leaveEvent(QEvent(QEvent.Leave))
    assert hovered.args == [""]
