import io
import json

import pytest

from otripy import __version__
from otripy.journey import BASE_FORMAT_VERSION, CURRENT_FORMAT_VERSION, Journey
from otripy.location import Group, Location, TripNotes


def save_to_str(journey):
    buffer = io.StringIO()
    journey.write_to_file(buffer)
    return buffer.getvalue()


def test_load_legacy_list(fixture_text):
    journey = Journey.from_json_str(fixture_text("legacy-list.json"))
    assert len(journey) == 6
    assert journey[0].label() == "Tour Eiffel"
    assert journey[5].note == {"markdown": journey[5].note["markdown"]}
    assert all(loc.marker is None and loc.color is None for loc in journey)


def test_load_current_format(fixture_text):
    journey = Journey.from_json_str(fixture_text("journey-1.0.0.json"))
    assert [loc.marker for loc in journey] == [None, "star", "binoculars", None, "bed", "motorcycle"]
    assert [loc.color for loc in journey] == [None, None, "purple", "red", None, "darkgreen"]


def test_load_file_with_images(fixture_text):
    journey = Journey.from_json_str(fixture_text("journey-with-images.json"))
    assert [len(loc.note["images"]) for loc in journey] == [1, 2, 0]
    assert all(loc.color is None for loc in journey)


@pytest.mark.parametrize("name", ["legacy-list.json", "journey-1.0.0.json", "journey-with-images.json"])
def test_save_load_round_trip(fixture_text, name):
    journey = Journey.from_json_str(fixture_text(name))
    again = Journey.from_json_str(save_to_str(journey))
    assert [loc.to_dict() for loc in again] == [loc.to_dict() for loc in journey]


def test_saved_metadata(fixture_text):
    journey = Journey.from_json_str(fixture_text("journey-1.0.0.json"))
    data = json.loads(save_to_str(journey))
    assert data["format"] == "otripy"
    # Without groups nor trip notes, the oldest format that holds it, for older readers
    assert data["format_version"] == BASE_FORMAT_VERSION
    assert "groups" not in data and "notes" not in data
    assert data["app_version"] == __version__
    # The creation date of the loaded file is kept; the update date is refreshed.
    assert data["created_at"] == "2025-03-16T14:20:41.146103+00:00"
    assert data["updated_at"] != "2025-03-17T18:43:54.281403+00:00"


def test_new_journey_gets_creation_date():
    data = json.loads(save_to_str(Journey([Location()])))
    assert data["created_at"] == data["updated_at"]


def with_metadata(fixture_text, **changes):
    data = json.loads(fixture_text("journey-1.0.0.json"))
    data.update(changes)
    return json.dumps(data)


def test_reads_file_from_newer_app_in_known_format(fixture_text):
    """Only the format version matters: newer versions write older formats when they can."""
    journey = Journey.from_json_str(with_metadata(fixture_text, app_version="99.0.0"))
    assert len(journey) == 6


def test_refuses_newer_format(fixture_text):
    with pytest.raises(ValueError, match="format version 2.0.0"):
        Journey.from_json_str(with_metadata(fixture_text, app_version=__version__, format_version="2.0.0"))


def test_refuses_non_otripy_json():
    with pytest.raises(ValueError):
        Journey.from_json_str(json.dumps({"format": "geojson"}))


def test_mutations_emit_dirty(qtbot):
    journey = Journey()
    loc = Location()
    for mutate in (lambda: journey.append(loc),
                   lambda: journey.insert(0, Location()),
                   lambda: journey.__setitem__(0, Location()),
                   lambda: journey.remove(loc),
                   lambda: journey.__delitem__(0)):
        with qtbot.waitSignal(journey.dirty) as blocker:
            mutate()
        assert blocker.args == [True]


def test_clear_and_clean_reset_dirty(qtbot):
    journey = Journey([Location()])
    for reset in (journey.clean, journey.clear):
        with qtbot.waitSignal(journey.dirty) as blocker:
            reset()
        assert blocker.args == [False]


def test_pop_emits_dirty_later(qtbot):
    journey = Journey([Location(), Location()])
    with qtbot.waitSignal(journey.dirty) as blocker:
        journey.pop()
    assert blocker.args == [True]
    assert len(journey) == 1


