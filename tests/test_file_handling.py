import json

import nc_py_api
import pytest
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMessageBox

from otripy import main
from otripy.journey import Journey
from otripy.location import Location
from otripy.main import MapApp


class Dialogs:
    """Scripted answers for the modal dialogs MapApp opens."""
    def __init__(self, monkeypatch):
        self.question_answer = QMessageBox.Discard
        self.open_path = ""
        self.save_path = ""
        self.errors = []
        monkeypatch.setattr(main.QMessageBox, "question", lambda *a, **k: self.question_answer)
        monkeypatch.setattr(main.QMessageBox, "critical", lambda parent, title, text: self.errors.append(text))
        monkeypatch.setattr(main.QFileDialog, "getOpenFileName", lambda *a, **k: (str(self.open_path), ""))
        monkeypatch.setattr(main.QFileDialog, "getSaveFileName", lambda *a, **k: (str(self.save_path), ""))


@pytest.fixture
def dialogs(monkeypatch):
    return Dialogs(monkeypatch)


@pytest.fixture
def window(qtbot, monkeypatch, dialogs):
    window = MapApp()
    qtbot.addWidget(window)
    monkeypatch.setattr(window.map_page, "setHtml", lambda html: None)
    monkeypatch.setattr(window.map_page, "runJavaScript", lambda code: None)
    return window


def add_location(window, name="Somewhere"):
    window.list_widget.addLocation(Location(1.0, 2.0, {"markdown": f"# {name}"}))


def labels(window):
    return [loc.label() for loc in window.list_widget.locations()]


def test_open_local_file(window, dialogs, fixture_text, tmp_path):
    dialogs.open_path = tmp_path / "trip.json"
    dialogs.open_path.write_text(fixture_text("journey-1.0.0.json"), encoding="utf-8")
    window.load_file()
    assert labels(window)[0] == "Tour Eiffel"
    assert window.current_file == str(dialogs.open_path)
    assert not window.dirty
    add_location(window)
    assert window.dirty, "edits of the opened journey must mark it modified"


def test_failed_open_keeps_current_journey(window, dialogs, tmp_path):
    add_location(window, "Mine")
    window.list_widget.locations().clean()
    window.current_file = "mine.json"
    dialogs.open_path = tmp_path / "broken.json"
    dialogs.open_path.write_text("{not json", encoding="utf-8")
    window.load_file()
    assert dialogs.errors
    assert labels(window) == ["Mine"]
    assert window.current_file == "mine.json"


def test_open_refused_when_keeping_changes(window, dialogs, tmp_path):
    add_location(window, "Unsaved")
    dialogs.question_answer = QMessageBox.No
    dialogs.open_path = tmp_path / "never-read.json"
    window.load_file()
    assert labels(window) == ["Unsaved"]


def test_save_as_then_save(window, dialogs, tmp_path):
    add_location(window, "Café")
    dialogs.save_path = tmp_path / "trip.json"
    assert window.save_file()
    assert not window.dirty
    assert window.current_file == str(dialogs.save_path)
    assert Journey.from_file(dialogs.save_path)[0].label() == "Café"
    add_location(window, "Second")
    assert window.save_file()
    assert len(Journey.from_file(dialogs.save_path)) == 2


def test_cancelled_save_as_keeps_changes_unsaved(window, dialogs):
    add_location(window)
    dialogs.save_path = ""
    assert not window.save_file()
    assert window.dirty


def test_failed_save_keeps_changes_unsaved(window, dialogs, tmp_path):
    add_location(window)
    dialogs.save_path = tmp_path / "missing-dir" / "trip.json"
    assert not window.save_file()
    assert dialogs.errors
    assert window.dirty
    assert window.current_file is None


def test_new_journey(window, dialogs):
    add_location(window)
    window.current_file = "old.json"
    dialogs.question_answer = QMessageBox.No
    window.new()
    assert labels(window) == ["Somewhere"]
    dialogs.question_answer = QMessageBox.Yes
    window.new()
    assert labels(window) == []
    assert window.current_file is None
    add_location(window)
    assert window.dirty


