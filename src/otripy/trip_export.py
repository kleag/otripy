"""Export a journey for map apps on phones (issue #47).

* KMZ, for Organic Maps (https://organicmaps.app): a zip of KML files, each of
  which Organic Maps imports as a separate bookmark list. The ungrouped
  locations form a list named after the trip, and each group its own list.
  Bookmarks carry the note as HTML, one of Organic Maps' predefined colors
  (styleUrl "#placemark-<color>") and, when there is a close match, one of its
  icons (<mwm:icon> in ExtendedData).
* GPX, for OsmAnd and other apps: waypoints with the note as text and their
  group as type, which OsmAnd uses as favorites group.

The routes between locations (issue #50) are exported as tracks: in the KMZ,
in the list of their starting location. Images stay in Otripy: these apps do
not show images in bookmark descriptions.
"""
import io
import re
import zipfile
from typing import List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape

import markdown as markdown_lib
from PySide6.QtCore import QCoreApplication

try:
    from . import routing
    from .journey import Journey
    from .limited_color_picker import LimitedColorPicker
    from .location import MARKDOWN_ESCAPE, Location, NoteHolder
except ImportError:
    import routing
    from journey import Journey
    from limited_color_picker import LimitedColorPicker
    from location import MARKDOWN_ESCAPE, Location, NoteHolder

Point = Tuple[float, float]  # latitude, longitude

# Otripy marker colors (Leaflet.awesome-markers) -> the 16 Organic Maps bookmark colors
ORGANIC_COLORS = {
    None: "blue", "blue": "blue", "darkblue": "deeppurple", "lightblue": "lightblue", "cadetblue": "bluegray",
    "red": "red", "darkred": "brown", "lightred": "pink", "pink": "pink", "orange": "orange",
    "green": "green", "darkgreen": "teal", "lightgreen": "lime", "purple": "purple",
    "white": "gray", "gray": "gray", "black": "bluegray",
}

# Font Awesome icons used as Otripy markers -> Organic Maps bookmark icons, when they mean the same
ORGANIC_ICONS = {
    "bed": "Hotel", "hotel": "Hotel", "house": "Hotel", "tent": "Hotel", "campground": "Hotel", "caravan": "Hotel",
    "utensils": "Food", "bowl-food": "Food", "pizza-slice": "Food", "fish": "Food",
    "burger": "FastFood", "hotdog": "FastFood",
    "mug-hot": "Cafe", "mug-saucer": "Cafe",
    "martini-glass": "Bar", "martini-glass-citrus": "Bar", "wine-glass": "Bar", "champagne-glasses": "Bar",
    "beer-mug-empty": "Pub",
    "landmark": "Sights", "monument": "Sights", "archway": "Sights", "camera": "Sights", "camera-retro": "Sights",
    "chess-rook": "Sights",
    "binoculars": "Viewpoint", "eye": "Viewpoint",
    "building-columns": "Museum",
    "palette": "Art", "paintbrush": "Art", "masks-theater": "Theatre", "ticket": "Entertainment",
    "film": "Entertainment", "music": "Entertainment",
    "mountain": "Mountain", "mountain-sun": "Mountain", "person-hiking": "Mountain",
    "tree": "Park", "leaf": "Park", "seedling": "Park",
    "water": "Water", "droplet": "Water", "person-swimming": "Swim", "water-ladder": "Swim", "umbrella-beach": "Swim",
    "square-parking": "Parking", "car": "Parking",
    "bus": "Transport", "bus-simple": "Transport", "train": "Transport", "train-subway": "Transport",
    "train-tram": "Transport", "ship": "Transport", "ferry": "Transport", "taxi": "Transport",
    "plane": "Airport", "plane-departure": "Airport", "plane-arrival": "Airport",
    "gas-pump": "Gas", "charging-station": "ChargingStation", "plug": "ChargingStation",
    "bicycle": "BicycleRental",
    "cart-shopping": "Shop", "bag-shopping": "Shop", "basket-shopping": "Shop", "store": "Shop", "shop": "Shop",
    "hospital": "Medicine", "house-medical": "Medicine", "kit-medical": "Medicine", "stethoscope": "Medicine",
    "prescription-bottle-medical": "Pharmacy", "pills": "Pharmacy",
    "money-bill": "Exchange", "coins": "Exchange", "money-bill-transfer": "Exchange",
    "circle-info": "Information", "circle-question": "Information",
    "church": "Christianity", "cross": "Christianity", "mosque": "Islam", "synagogue": "Judaism",
    "star-of-david": "Judaism", "vihara": "Buddhism", "dharmachakra": "Buddhism",
    "paw": "Animals", "hippo": "Animals", "otter": "Animals", "horse": "Animals", "dove": "Animals",
    "futbol": "Sport", "volleyball": "Sport", "basketball": "Sport", "person-running": "Sport",
    "building": "Building", "city": "Building",
}

