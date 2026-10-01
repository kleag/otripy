import io
import json
import logging

from datetime import datetime, timezone
from typing import List, Iterator, TextIO
from packaging.version import Version
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QTimer
try:
    from . import __version__
    from .location import Group, Location, TripNotes, note_from_data
except ImportError:
    from __init__ import __version__
    from location import Group, Location, TripNotes, note_from_data

logger = logging.getLogger(__name__)

# The newest file format this version reads and writes
CURRENT_FORMAT_VERSION = "1.1.0"
# Written when a journey uses none of the 1.1.0 additions (groups, trip notes),
# so that versions reading only 1.0.0 can open it
BASE_FORMAT_VERSION = "1.0.0"


class Journey(QObject):
    """An ordered list of Locations, the document Otripy edits and saves.

    It behaves like a list (indexing, iteration, len, append, insert, remove,
    pop) and emits dirty(True) on every change, dirty(False) once saved or
    cleared. It also has groups (titled sections of the list, issue #18) and
    the trip's notes (issue #19). Locations are kept in display order:
    ungrouped ones first, then those of each group, in group order. It reads
    and writes the JSON format described in docs/file-format.md, including the
    legacy pre-1.0.0 one.
    """
    dirty = Signal(bool)  # True when modified since last saved

    def __init__(self, locations: List[Location] = None, parent=None, groups: List[Group] = None,
                 notes: TripNotes = None):
        """Initialize the journey with a list of Location objects."""
        super().__init__(parent)
        self._locations = locations if locations is not None else []
        self._groups = groups if groups is not None else []
        self.notes = notes if notes is not None else TripNotes()
        self.normalize_order()
        self._dirty = False
        self._created_at = None  # The creation date that was stored in the file where this journey was saved at, None if not already saved or if absent
        self._updated_at = None  # The last update date that was stored in the file where this journey was saved at, None if not already saved or if absent

    @classmethod
    def from_json_str(cls, json_str: str):
        journey = Journey()
        journey.load_from_json(json_str)
        return journey

    def __getitem__(self, index):
        """Enable indexing and slicing."""
        return self._locations[index]

    def __setitem__(self, index, value: Location):
        """Enable item assignment."""
        if not isinstance(value, Location):
            raise TypeError("Only Location instances can be added to the journey.")
        self._dirty = True
        self.dirty.emit(self._dirty)
        self._locations[index] = value

    def __delitem__(self, index):
        """Enable item deletion."""
        self._dirty = True
        self.dirty.emit(self._dirty)
        del self._locations[index]

    def __iter__(self) -> Iterator[Location]:
        """Enable iteration."""
        return iter(self._locations)

    def __len__(self) -> int:
        """Return the number of locations in the journey."""
        return len(self._locations)

    def append(self, location: Location):
        """Add a location to the journey."""
        if not isinstance(location, Location):
            raise TypeError("Only Location instances can be added to the journey.")
        self._dirty = True
        self.dirty.emit(self._dirty)
        self._locations.append(location)

    def insert(self, index: int, location: Location):
        """Insert a location at a specific index."""
        # logger.info(f"Journey.insert {index}, {location}")
        if not isinstance(location, Location):
            raise TypeError("Only Location instances can be inserted into the journey.")
        self._locations.insert(index, location)
        self._dirty = True
        self.dirty.emit(self._dirty)

    def remove(self, location: Location):
        """Remove a location from the journey."""
        self._dirty = True
        self.dirty.emit(self._dirty)
        self._locations.remove(location)

    def __repr__(self) -> str:
        return f"Journey({self._locations})"

    def loc_by_id(self, id: str) -> Location:
        for loc in self:
            if loc.lid == id:
                return loc
        return None

    # Groups (issue #18)
    @property
    def groups(self) -> List[Group]:
        return list(self._groups)

    def group_by_id(self, group_id) -> Group | None:
        return next((group for group in self._groups if group.gid == group_id), None)

    def group_locations(self, group: Group | None) -> List[Location]:
        """The locations of a group, or the ungrouped ones for None, in order."""
        group_id = group.gid if group is not None else None
        return [loc for loc in self._locations if loc.group == group_id]

    def normalize_order(self):
        """Put the locations in display order: ungrouped ones, then each group's."""
        known = {group.gid for group in self._groups}
        for loc in self._locations:
            if loc.group is not None and loc.group not in known:
                loc.group = None  # its group is gone: keep the location
        self._locations = self.group_locations(None) + [
            loc for group in self._groups for loc in self.group_locations(group)]

    def add_group(self, group: Group, index: int = None):
        if index is None:
            self._groups.append(group)
        else:
            self._groups.insert(index, group)
        self.mark_dirty()

    def remove_group(self, group: Group):
        """Remove a group; its locations stay, ungrouped."""
        self._groups.remove(group)
        for loc in self._locations:
            if loc.group == group.gid:
                loc.group = None
        self.normalize_order()
        self.mark_dirty()

    def arrange(self, locations: List[Location], groups: List[Group]):
        """Set the order of the locations and of the groups, after a move in the list."""
        assert sorted(map(id, locations)) == sorted(map(id, self._locations))
        assert sorted(map(id, groups)) == sorted(map(id, self._groups))
        self._locations = list(locations)
        self._groups = list(groups)
        self.normalize_order()
        self.mark_dirty()

    def mark_dirty(self):
        self._dirty = True
        self.dirty.emit(True)

    def uses_format_1_1(self) -> bool:
        return bool(self._groups) or self.notes.has_note()

    def clear(self):
        self._locations.clear()
        self._groups.clear()
        self.notes = TripNotes()
        self._dirty = False
        self.dirty.emit(self._dirty)

    def clean(self):
        self._dirty = False
        self.dirty.emit(self._dirty)

    def pop(self, index: int = -1) -> Location:
        """Remove and return a location at the given index (default: last item)."""
        # logger.info(f"Journey.pop {index}")
        if not self._locations:
            raise IndexError("pop from empty Journey")

        loc = self._locations.pop(index)
        self._dirty = True
        # Use QTimer to emit the signal after execution completes
        if self._locations:  # Only emit dirty if there are still items
            QTimer.singleShot(0, lambda: self.dirty.emit(self._dirty))
        else:
            self.clean()  # Reset if empty
        # logger.info(f"Journey.pop popped {loc}")
        return loc

    def load_from_json(self, json_str: str):
        journey = json.loads(json_str)
        # logger.info(f"Journey.load_from_json {journey}")
        if type(journey) is list:
            # Initial pre-1.0.0 unstructured format with no metadata
            # we have only a list of locations
            self._locations = [Location.from_data(loc) for loc in journey]
            logger.warning("Loading old unstructured pre-1.0.0 format with no metadata")
            return
        if not isinstance(journey, dict) or journey.get("format") != "otripy":
            raise ValueError("This is not an Otripy journey file.")

        # Only the format version decides whether this version can read the
        # file: newer Otripy versions write older formats when they can.
        saved_format_version = Version(journey["format_version"])
        if Version(CURRENT_FORMAT_VERSION) < saved_format_version:
            raise ValueError(f"Loading file from Otripy file format version {saved_format_version} while we are at format version {CURRENT_FORMAT_VERSION} is forbidden.\nPlease update Otripy.")

        self._created_at = journey["created_at"]

        self._locations = [Location.from_data(loc) for loc in journey["locations"]]
        self._groups = [Group.from_data(group) for group in journey.get("groups", [])]
        self.notes = TripNotes(note_from_data(journey["notes"])) if "notes" in journey else TripNotes()
        self.normalize_order()

    @classmethod
    def from_file(cls, path):
        """Load a journey from a JSON file. Raises OSError or ValueError."""
        return cls.from_json_str(Path(path).read_text(encoding="utf-8"))

    def to_json_str(self) -> str:
        buffer = io.StringIO()
        self.write_to_file(buffer)
        return buffer.getvalue()

    def save(self, path):
        """Write the journey to a JSON file. Raises OSError."""
        Path(path).write_text(self.to_json_str(), encoding="utf-8")

    def write_to_file(self, file: TextIO):
        iso_timestamp = datetime.now(timezone.utc).isoformat()

        locations = [loc.to_dict() for loc in self._locations]
        # logger.info(f"Journey.write_to_file locations: {locations}")
        uses_1_1 = self.uses_format_1_1()
        data = {
            "format": "otripy",
            "description": "A Journey with Otripy",  # A brief description of the data.
            # The version of the JSON format itself, which may evolve separately from the application:
            # the oldest one that can hold this journey, so that more Otripy versions can read it
            "format_version": CURRENT_FORMAT_VERSION if uses_1_1 else BASE_FORMAT_VERSION,
            "app_version": __version__,  # The version of the application that generated the file.
            "app_name": "Otripy",  # The name of the application that created the file.
            "created_at": self._created_at if self._created_at is not None else iso_timestamp,  # Timestamp when the file was created (ISO 8601 format).
            "updated_at": iso_timestamp,  # Timestamp of the last update.
            "encoding": "UTF-8",  # If the text has a specific encoding (e.g., "UTF-8").
            "settings": {},  # If the JSON file stores configuration, a settings section.
            "locations": locations
            }
        if uses_1_1:
            data["notes"] = self.notes.note
            data["groups"] = [group.to_dict() for group in self._groups]
        json.dump(data, file, indent=4)

    # Data that could be added later in the format
    # "author": "",  # Name or identifier of the creator.
    # "license": ""  # License information if applicable.
    # "schema": "",  # (Optional) A reference to a JSON Schema for validation.
    # "checksum": "",  # A hash (e.g., SHA-256) of the data to verify integrity.
    # "compression": "",  # If data is compressed, specify the method (e.g., "gzip").
    # "dependencies": "",  # If the file depends on external resources or plugins, list them.
