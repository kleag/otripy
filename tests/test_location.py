from otripy.location import Location


def test_label_is_first_line_without_heading_marks():
    loc = Location(note={"markdown": "## Tour Eiffel\n\nParis"})
    assert loc.label() == "Tour Eiffel"
    assert str(loc) == "Tour Eiffel"


def test_default_notes_are_not_shared():
    a, b = Location(), Location()
    a.note["markdown"] = "changed"
    assert b.note == {"markdown": ""}


def test_ids_are_unique_unless_given():
    assert Location().lid != Location().lid
    assert Location(id="abc").lid == "abc"


def test_from_data_normalizes_legacy_values():
    loc = Location.from_data({"lat": "48.5", "lon": "2.25", "note": "Plain text", "marker": "", "color": ""})
    assert (loc.lat, loc.lon) == (48.5, 2.25)
    assert loc.note == {"markdown": "Plain text"}
    assert loc.marker is None
    assert loc.color is None


def test_from_data_defaults_missing_fields():
    loc = Location.from_data({})
    assert (loc.lat, loc.lon) == (0.0, 0.0)
    assert loc.note == {"markdown": ""}


def test_to_dict_round_trip():
    loc = Location(1.5, -2.5, {"markdown": "# A", "images": {}}, id="x", marker="star", color="red")
    again = Location.from_data(loc.to_dict())
    assert again.to_dict() == loc.to_dict()


def test_label_removes_markdown_escapes():
    loc = Location(note={"markdown": r"# Café \*Le Bistro\* at \[1.5, 2.5\] \\ ok" + "\n\nbody"})
    assert loc.label() == r"Café *Le Bistro* at [1.5, 2.5] \ ok"


def test_popup_html_is_escaped():
    loc = Location(note={"markdown": "# Fish & <Chips>"})
    assert loc.to_html() == "Fish &amp; &lt;Chips&gt;"
