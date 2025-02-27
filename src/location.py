import logging
import uuid

from typing import Dict

logger = logging.getLogger(__name__)

class Location:
    def __init__(self,
                 lat: float = 0.0,
                 lon: float = 0.0,
                 note: str = "",
                 id: str = str(uuid.uuid4())):
        logger.info(f"Location({lat}, {lon}, {note}, {id})")
        self.id = id
        self.lat = lat
        self.lon = lon
        self.note = note

    @classmethod
    def from_data(cls, data: Dict[str, str] = {}):
        logger.info(f"Location.from_data({data})")
        lat = float(data["lat"]) if "lat" in data else 0.0
        lon = float(data["lon"]) if "lon" in data else 0.0
        note = data["note"] if "note" in data else ""
        id = data["id"] if "id" in data else str(uuid.uuid4())
        return cls(lat, lon, note,id)

    def label(self):
        return self.note.split('\n')[0]

    def to_html(self):
        return self.note.split('\n')[0].replace("\n", "<br>")

    def location(self):
        return [self.lat, self.lon]

    def to_dict(self):
        return {
            "id": self.id,
            "lat": self.lat,
            "lon": self.lon,
            "note": self.note
            }
