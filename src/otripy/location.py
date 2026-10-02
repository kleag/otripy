import html
import logging
import re
import uuid

from typing import Dict

logger = logging.getLogger(__name__)

# A backslash before an ASCII punctuation character, as written by QTextDocument.toMarkdown
MARKDOWN_ESCAPE = r'\\([!-/:-@\[-`{-~])'

def empty_note() -> dict:
    return {"markdown": "", "images": {}}


class NoteHolder:
    """Something with a note: a location, a group of locations, or the trip itself.

    The note is a dict with the note's text in "markdown" and its images in
    "images" (name -> base64 PNG); the first line of the text is its label.
    """
    note: dict

    def label(self):
        """Return the first line of the note as plain text: heading marks and markdown escapes removed."""
        the_label = self.note["markdown"].split('\n')[0]
        the_label = re.sub(r'^#+ ?', '', the_label)
        # bold (**, __) and strikethrough (~~) written by Qt around formatted words
        the_label = re.sub(r'(?<!\\)(\*\*|__|~~)(.+?)(?<!\\)\1', r'\2', the_label)
        return re.sub(MARKDOWN_ESCAPE, r'\1', the_label)

    def to_html(self):
        return html.escape(self.label())

    def preview(self, max_lines: int = 3, max_chars: int = 200) -> str:
        """Return the first lines of the note after its title, as plain text."""
        lines = []
        for line in self.note["markdown"].split("\n")[1:]:
            line = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line)  # images
            line = re.sub(r"^\s*(#+|[-*+]|\d+\.)\s+", "", line)  # headings, list marks
            line = re.sub(r"(\*\*|__|~~|\*|_)", "", line)  # emphasis marks
            line = re.sub(MARKDOWN_ESCAPE, r"\1", line).strip()
            if line:
                lines.append(line)
            if len(lines) == max_lines:
                break
        text = "\n".join(lines)
        return text if len(text) <= max_chars else text[:max_chars - 1].rstrip() + "…"

    def has_note(self) -> bool:
        return bool(self.note.get("markdown", "").strip() or self.note.get("images"))


def note_from_data(note) -> dict:
    """Normalize a saved note: plain strings (old files) become note dicts."""
    if note is None:
        return {"markdown": ""}
    return {"markdown": note} if isinstance(note, str) else note


class Location(NoteHolder):
    """A place of a journey: coordinates, a note, and how its marker looks.

    The note is a dict with the note's text in "markdown" and its images in
    "images" (name -> base64 PNG); the first line of the text is the location's
    label. marker is a Font Awesome icon name without its "fa-" prefix and color
    a Leaflet.awesome-markers color; None means the defaults (a blue circle).
    group is the id of the Group the location belongs to, or None.
    See docs/file-format.md for the saved form.
    """

    def __init__(self,
                 lat: float = 0.0,
                 lon: float = 0.0,
                 note: Dict[str, str] = None,
                 id: str = None,
                 marker: str = None,
                 color: str = None,
                 group: str = None):
        logger.info(f"Location({lat}, {lon}, {note}, {id})")
        self.lid = id if id is not None else str(uuid.uuid4())
        self.lat = lat
        self.lon = lon
        self.note = note if note is not None else {"markdown": ""}
        self.marker = marker
        self.color = color
        self.group = group

    def __str__(self):
        return self.label()

    def __repr__(self):
        return f"{self.lid}: [{self.lat}, {self.lon}]\n{self.marker}, {self.color}\n{self.note}"

    @classmethod
    def from_data(cls, data: Dict[str, str | dict]):
        logger.info(f"Location.from_data({data})")
        lat = float(data["lat"]) if "lat" in data else 0.0
        lon = float(data["lon"]) if "lon" in data else 0.0
        note = note_from_data(data.get("note"))
        id = data["id"] if "id" in data else None
        marker = data["marker"] if "marker" in data and data["marker"] else None
        color = data["color"] if "color" in data and data["color"] else None
        return cls(lat, lon, note, id, marker, color, data.get("group") or None)

    def location(self):
        return [self.lat, self.lon]

    def to_dict(self):
        return {
            "id": self.lid,
            "lat": self.lat,
            "lon": self.lon,
            "note": self.note,
            "marker": self.marker,
            "color": self.color,
            **({"group": self.group} if self.group else {}),  # format 1.1.0
            }


class Group(NoteHolder):
    """A titled section of the location list (issue #18).

    The locations whose group is this group's id follow its title row in the
    list. Its note's first line is its title, like a location's.
    """

    def __init__(self, note: dict = None, id: str = None, collapsed: bool = False):
        self.gid = id if id is not None else str(uuid.uuid4())
        self.note = note if note is not None else {"markdown": ""}
        self.collapsed = collapsed

    def __repr__(self):
        return f"Group({self.gid}: {self.label()!r})"

    @classmethod
    def from_data(cls, data: dict):
        return cls(note_from_data(data.get("note")), data.get("id"), bool(data.get("collapsed", False)))

    def to_dict(self):
        return {"id": self.gid, "note": self.note, "collapsed": self.collapsed}


class TripNotes(NoteHolder):
    """The trip's general notes, not linked to a location (issue #19)."""

    def __init__(self, note: dict = None):
        self.note = note if note is not None else {"markdown": ""}


class Leg:
    """A route between two locations, with its own travel mode (issue #50).

    start and end are location ids; mode is a key of routing.MODES. The route's
    length (meters), duration (seconds) and path ((latitude, longitude) points)
    are kept, so that it shows again without asking the routing server.
    """

    def __init__(self, start: str, end: str, mode: str, distance: float = 0.0, duration: float = 0.0,
                 geometry=None, id: str = None):
        self.leg_id = id if id is not None else str(uuid.uuid4())
        self.start = start
        self.end = end
        self.mode = mode
        self.distance = distance
        self.duration = duration
        self.geometry = [(float(lat), float(lon)) for lat, lon in (geometry or [])]

    def __repr__(self):
        return f"Leg({self.start} -> {self.end}, {self.mode})"

    def joins(self, a: str, b: str) -> bool:
        """Whether the leg goes between the two locations, in either direction."""
        return {self.start, self.end} == {a, b}

    @classmethod
    def from_data(cls, data: dict):
        return cls(data["from"], data["to"], data["mode"], float(data.get("distance", 0)),
                   float(data.get("duration", 0)), data.get("geometry", []), data.get("id"))

    def to_dict(self):
        return {"id": self.leg_id, "from": self.start, "to": self.end, "mode": self.mode,
                "distance": round(self.distance, 1), "duration": round(self.duration, 1),
                "geometry": [[round(lat, 6), round(lon, 6)] for lat, lon in self.geometry]}