def close(window):
    event = QCloseEvent()
    window.closeEvent(event)
    return event.isAccepted()


@pytest.mark.parametrize("answer, save_path, closes", [
    (QMessageBox.Discard, "", True),
    (QMessageBox.Cancel, "", False),
    (QMessageBox.Save, "", False),           # save dialog cancelled
    (QMessageBox.Save, "trip.json", True),
])
def test_close_with_unsaved_changes(window, dialogs, tmp_path, answer, save_path, closes):
    add_location(window)
    dialogs.question_answer = answer
    dialogs.save_path = tmp_path / save_path if save_path else ""
    assert close(window) == closes


def test_close_without_changes(window):
    assert close(window)


class FakeNode(nc_py_api.FsNode):
    def __init__(self, path, etag):
        super().__init__(path, etag=etag, file_id=path)


class FakeFiles:
    """In-memory stand-in for nc_py_api's files API."""
    def __init__(self):
        self.contents, self.etags = {}, {}

    def put(self, path, data):
        self.contents[path] = data.encode() if isinstance(data, str) else data
        self.etags[path] = self.etags.get(path, 0) + 1
        return FakeNode(path, str(self.etags[path]))

    def by_path(self, path):
        if path not in self.contents:
            raise nc_py_api.NextcloudException(404, "not found")
        return FakeNode(path, str(self.etags[path]))

    def by_id(self, file_id):
        return self.by_path(file_id) if file_id in self.contents else None

    def download(self, node):
        return self.contents[node.user_path if isinstance(node, nc_py_api.FsNode) else node]

    def upload(self, node, data):
        return self.put(node.user_path if isinstance(node, nc_py_api.FsNode) else node, data)


@pytest.fixture
def nextcloud(window, monkeypatch):
    files = FakeFiles()
    window.nc = type("FakeNextcloud", (), {"files": files})()
    picked = {"path": None}

    class FakePicker:
        def __init__(self, nc, parent, save=False):
            pass

        def exec(self):
            return main.QDialog.DialogCode.Accepted

        def get_selected_file(self):
            return picked["path"]

    monkeypatch.setattr(main, "NextcloudFilePicker", FakePicker)
    files.pick = lambda path: picked.update(path=path)
    return files


def test_nextcloud_open_and_save(window, nextcloud, fixture_text):
    nextcloud.put("Trips/paris.json", fixture_text("journey-1.0.0.json"))
    nextcloud.pick("Trips/paris.json")
    window.load_nc_file()
    assert labels(window)[0] == "Tour Eiffel"
    add_location(window, "Added")
    assert window.save_file()
    assert not window.dirty
    saved = json.loads(nextcloud.contents["Trips/paris.json"])
    assert saved["format"] == "otripy"
    assert saved["locations"][-1]["note"]["markdown"] == "# Added"


def test_nextcloud_conflict_saves_under_new_name(window, nextcloud, fixture_text, monkeypatch):
    nextcloud.put("paris.json", fixture_text("journey-1.0.0.json"))
    nextcloud.pick("paris.json")
    window.load_nc_file()
    nextcloud.put("paris.json", "changed elsewhere")
    add_location(window)

    class FakeRename:
        def __init__(self, parent, path):
            self.line_edit = type("Edit", (), {"text": lambda self: "paris-2.json"})()

        def exec(self):
            return True

    monkeypatch.setattr(main, "RenamePopup", FakeRename)
    monkeypatch.setattr(window, "ask_save_conflict", lambda path, deleted: "rename")
    assert window.save_file()
    assert nextcloud.contents["paris.json"] == b"changed elsewhere"
    assert json.loads(nextcloud.contents["paris-2.json"])["format"] == "otripy"
    assert window.current_file.user_path == "paris-2.json"
    assert not window.dirty