IMAGE_REF = re.compile(r"!\[[^\]]*\]\([^)]*\)")
AUTOLINK = re.compile(r"<(https?://[^>\s]+)>")


# Notes

def note_body(holder: NoteHolder) -> str:
    """The markdown of a note after its first line, which is its title, without images."""
    body = holder.note.get("markdown", "").split("\n", 1)
    return IMAGE_REF.sub("", body[1] if len(body) > 1 else "").strip()


def markdown_to_html(text: str) -> str:
    """HTML for bookmark descriptions: notes' formatting and links, no raw HTML."""
    text = AUTOLINK.sub(r"[\1](\1)", text)
    text = text.replace("<", "&lt;")  # notes are text: any < is literal
    return markdown_lib.markdown(text).strip()


def markdown_to_text(text: str) -> str:
    """Plain text for GPX descriptions."""
    text = re.sub(r"\[([^\]]*)\]\(([^)]*)\)", r"\1 (\2)", text)  # links: text (url)
    text = AUTOLINK.sub(r"\1", text)
    text = re.sub(r"^\s*#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"(\*\*|__|~~)(.+?)\1", r"\2", text)
    text = re.sub(MARKDOWN_ESCAPE, r"\1", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# Sections: what becomes a list (KMZ) or a waypoint type (GPX)

def sections(journey: Journey, trip_name: str) -> List[Tuple[str, Optional[NoteHolder], List[Location]]]:
    """(name, note holder for its description, locations) for the ungrouped locations and each group."""
    result = [(trip_name, journey.notes, journey.group_locations(None))]
    for group in journey.groups:
        title = group.label() or "…"
        result.append((f"{trip_name} – {title}", group, journey.group_locations(group)))
    return result


# KML / KMZ

def _cdata(text: str) -> str:
    return "<![CDATA[" + text.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def _style_definitions() -> str:
    """Styles for apps other than Organic Maps, which only reads the styleUrl names."""
    styles = []
    for name in sorted(set(ORGANIC_COLORS.values())):
        styles.append(f'  <Style id="placemark-{name}"><IconStyle><Icon><href>'
                      f'https://omaps.app/placemarks/placemark-{name}.png</href></Icon></IconStyle></Style>')
    styles.append('  <Style id="route"><LineStyle><color>ffd86f3b</color><width>5</width></LineStyle></Style>')
    return "\n".join(styles)


def _placemark(location: Location) -> str:
    color = ORGANIC_COLORS.get(location.color, "blue")
    parts = [f"  <Placemark>\n    <name>{escape(location.label() or '…')}</name>"]
    description = markdown_to_html(note_body(location))
    if description:
        parts.append(f"    <description>{_cdata(description)}</description>")
    parts.append(f"    <styleUrl>#placemark-{color}</styleUrl>")
    parts.append(f"    <Point><coordinates>{float(location.lon):.6f},{float(location.lat):.6f}</coordinates></Point>")
    icon = ORGANIC_ICONS.get(location.marker or "")
    if icon:
        parts.append(f'    <ExtendedData xmlns:mwm="https://omaps.app"><mwm:icon>{icon}</mwm:icon></ExtendedData>')
    parts.append("  </Placemark>")
    return "\n".join(parts)


def leg_name(journey: Journey, leg) -> str:
    """'Dublin → Galway (Car)'."""
    start, end = journey.loc_by_id(leg.start), journey.loc_by_id(leg.end)
    return QCoreApplication.translate("Export", "{start} → {end} ({mode})").format(
        start=start.label() if start else "?", end=end.label() if end else "?", mode=routing.mode_label(leg.mode))


def _track(name: str, route: Sequence[Point]) -> str:
    coordinates = " ".join(f"{float(lon):.6f},{float(lat):.6f}" for lat, lon in route)
    return (f"  <Placemark>\n    <name>{escape(name)}</name>\n    <styleUrl>#route</styleUrl>\n"
            f"    <LineString><coordinates>{coordinates}</coordinates></LineString>\n  </Placemark>")


def kml_document(name: str, description_html: str, locations: Sequence[Location],
                 tracks: Sequence[Tuple[str, Sequence[Point]]] = ()) -> str:
    """One KML document, which Organic Maps imports as one bookmark list."""
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<kml xmlns="http://www.opengis.net/kml/2.2">',
             "<Document>",
             f"  <name>{escape(name)}</name>"]
    if description_html:
        parts.append(f"  <description>{_cdata(description_html)}</description>")
    parts.append(_style_definitions())
    parts.extend(_placemark(location) for location in locations)
    parts.extend(_track(track_name, points) for track_name, points in tracks if len(points) > 1)
    parts += ["</Document>", "</kml>", ""]
    return "\n".join(parts)


def _file_name(index: int, name: str) -> str:
    safe = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name).strip() or "list"
    return f"{index:02d} {safe[:80]}.kml"


