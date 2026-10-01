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
    from .location import Location
except ImportError:
    from __init__ import __version__
    from location import Location

logger = logging.getLogger(__name__)

CURRENT_FORMAT_VERSION = "1.0.0"
class Journey(QObject):
    """An ordered list of Locations, the document Otripy edits and saves.

    It behaves like a list (indexing, iteration, len, append, insert, remove,
    pop) and emits dirty(True) on every change, dirty(False) once saved or
    cleared. It reads and writes the JSON format described in
    docs/file-format.md, including the legacy pre-1.0.0 one.
    """
    dirty = Signal(bool)  # True when modified since last saved

    def __init__(self, locations: List[Location] = None, parent=None):
        """Initialize the journey with a list of Location objects."""
        super().__init__(parent)
        self._locations = locations if locations is not None else []
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

    def clear(self):
        self._locations.clear()
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

        current_app_version = Version(__version__)
        saved_app_version = Version(journey["app_version"])
        if current_app_version < saved_app_version:
            raise ValueError(f"Loading file from Otripy version {saved_app_version} while we are at version {current_app_version} is forbidden.\nPlease update Otripy.")

        saved_format_version = Version(journey["format_version"])
        if Version(CURRENT_FORMAT_VERSION) < saved_format_version:
            raise ValueError(f"Loading file from Otripy file format version {saved_format_version} while we are at format version {CURRENT_FORMAT_VERSION} is forbidden.\nPlease update Otripy.")

        self._created_at = journey["created_at"]

        self._locations = [Location.from_data(loc) for loc in journey["locations"]]

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
        data = {
            "format": "otripy",
            "description": "A Journey with Otripy",  # A brief description of the data.
            "format_version": CURRENT_FORMAT_VERSION,  # The version of the JSON format itself, which may evolve separately from the application.
            "app_version": __version__,  # The version of the application that generated the file.
            "app_name": "Otripy",  # The name of the application that created the file.
            "created_at": self._created_at if self._created_at is not None else iso_timestamp,  # Timestamp when the file was created (ISO 8601 format).
            "updated_at": iso_timestamp,  # Timestamp of the last update.
            "encoding": "UTF-8",  # If the text has a specific encoding (e.g., "UTF-8").
            "settings": {},  # If the JSON file stores configuration, a settings section.
            "locations": locations
            }
        json.dump(data, file, indent=4)

    # Data that could be added later in the format
    # "author": "",  # Name or identifier of the creator.
    # "license": ""  # License information if applicable.
    # "schema": "",  # (Optional) A reference to a JSON Schema for validation.
    # "checksum": "",  # A hash (e.g., SHA-256) of the data to verify integrity.
    # "compression": "",  # If data is compressed, specify the method (e.g., "gzip").
    # "dependencies": "",  # If the file depends on external resources or plugins, list them.