def test_nextcloud_upload_error_keeps_changes_unsaved(window, nextcloud, dialogs, fixture_text, monkeypatch):
    nextcloud.put("paris.json", fixture_text("journey-1.0.0.json"))
    nextcloud.pick("paris.json")
    window.load_nc_file()
    add_location(window)

    def fail(*args):
        raise nc_py_api.NextcloudException(503, "unavailable")

    monkeypatch.setattr(nextcloud, "upload", fail)
    assert not window.save_file()
    assert dialogs.errors
    assert window.dirty


def test_nextcloud_open_error(window, nextcloud, dialogs):
    nextcloud.pick("missing.json")
    window.load_nc_file()
    assert dialogs.errors
    assert labels(window) == []


def test_opened_journey_is_framed(window, dialogs, fixture_text, tmp_path, monkeypatch):
    """Issue #25: opening a file shows all its locations."""
    pages = []
    monkeypatch.setattr(window.map_page, "setHtml", pages.append)
    dialogs.open_path = tmp_path / "trip.json"
    dialogs.open_path.write_text(fixture_text("journey-1.0.0.json"), encoding="utf-8")
    window.load_file()
    assert "fitBounds" in pages[-1]
    add_location(window)
    window.update_map()
    assert "fitBounds" not in pages[-1], "editing must not move the map"


def test_save_as_nextcloud(window, nextcloud):
    """Issue #28: save a new trip to Nextcloud, then save it again in place."""
    add_location(window, "First")
    nextcloud.pick("/Trips/new.json")
    assert window.save_file_as_nc()
    assert not window.dirty
    assert window.current_file.user_path == "/Trips/new.json"
    assert json.loads(nextcloud.contents["/Trips/new.json"])["locations"][0]["note"]["markdown"] == "# First"
    add_location(window, "Second")
    assert window.save_file()
    assert len(json.loads(nextcloud.contents["/Trips/new.json"])["locations"]) == 2


@pytest.mark.parametrize("answer, replaced", [(QMessageBox.Yes, True), (QMessageBox.No, False)])
def test_save_as_nextcloud_over_existing_file(window, nextcloud, dialogs, answer, replaced):
    nextcloud.put("/trip.json", "previous content")
    add_location(window)
    nextcloud.pick("/trip.json")
    dialogs.question_answer = answer
    assert window.save_file_as_nc() == replaced
    assert (nextcloud.contents["/trip.json"] != b"previous content") == replaced
    assert window.dirty != replaced


def test_save_as_nextcloud_error_keeps_changes_unsaved(window, nextcloud, dialogs, monkeypatch):
    add_location(window)
    nextcloud.pick("/trip.json")

    def fail(*args):
        raise nc_py_api.NextcloudException(507, "insufficient storage")

    monkeypatch.setattr(nextcloud, "upload", fail)
    assert not window.save_file_as_nc()
    assert dialogs.errors
    assert window.dirty


def open_then_change_remotely(window, nextcloud, fixture_text, remote_change):
    nextcloud.put("paris.json", fixture_text("journey-1.0.0.json"))
    nextcloud.pick("paris.json")
    window.load_nc_file()
    remote_change()
    add_location(window, "Mine")


@pytest.mark.parametrize("choice, saved", [("overwrite", True), ("cancel", False)])
def test_nextcloud_conflict_overwrite_or_cancel(window, nextcloud, fixture_text, monkeypatch, choice, saved):
    """Issue #10: a file changed on the server can be overwritten."""
    open_then_change_remotely(window, nextcloud, fixture_text, lambda: nextcloud.put("paris.json", "theirs"))
    asked = []
    monkeypatch.setattr(window, "ask_save_conflict", lambda path, deleted: asked.append((path, deleted)) or choice)
    assert window.save_file() == saved
    assert asked == [("paris.json", False)]
    content = nextcloud.contents["paris.json"]
    assert (content != b"theirs") == saved
    if saved:
        assert json.loads(content)["locations"][-1]["note"]["markdown"] == "# Mine"
    assert window.dirty != saved


