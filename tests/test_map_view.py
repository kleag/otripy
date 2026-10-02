import re
import shutil
import subprocess

import pytest

from otripy.journey import Journey
from otripy.location import Location
from otripy.map_view import (DEFAULT_CENTER, MapBridge, build_map_html, downplay_marker_js,
                             highlight_marker_js, js_string, marker_icon_js, move_map_js,
                             hover_marker_js, tooltip_html, update_marker_text_js)

# folium's fit_bounds call, with literal bounds (the page's fitPoints function calls fitBounds too)
FIT_ALL = re.compile(r"\.fitBounds\(\s*\[\[")


def inline_scripts(html):
    return re.findall(r"<script>(.*?)</script>", html, re.S)


def assert_valid_js(code, tmp_path):
    if shutil.which("node") is None:
        pytest.skip("node is needed to check JavaScript syntax")
    path = tmp_path / "check.js"
    path.write_text(code)
    result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("value", ['say "hi"', "back\\slash", "it's", "line\nbreak", "</script><b>x</b>"])
def test_js_string_escapes(value, tmp_path):
    literal = js_string(value)
    assert "</" not in literal
    assert_valid_js(f"var s = {literal};", tmp_path)


def test_marker_icon_defaults():
    js = marker_icon_js(Location())
    assert '"fa-circle"' in js and '"blue"' in js


def test_marker_icon_uses_location_style():
    js = marker_icon_js(Location(marker="bed", color="purple"))
    assert '"fa-bed"' in js and '"purple"' in js


@pytest.mark.parametrize("name", ["legacy-list.json", "journey-1.0.0.json", "journey-with-images.json"])
def test_map_html_scripts_are_valid(fixture_text, name, tmp_path):
    journey = Journey.from_json_str(fixture_text(name))
    html = build_map_html(journey)
    for loc in journey:
        assert js_string(loc.lid) in html
    scripts = inline_scripts(html)
    assert scripts
    for script in scripts:
        assert_valid_js(script, tmp_path)


def test_map_centers_on_last_location():
    html = build_map_html([Location(10.5, 20.25), Location(-33.5, 151.25)])
    assert "[-33.5, 151.25]" in html


def test_empty_map_centers_on_default():
    assert str(DEFAULT_CENTER) in build_map_html([])


def test_marker_update_snippets_are_valid(tmp_path):
    loc = Location(1, 2, id='quote"id', marker="star", color="red")
    for code in (highlight_marker_js(loc.lid), downplay_marker_js(loc), move_map_js(1, 2),
                 update_marker_text_js(loc)):
        assert_valid_js("function moveMap() {}\n" + code, tmp_path)


def test_bridge_relays_events(qtbot):
    bridge = MapBridge()
    with qtbot.waitSignal(bridge.mapClicked) as clicked:
        bridge.on_map_clicked(48.5, 2.25)
    assert clicked.args == [48.5, 2.25]
    with qtbot.waitSignal(bridge.markerClicked) as clicked:
        bridge.on_marker_clicked("abc")
    assert clicked.args == ["abc"]


def test_marker_texts_are_escaped_html():
    loc = Location(1, 2, {"markdown": "# Fish & <Chips>"}, id="x")
    for code in (build_map_html([loc]), update_marker_text_js(loc)):
        assert "<Chips>" not in code
        assert "Fish &amp; &lt;Chips&gt;" in code


def test_fit_all_frames_every_location():
    locations = [Location(48.85, 2.35), Location(43.30, 5.37), Location(50.63, 3.06)]
    html = build_map_html(locations, fit_all=True)
    assert FIT_ALL.search(html)
    assert "[[43.3, 2.35], [50.63, 5.37]]" in html


@pytest.mark.parametrize("locations", [[], [Location(48.85, 2.35)]])
def test_fit_all_needs_two_locations(locations):
    assert not FIT_ALL.search(build_map_html(locations, fit_all=True))


