from types import SimpleNamespace

import pytest

from otripy.nextcloud_with_api import NextcloudFilePicker

TREE = {
    "": [("Trips", True), ("notes.txt", False)],
    "/Trips": [("Old", True), ("paris.json", False), ("[odd].json", False)],
    "/Trips/Old": [("2024.json", False)],
}


class FakeNextcloud:
    def __init__(self):
        self.files = SimpleNamespace(listdir=lambda path: [SimpleNamespace(name=n, is_dir=d) for n, d in TREE[path]])


def entries(picker):
    return [picker.list_model.item(row).text() for row in range(picker.list_model.rowCount())]


def click(picker, text):
    row = entries(picker).index(text)
    picker.on_file_selected(picker.list_model.index(row, 0))


@pytest.fixture
def make_picker(qtbot):
    def make(save=False):
        picker = NextcloudFilePicker(FakeNextcloud(), save=save)
        qtbot.addWidget(picker)
        return picker
    return make


def test_open_browses_folders_and_picks_a_file(make_picker):
    picker = make_picker()
    assert entries(picker) == ["[Trips]", "notes.txt"]
    click(picker, "[Trips]")
    assert entries(picker) == ["[..]", "[Old]", "paris.json", "[odd].json"]
    click(picker, "[Old]")
    click(picker, "[..]")
    assert picker.path_line_edit.text() == "/Trips"
    click(picker, "paris.json")
    assert picker.result() == NextcloudFilePicker.Accepted
    assert picker.get_selected_file() == "/Trips/paris.json"


def test_bracketed_file_name_is_a_file(make_picker):
    picker = make_picker()
    click(picker, "[Trips]")
    click(picker, "[odd].json")
    assert picker.get_selected_file() == "/Trips/[odd].json"


def test_save_names_a_new_file(make_picker):
    """Issue #28: pick a folder and type a name; .json is added if missing."""
    picker = make_picker(save=True)
    click(picker, "[Trips]")
    picker.name_line_edit.setText("rome")
    picker.accept_name()
    assert picker.result() == NextcloudFilePicker.Accepted
    assert picker.get_selected_file() == "/Trips/rome.json"


def test_save_clicking_a_file_fills_the_name(make_picker):
    picker = make_picker(save=True)
    click(picker, "[Trips]")
    click(picker, "paris.json")
    assert picker.result() != NextcloudFilePicker.Accepted, "saving over a file must not be immediate"
    assert picker.name_line_edit.text() == "paris.json"


def test_save_needs_a_name(make_picker):
    picker = make_picker(save=True)
    picker.accept_name()
    assert picker.result() != NextcloudFilePicker.Accepted
