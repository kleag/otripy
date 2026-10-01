import html
import logging
import re
import uuid

from typing import Dict

logger = logging.getLogger(__name__)

# A backslash before an ASCII punctuation character, as written by QTextDocument.toMarkdown
MARKDOWN_ESCAPE = r'\\([!-/:-@\[-`{-~])'

class Location:
    """A place of a journey: coordinates, a note, and how its marker looks.

    The note is a dict with the note's text in "markdown" and its images in
    "images" (name -> base64 PNG); the first line of the text is the location's
    label. marker is a Font Awesome icon name without its "fa-" prefix and color
    a Leaflet.awesome-markers color; None means the defaults (a blue circle).
    See docs/file-format.md for the saved form.
    """

    def __init__(self,
                 lat: float = 0.0,
                 lon: float = 0.0,
                 note: Dict[str, str] = None,
                 id: str = None,
                 marker: str = None,
                 color: str = None):
        logger.info(f"Location({lat}, {lon}, {note}, {id})")
        self.lid = id if id is not None else str(uuid.uuid4())
        self.lat = lat
        self.lon = lon
        self.note = note if note is not None else {"markdown": ""}
        self.marker = marker
        self.color = color

    def __str__(self):
        return self.label()

    def __repr__(self):
        return f"{self.lid}: [{self.lat}, {self.lon}]\n{self.marker}, {self.color}\n{self.note}"

    @classmethod
    def from_data(cls, data: Dict[str, str | dict]):
        logger.info(f"Location.from_data({data})")
        lat = float(data["lat"]) if "lat" in data else 0.0
        lon = float(data["lon"]) if "lon" in data else 0.0
        note = data["note"] if "note" in data else {"markdown": ""}
        if type(note) is str:
            note = {"markdown": note}
        id = data["id"] if "id" in data else None
        marker = data["marker"] if "marker" in data and data["marker"] else None
        color = data["color"] if "color" in data and data["color"] else None
        return cls(lat, lon, note, id, marker, color)

    def label(self):
        """Return the first line of the note as plain text: heading marks and markdown escapes removed."""
        the_label = self.note["markdown"].split('\n')[0]
        the_label = re.sub(r'^#+ ?', '', the_label)
        return re.sub(MARKDOWN_ESCAPE, r'\1', the_label)

    def to_html(self):
        return html.escape(self.label())

    def location(self):
        return [self.lat, self.lon]

    def to_dict(self):
        return {
            "id": self.lid,
            "lat": self.lat,
            "lon": self.lon,
            "note": self.note,
            "marker": self.marker,
            "color": self.color
            }