def test_map_does_not_fit_by_default():
    assert not FIT_ALL.search(build_map_html([Location(48.85, 2.35), Location(43.30, 5.37)]))


def test_map_keeps_given_view():
    html = build_map_html([Location(48.85, 2.35), Location(43.30, 5.37)], view=(45.5, 4.25, 9))
    assert "[45.5, 4.25]" in html
    assert '"zoom": 9' in html


def test_fit_all_overrides_view():
    html = build_map_html([Location(48.85, 2.35), Location(43.30, 5.37)], fit_all=True, view=(45.5, 4.25, 9))
    assert FIT_ALL.search(html)
    assert '"zoom": 9' not in html


def test_page_reports_its_view():
    html = build_map_html([Location(48.85, 2.35)])
    assert 'map.on("moveend", reportView)' in html
    assert "on_view_changed" in html


def test_bridge_relays_view_changes(qtbot):
    bridge = MapBridge()
    with qtbot.waitSignal(bridge.viewChanged) as changed:
        bridge.on_view_changed(45.5, 4.25, 9)
    assert changed.args == [45.5, 4.25, 9]


def test_tooltip_shows_title_and_note_preview():
    loc = Location(note={"markdown": "# Fish & Chips\n\nOpen <late>\n\nCash only"})
    assert tooltip_html(loc) == "<b>Fish &amp; Chips</b><br>Open &lt;late&gt;<br>Cash only"


def test_markers_report_hovering():
    html = build_map_html([Location(1, 2, id="abc")])
    assert 'on_marker_hovered("abc")' in html
    assert 'on_marker_hovered("")' in html
    assert ".otripy-hover" in html


def test_hover_snippet_is_valid(tmp_path):
    for hovered in (True, False):
        assert_valid_js("function hoverMarker() {}\n" + hover_marker_js('a"b', hovered), tmp_path)


def test_bridge_relays_hovering(qtbot):
    bridge = MapBridge()
    with qtbot.waitSignal(bridge.markerHovered) as hovered:
        bridge.on_marker_hovered("abc")
    assert hovered.args == ["abc"]


# Routes between two locations (issue #50)

def leg_page():
    from otripy.location import Leg
    a = Location(48.8584, 2.2945, {"markdown": "# Tour \"Eiffel\""}, id="a")
    b = Location(48.8606, 2.3376, {"markdown": "# Louvre"}, id="b")
    leg = Leg("a", "b", "foot", 3748, 3002, [(48.8584, 2.2945), (48.86, 2.31), (48.8606, 2.3376)], id="leg-1")
    return [a, b], leg


def test_legs_are_drawn_with_their_mode_and_actions(tmp_path):
    locations, leg = leg_page()
    html = build_map_html(locations, legs=[leg])
    assert "L.polyline([[48.8584, 2.2945], [48.86, 2.31], [48.8606, 2.3376]]" in html
    assert '"#e07b24"' in html and "dashArray" in html, "foot routes are orange and dashed"
    assert "Foot: 3.7 km, 50 min" in html
    assert 'on_leg_action(&quot;leg-1&quot;, &quot;car&quot;)' in html
    assert 'on_leg_action(&quot;leg-1&quot;, &quot;remove&quot;)' in html
    assert "Tour &quot;Eiffel&quot; → Louvre" in html.replace("\\u2192", "→")
    for script in inline_scripts(html):
        assert_valid_js(script, tmp_path)


def test_marker_shift_click_is_reported():
    locations, _ = leg_page()
    html = build_map_html(locations)
    assert "event.originalEvent.shiftKey" in html
    assert 'on_marker_shift_clicked("a")' in html


def test_bridge_relays_route_events(qtbot):
    bridge = MapBridge()
    with qtbot.waitSignal(bridge.markerShiftClicked) as clicked:
        bridge.on_marker_shift_clicked("b")
    assert clicked.args == ["b"]
    with qtbot.waitSignal(bridge.legAction) as action:
        bridge.on_leg_action("leg-1", "remove")
    assert action.args == ["leg-1", "remove"]