def build_kmz(journey: Journey, trip_name: str, include_routes: bool = True) -> bytes:
    """A KMZ archive with one KML document per non-empty section; routes go with their start."""
    documents = []
    for name, holder, locations in sections(journey, trip_name):
        description = markdown_to_html(note_body(holder)) if holder is not None else ""
        ids = {loc.lid for loc in locations}
        tracks = [(leg_name(journey, leg), leg.geometry) for leg in journey.legs
                  if include_routes and leg.start in ids]
        if locations or (holder is journey.notes and description):
            documents.append((name, description, locations, tracks))
    if not documents:
        documents.append((trip_name, "", [], []))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for index, (name, description, locations, tracks) in enumerate(documents):
            archive.writestr(_file_name(index, name), kml_document(name, description, locations, tracks).encode("utf-8"))
    return buffer.getvalue()


# GPX

def build_gpx(journey: Journey, trip_name: str, include_routes: bool = True) -> bytes:
    """A GPX 1.1 file: a waypoint per location, typed by its group, and a track per route."""
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<gpx version="1.1" creator="Otripy" xmlns="http://www.topografix.com/GPX/1/1"',
             '     xmlns:osmand="https://osmand.net">',
             f"  <metadata>\n    <name>{escape(trip_name)}</name>"]
    trip_description = markdown_to_text(note_body(journey.notes))
    if trip_description:
        parts.append(f"    <desc>{escape(trip_description)}</desc>")
    parts.append("  </metadata>")
    for name, holder, locations in sections(journey, trip_name):
        group_type = name if holder is not journey.notes else trip_name
        for location in locations:
            parts.append(f'  <wpt lat="{float(location.lat):.6f}" lon="{float(location.lon):.6f}">')
            parts.append(f"    <name>{escape(location.label() or '…')}</name>")
            description = markdown_to_text(note_body(location))
            if description:
                parts.append(f"    <desc>{escape(description)}</desc>")
            parts.append(f"    <type>{escape(group_type)}</type>")
            rgb = LimitedColorPicker.COLORS.get(location.color or "blue", LimitedColorPicker.COLORS["blue"])
            parts.append("    <extensions><osmand:color>#{:02x}{:02x}{:02x}</osmand:color></extensions>".format(*rgb))
            parts.append("  </wpt>")
    for leg in journey.legs if include_routes else []:
        if len(leg.geometry) < 2:
            continue
        parts.append(f"  <trk>\n    <name>{escape(leg_name(journey, leg))}</name>\n    <trkseg>")
        parts.extend(f'      <trkpt lat="{float(lat):.6f}" lon="{float(lon):.6f}"/>' for lat, lon in leg.geometry)
        parts.append("    </trkseg>\n  </trk>")
    parts += ["</gpx>", ""]
    return "\n".join(parts).encode("utf-8")