def test_nextcloud_deleted_file_can_be_recreated(window, nextcloud, fixture_text, monkeypatch):
    def delete():
        del nextcloud.contents["paris.json"]
        del nextcloud.etags["paris.json"]
    open_then_change_remotely(window, nextcloud, fixture_text, delete)
    asked = []
    monkeypatch.setattr(window, "ask_save_conflict", lambda path, deleted: asked.append(deleted) or "overwrite")
    assert window.save_file()
    assert asked == [True]
    assert json.loads(nextcloud.contents["paris.json"])["format"] == "otripy"
    assert window.save_file(), "later saves go to the recreated file without asking again"
    assert asked == [True]


def test_save_conflict_dialog_buttons(window, monkeypatch):
    """The real dialog maps its buttons to the choices."""
    for label, expected in (("Save As…", "rename"), ("Overwrite", "overwrite"), (None, "cancel")):
        def fake_exec(box, label=label):
            buttons = {b.text(): b for b in box.buttons()}
            box_clicked = buttons[label] if label else box.button(QMessageBox.Cancel)
            monkeypatch.setattr(box, "clickedButton", lambda: box_clicked)
        monkeypatch.setattr(main.QMessageBox, "exec", fake_exec)
        assert window.ask_save_conflict("paris.json", deleted=False) == expected


def recent_labels(window):
    window.update_recent_menu()
    return [a.text() for a in window.recent_menu.actions() if a.text() and a.text() != "Clear Recent Files"]


def test_opened_and_saved_files_become_recent(window, dialogs, fixture_text, tmp_path):
    """Issue #11: File > Open Recent lists opened and saved trips, most recent first."""
    first = tmp_path / "first.json"
    first.write_text(fixture_text("journey-1.0.0.json"), encoding="utf-8")
    dialogs.open_path = first
    window.load_file()
    add_location(window)
    dialogs.save_path = tmp_path / "second.json"
    assert window.save_file_as()
    assert recent_labels(window) == [str(tmp_path / "second.json"), str(first)]


def test_open_recent_file(window, dialogs, fixture_text, tmp_path):
    trip = tmp_path / "trip.json"
    trip.write_text(fixture_text("journey-1.0.0.json"), encoding="utf-8")
    dialogs.open_path = trip
    window.load_file()
    window.new()
    window.update_recent_menu()  # done by the menu when it opens
    [action] = [a for a in window.recent_menu.actions() if a.text() == str(trip)]
    action.trigger()
    assert labels(window)[0] == "Tour Eiffel"
    assert window.current_file == str(trip)


def test_missing_recent_file_is_forgotten(window, dialogs, fixture_text, tmp_path):
    trip = tmp_path / "trip.json"
    trip.write_text(fixture_text("journey-1.0.0.json"), encoding="utf-8")
    dialogs.open_path = trip
    window.load_file()
    trip.unlink()
    assert not window.open_recent_file(str(trip))
    assert dialogs.errors
    assert recent_labels(window) == []


def test_recent_files_are_limited_and_clearable(window):
    for i in range(main.MAX_RECENT_FILES + 3):
        window.current_file = f"/trips/{i}.json"
        window.remember_current_file()
    assert len(recent_labels(window)) == main.MAX_RECENT_FILES
    assert recent_labels(window)[0] == str(main.Path("/trips/12.json").resolve())
    [clear] = [a for a in window.recent_menu.actions() if a.text() == "Clear Recent Files"]
    clear.trigger()
    assert recent_labels(window) == []


def test_recent_nextcloud_file(window, nextcloud, fixture_text):
    nextcloud.put("Trips/paris.json", fixture_text("journey-1.0.0.json"))
    nextcloud.pick("Trips/paris.json")
    window.load_nc_file()
    assert recent_labels(window) == ["Trips/paris.json (Nextcloud)"]
    window.new()
    assert window.open_recent_file(main.NEXTCLOUD_PREFIX + "Trips/paris.json")
    assert window.current_file.user_path == "Trips/paris.json"
