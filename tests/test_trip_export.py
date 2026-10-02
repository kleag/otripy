"""Export for map apps on phones (issue #47)."""
import io
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

from otripy.journey import Journey
from otripy.location import Group, Leg, Location, TripNotes
from otripy.trip_export import (ORGANIC_COLORS, ORGANIC_ICONS, build_gpx, build_kmz, markdown_to_html,
                                markdown_to_text)

KML = {"k": "http://www.opengis.net/kml/2.2"}
GPX = {"g": "http://www.topografix.com/GPX/1/1"}
ICONS = {p.stem for p in (Path(__file__).resolve().parent.parent / "src" / "otripy" / "resources" / "icons").glob("*.svg")}
ORGANIC_COLOR_NAMES = {"red", "blue", "purple", "yellow", "pink", "brown", "green", "orange", "deeppurple",
                       "lightblue", "cyan", "teal", "lime", "deeporange", "gray", "bluegray"}
ORGANIC_ICON_NAMES = {"Hotel", "Animals", "Buddhism", "Building", "Christianity", "Entertainment", "Exchange", "Food",
                      "Gas", "Judaism", "Medicine", "Mountain", "Museum", "Islam", "Park", "Parking", "Shop", "Sights",
                      "Swim", "Water", "Bar", "Transport", "Viewpoint", "Sport", "Pub", "Art", "Bank", "Cafe",
                      "Pharmacy", "Stadium", "Theatre", "Information", "ChargingStation", "BicycleParking",
                      "BicycleParkingCovered", "BicycleRental", "FastFood", "Airport"}


def trip():
    days = [Group({"markdown": "# Day 1\n\nOn **foot**"}, id="g1"), Group({"markdown": "# Day 2"}, id="g2"),
            Group({"markdown": "# Empty day"}, id="g3")]
    return Journey([
        Location(53.3498, -6.2603, {"markdown": "# Dublin\n\nArrival", "images": {}}, id="dublin"),
        Location(53.2707, -9.0568, {"markdown": "# Galway\n\nSee [the harbour](https://galway.ie) & <the docks>\n\n"
                                                "![image](image_1)\n\n- pub\n- music", "images": {"image_1": "x"}},
                 id="galway", marker="bed", color="darkgreen", group="g1"),
        Location(53.0, -9.4, {"markdown": "# Cliffs of Moher"}, id="moher", marker="binoculars", group="g1"),
        Location(52.06, -9.5, {"markdown": "# Killarney"}, id="killarney", marker="star", color="red", group="g2"),
    ], groups=days, notes=TripNotes({"markdown": "# Ireland\n\nPassports and *adapters*", "images": {}}))