def test_only_locations_accepted():
    journey = Journey()
    with pytest.raises(TypeError):
        journey.append("not a location")
    with pytest.raises(TypeError):
        journey.insert(0, {"lat": 1})


def grouped_journey():
    days = [Group({"markdown": "# Day 1"}, id="d1"), Group({"markdown": "# Day 2"}, id="d2")]
    locations = [Location(1, 1, {"markdown": "# Louvre"}, id="louvre", group="d2"),
                 Location(2, 2, {"markdown": "# Hotel"}, id="hotel"),
                 Location(3, 3, {"markdown": "# Eiffel"}, id="eiffel", group="d1")]
    return Journey(locations, groups=days, notes=TripNotes({"markdown": "# Trip\n\nPassports!", "images": {}}))


def test_locations_are_kept_in_display_order():
    """Ungrouped locations first, then each group's, in group order (issue #18)."""
    journey = grouped_journey()
    assert [loc.lid for loc in journey] == ["hotel", "eiffel", "louvre"]
    assert [loc.lid for loc in journey.group_locations(journey.groups[1])] == ["louvre"]


def test_groups_and_trip_notes_round_trip():
    journey = grouped_journey()
    data = json.loads(save_to_str(journey))
    assert data["format_version"] == CURRENT_FORMAT_VERSION == "1.1.0"
    assert [g["id"] for g in data["groups"]] == ["d1", "d2"]
    assert data["notes"]["markdown"] == "# Trip\n\nPassports!"
    again = Journey.from_json_str(json.dumps(data))
    assert [(loc.lid, loc.group) for loc in again] == [("hotel", None), ("eiffel", "d1"), ("louvre", "d2")]
    assert [g.label() for g in again.groups] == ["Day 1", "Day 2"]
    assert again.notes.label() == "Trip"


@pytest.mark.parametrize("change", ["groups", "notes"])
def test_either_addition_needs_format_1_1(change):
    journey = Journey([Location()])
    if change == "groups":
        journey.add_group(Group({"markdown": "# Day 1"}))
    else:
        journey.notes.note = {"markdown": "Visa", "images": {}}
    assert json.loads(save_to_str(journey))["format_version"] == "1.1.0"


def test_location_of_unknown_group_is_kept_ungrouped(fixture_text):
    data = json.loads(fixture_text("journey-1.1.0.json"))
    data["locations"][-1]["group"] = "no-such-group"
    journey = Journey.from_json_str(json.dumps(data))
    orphan = journey.loc_by_id(data["locations"][-1]["id"])
    assert orphan.group is None
    assert orphan in journey.group_locations(None)


def test_removing_a_group_keeps_its_locations(qtbot):
    journey = grouped_journey()
    with qtbot.waitSignal(journey.dirty):
        journey.remove_group(journey.groups[0])
    assert [(loc.lid, loc.group) for loc in journey] == [("hotel", None), ("eiffel", None), ("louvre", "d2")]


def test_arrange_reorders_locations_and_groups():
    journey = grouped_journey()
    louvre, hotel, eiffel = journey.loc_by_id("louvre"), journey.loc_by_id("hotel"), journey.loc_by_id("eiffel")
    louvre.group = "d1"
    journey.arrange([hotel, louvre, eiffel], list(reversed(journey.groups)))
    assert [g.gid for g in journey.groups] == ["d2", "d1"]
    assert [loc.lid for loc in journey] == ["hotel", "louvre", "eiffel"]


def test_refuses_newer_format_than_1_1(fixture_text):
    with pytest.raises(ValueError, match="format version 1.2.0"):
        Journey.from_json_str(with_metadata(fixture_text, format_version="1.2.0"))


def test_load_format_1_1_fixture(fixture_text):
    journey = Journey.from_json_str(fixture_text("journey-1.1.0.json"))
    assert journey.notes.label() == "Paris trip"
    assert [g.label() for g in journey.groups] == ["Day 1: Left bank", "Day 2: Right bank"]
    assert [len(journey.group_locations(g)) for g in [None, *journey.groups]] == [1, 2, 3]
    assert journey.groups[1].collapsed
