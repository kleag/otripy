import re
import shutil
import subprocess

import pytest

from otripy.journey import Journey
from otripy.location import Location
from otripy.map_view import (DEFAULT_CENTER, MapBridge, build_map_html, downplay_marker_js,
                             highlight_marker_js, js_string, marker_icon_js, move_map_js,
                             update_marker_text_js)


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