def kml_documents(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return [(name, ET.fromstring(archive.read(name))) for name in archive.namelist()]


def placemarks(document):
    return document.findall(".//k:Placemark", KML)


def test_mappings_use_existing_names():
    assert set(ORGANIC_COLORS.values()) <= ORGANIC_COLOR_NAMES
    assert set(ORGANIC_ICONS.values()) <= ORGANIC_ICON_NAMES
    assert set(ORGANIC_ICONS) <= ICONS, "only icons Otripy offers"


def test_kmz_has_one_list_per_section():
    """Organic Maps imports each KML of a KMZ as a separate list; empty groups are skipped."""
    documents = kml_documents(build_kmz(trip(), "Ireland"))
    assert [name for name, _ in documents] == ["00 Ireland.kml", "01 Ireland – Day 1.kml", "02 Ireland – Day 2.kml"]
    names = [doc.find("k:Document/k:name", KML).text for _, doc in documents]
    assert names == ["Ireland", "Ireland – Day 1", "Ireland – Day 2"]
    assert [[p.find("k:name", KML).text for p in placemarks(doc)] for _, doc in documents] == \
        [["Dublin"], ["Galway", "Cliffs of Moher"], ["Killarney"]]


def test_list_descriptions_come_from_trip_and_group_notes():
    documents = kml_documents(build_kmz(trip(), "Ireland"))
    descriptions = [doc.findtext("k:Document/k:description", None, KML) for _, doc in documents]
    assert descriptions[0] == "<p>Passports and <em>adapters</em></p>"
    assert descriptions[1] == "<p>On <strong>foot</strong></p>"
    assert descriptions[2] is None


def test_bookmark_details():
    _, day1 = kml_documents(build_kmz(trip(), "Ireland"))[1]
    galway, moher = placemarks(day1)
    assert galway.findtext("k:Point/k:coordinates", None, KML) == "-9.056800,53.270700", "KML is lon,lat"
    assert galway.findtext("k:styleUrl", None, KML) == "#placemark-teal"
    assert galway.findtext("k:ExtendedData/{https://omaps.app}icon", None, KML) == "Hotel"
    assert moher.findtext("k:styleUrl", None, KML) == "#placemark-blue"
    assert moher.findtext("k:ExtendedData/{https://omaps.app}icon", None, KML) == "Viewpoint"
    description = galway.findtext("k:description", None, KML)
    assert '<a href="https://galway.ie">the harbour</a>' in description
    assert "&lt;the docks&gt;" in description or "&lt;the docks>" in description
    assert "<li>pub</li>" in description
    assert "image" not in description, "images are not exported"


def test_unmapped_icon_has_no_icon():
    _, day2 = kml_documents(build_kmz(trip(), "Ireland"))[2]
    [killarney] = placemarks(day2)
    assert killarney.find("k:ExtendedData", KML) is None
    assert killarney.findtext("k:styleUrl", None, KML) == "#placemark-red"


def trip_with_legs():
    journey = trip()
    journey.add_leg(Leg("dublin", "galway", "car", 208_000, 9_000, [(53.35, -6.26), (53.27, -9.06)]))
    journey.add_leg(Leg("galway", "moher", "bike", 70_000, 14_000, [(53.27, -9.06), (53.1, -9.2), (53.0, -9.4)]))
    return journey


def test_routes_are_tracks_in_the_list_of_their_start():
    """Issue #50: each route between two places is a track, with the list of its first place."""
    documents = kml_documents(build_kmz(trip_with_legs(), "Ireland"))
    tracks = [[(p.findtext("k:name", None, KML), p.findtext("k:LineString/k:coordinates", None, KML))
               for p in placemarks(doc) if p.find("k:LineString", KML) is not None] for _, doc in documents]
    assert tracks[0] == [("Dublin → Galway (Car)", "-6.260000,53.350000 -9.060000,53.270000")]
    assert tracks[1] == [("Galway → Cliffs of Moher (Bicycle)",
                          "-9.060000,53.270000 -9.200000,53.100000 -9.400000,53.000000")]
    assert tracks[2] == []


def test_routes_can_be_left_out():
    documents = kml_documents(build_kmz(trip_with_legs(), "Ireland", include_routes=False))
    assert all(doc.find(".//k:LineString", KML) is None for _, doc in documents)


def test_trip_without_groups_is_one_list():
    journey = Journey([Location(1, 2, {"markdown": "# A"}), Location(3, 4, {"markdown": "# B"})])
    documents = kml_documents(build_kmz(journey, "Trip"))
    assert len(documents) == 1 and len(placemarks(documents[0][1])) == 2


def test_cdata_end_in_notes_stays_valid():
    journey = Journey([Location(1, 2, {"markdown": "# A\n\ncode ]]> end"})])
    [(_, document)] = kml_documents(build_kmz(journey, "Trip"))
    assert "]]&gt; end" in placemarks(document)[0].findtext("k:description", None, KML) or \
        "]]> end" in placemarks(document)[0].findtext("k:description", None, KML)


def test_gpx_waypoints_and_tracks():
    root = ET.fromstring(build_gpx(trip_with_legs(), "Ireland"))
    assert root.findtext("g:metadata/g:name", None, GPX) == "Ireland"
    assert root.findtext("g:metadata/g:desc", None, GPX) == "Passports and *adapters*"
    waypoints = root.findall("g:wpt", GPX)
    assert [(w.findtext("g:name", None, GPX), w.findtext("g:type", None, GPX)) for w in waypoints] == [
        ("Dublin", "Ireland"), ("Galway", "Ireland – Day 1"), ("Cliffs of Moher", "Ireland – Day 1"),
        ("Killarney", "Ireland – Day 2")]
    galway = waypoints[1]
    assert (galway.get("lat"), galway.get("lon")) == ("53.270700", "-9.056800")
    assert galway.findtext("g:desc", None, GPX) == \
        "See the harbour (https://galway.ie) & <the docks>\n\n- pub\n- music"
    assert galway.findtext("g:extensions/{https://osmand.net}color", None, GPX) == "#006400"
    assert [t.findtext("g:name", None, GPX) for t in root.findall("g:trk", GPX)] == [
        "Dublin → Galway (Car)", "Galway → Cliffs of Moher (Bicycle)"]
    assert len(root.findall("g:trk/g:trkseg/g:trkpt", GPX)) == 5


@pytest.mark.parametrize("markdown, text", [
    ("**Bold** and ~~struck~~", "Bold and struck"),
    ("## Heading\n\nText", "Heading\n\nText"),
    ("<https://x.org>", "https://x.org"),
])
def test_markdown_to_text(markdown, text):
    assert markdown_to_text(markdown) == text


def test_markdown_to_html_has_no_raw_html():
    converted = markdown_to_html("<script>alert(1)</script>")
    assert "<script" not in converted and "&lt;script" in converted
    assert markdown_to_html("<https://x.org>") == '<p><a href="https://x.org">https://x.org</a></p>'


# The export in the main window

class FakeExportDialog:
    """Scripted ExportDialog: format, route, destination (None to cancel)."""
    choice = ("kmz", True, "file")

    def __init__(self, parent=None, route_count=0):
        self.route_count = route_count

    def exec(self):
        from otripy import main
        return main.QDialog.DialogCode.Accepted if self.choice[2] else main.QDialog.DialogCode.Rejected

    @property
    def destination(self):
        return self.choice[2]

    def export_format(self):
        return self.choice[0]

    def include_route(self):
        return bool(self.route_count) and self.choice[1]


@pytest.fixture
def window(qtbot, monkeypatch, tmp_path):
    from otripy import main
    window = main.MapApp()
    qtbot.addWidget(window)
    monkeypatch.setattr(window.map_page, "setHtml", lambda html: None)
    monkeypatch.setattr(window.map_page, "runJavaScript", lambda code: None)
    monkeypatch.setattr(main.QMessageBox, "question", lambda *a, **k: main.QMessageBox.Discard)
    window.messages = []
    monkeypatch.setattr(main.QMessageBox, "information", lambda parent, title, text: window.messages.append(text))
    monkeypatch.setattr(main.QMessageBox, "critical", lambda parent, title, text: window.messages.append(text))
    monkeypatch.setattr(main, "ExportDialog", FakeExportDialog)
    window.save_path = tmp_path / "export"
    monkeypatch.setattr(main.QFileDialog, "getSaveFileName", lambda *a, **k: (str(window.save_path), ""))
    window.set_journey(trip(), str(tmp_path / "Ireland 2026.json"))
    return window


@pytest.mark.parametrize("fmt, extension", [("kmz", ".kmz"), ("gpx", ".gpx")])
def test_export_to_file(window, monkeypatch, fmt, extension):
    monkeypatch.setattr(FakeExportDialog, "choice", (fmt, True, "file"))
    assert window.export_for_phone()
    exported = window.save_path.with_suffix(extension)
    assert exported.exists(), "the extension is added"
    data = exported.read_bytes()
    if fmt == "kmz":
        assert kml_documents(data)[0][1].findtext("k:Document/k:name", None, KML) == "Ireland 2026"
    else:
        assert ET.fromstring(data).findtext("g:metadata/g:name", None, GPX) == "Ireland 2026"


def test_export_includes_the_routes(window, monkeypatch):
    window.list_widget.locations().add_leg(Leg("dublin", "galway", "car", 1000, 600, [(53.35, -6.26), (53.27, -9.06)]))
    monkeypatch.setattr(FakeExportDialog, "choice", ("kmz", True, "file"))
    assert window.export_for_phone()
    first = kml_documents(window.save_path.with_suffix(".kmz").read_bytes())[0][1]
    assert first.findall(".//k:Placemark/k:name", KML)[-1].text == "Dublin → Galway (Car)"


def test_export_to_nextcloud(window, monkeypatch):
    from otripy import main
    uploads = {}
    files = type("Files", (), {
        "by_path": lambda self, path: (_ for _ in ()).throw(main.nc_py_api.NextcloudException(404, "absent")),
        "upload": lambda self, path, data: uploads.update({path: data})})()
    window.nc = type("FakeNextcloud", (), {"files": files})()

    class Picker:
        def __init__(self, nc, parent, save=False, extension=".json"):
            self.extension = extension

        def exec(self):
            return main.QDialog.DialogCode.Accepted

        def get_selected_file(self):
            return "/Trips/ireland" + self.extension

    monkeypatch.setattr(main, "NextcloudFilePicker", Picker)
    monkeypatch.setattr(FakeExportDialog, "choice", ("gpx", False, "nextcloud"))
    assert window.export_for_phone()
    assert list(uploads) == ["/Trips/ireland.gpx"]
    assert ET.fromstring(uploads["/Trips/ireland.gpx"]).find("g:wpt", GPX) is not None


def test_export_needs_locations(window):
    window.set_journey(Journey(), None)
    assert not window.export_for_phone()
    assert window.messages


def test_cancelled_export_writes_nothing(window, monkeypatch):
    monkeypatch.setattr(FakeExportDialog, "choice", ("kmz", True, None))
    assert not window.export_for_phone()
    assert not window.save_path.with_suffix(".kmz").exists()


def test_export_dialog_choices(qtbot):
    from otripy.export_dialog import ExportDialog
    dialog = ExportDialog(route_count=0)
    qtbot.addWidget(dialog)
    assert dialog.export_format() == "kmz" and not dialog.include_route() and not dialog.route_box.isEnabled()
    dialog.gpx_button.setChecked(True)
    dialog.nextcloud_button.click()
    assert (dialog.export_format(), dialog.destination) == ("gpx", "nextcloud")
    with_routes = ExportDialog(route_count=3)
    qtbot.addWidget(with_routes)
    assert with_routes.include_route() and "(3)" in with_routes.route_box.text()
