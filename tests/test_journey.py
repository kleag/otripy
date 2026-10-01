import io
import json

import pytest

from otripy import __version__
from otripy.journey import CURRENT_FORMAT_VERSION, Journey
from otripy.location import Location


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
    assert data["format_version"] == CURRENT_FORMAT_VERSION
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


def test_refuses_file_from_newer_app(fixture_text):
    with pytest.raises(ValueError, match="99.0.0"):
        Journey.from_json_str(with_metadata(fixture_text, app_version="99.0.0"))


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
