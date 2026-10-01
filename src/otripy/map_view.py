"""Generation of the Leaflet map page and of the JavaScript snippets that update it.

The page talks back to Python through a QWebChannel on which a MapBridge is
registered as "mapBridge".
"""
import io
import json
import logging
from typing import Iterable

import folium
from branca.element import Element
from folium.elements import JavascriptLink
from PySide6.QtCore import QObject, Signal, Slot

try:
    from .location import Location
except ImportError:
    from location import Location

logger = logging.getLogger(__name__)

DEFAULT_CENTER = [48.8566, 2.3522]  # Paris
DEFAULT_MARKER_ICON = "circle"
# Do not zoom closer than street level when fitting a few nearby locations
FIT_MAX_ZOOM = 15
DEFAULT_MARKER_COLOR = "blue"
HIGHLIGHT_ICON_URL = "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png"


class MapBridge(QObject):
    """Object exposed to the map page; relays its events as Qt signals."""
    mapClicked = Signal(float, float)  # latitude, longitude
    markerClicked = Signal(str)  # location id

    @Slot(float, float)
    def on_map_clicked(self, lat, lon):
        self.mapClicked.emit(lat, lon)

    @Slot(str)
    def on_marker_clicked(self, marker_id):
        self.markerClicked.emit(marker_id)


def js_string(value) -> str:
    """Return value as a JavaScript string literal, safe to embed in a <script> element."""
    return json.dumps(str(value)).replace("</", "<\\/")


def marker_icon_js(loc: Location) -> str:
    """Return a JavaScript expression creating the marker icon of a location.

    Available colors: red, blue, green, orange, yellow, purple, darkred, lightred, darkblue,
    lightblue, darkgreen, lightgreen, cadetblue, white, pink, gray, black.
    """
    icon = loc.marker if loc.marker is not None else DEFAULT_MARKER_ICON
    color = loc.color if loc.color is not None else DEFAULT_MARKER_COLOR
    return f"L.AwesomeMarkers.icon({{icon: {js_string('fa-' + icon)}, markerColor: {js_string(color)}, prefix: 'fa'}})"


def highlight_marker_js(marker_id: str) -> str:
    """Return JavaScript replacing a marker's icon with the large red highlight icon."""
    return f"""
    if (window.markerMap[{js_string(marker_id)}]) {{
        window.markerMap[{js_string(marker_id)}].setIcon(L.icon({{
            iconUrl: {js_string(HIGHLIGHT_ICON_URL)},
            iconSize: [35, 55],
            iconAnchor: [17, 54],
            popupAnchor: [1, -34],
        }}));
    }}
    """


def downplay_marker_js(loc: Location) -> str:
    """Return JavaScript restoring a marker's own icon."""
    return f"""
    if (window.markerMap[{js_string(loc.lid)}]) {{
        window.markerMap[{js_string(loc.lid)}].setIcon({marker_icon_js(loc)});
    }}
    """


def update_marker_text_js(loc: Location) -> str:
    """Return JavaScript updating a marker's tooltip and popup to the location's current title.

    Leaflet renders both as HTML: give them the escaped title.
    """
    return f"""
    if (window.markerMap[{js_string(loc.lid)}]) {{
        window.markerMap[{js_string(loc.lid)}].setTooltipContent({js_string(loc.to_html())});
        window.markerMap[{js_string(loc.lid)}].setPopupContent({js_string(loc.to_html())});
    }}
    """


def move_map_js(lat: float, lon: float) -> str:
    return f"moveMap({float(lat)}, {float(lon)});"


def build_map_html(locations: Iterable[Location], fit_all: bool = False) -> str:
    """Return the full HTML page showing the locations.

    The map is centered on the last location, or, with fit_all, zoomed to show
    all of them.
    """
    locations = list(locations)
    center = locations[-1].location() if locations else DEFAULT_CENTER
    m = folium.Map(location=center, zoom_start=12)
    if fit_all and len(locations) > 1:
        lats = [loc.lat for loc in locations]
        lons = [loc.lon for loc in locations]
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(30, 30), max_zoom=FIT_MAX_ZOOM)
    m.get_root().html.add_child(
        JavascriptLink('qrc:///qtwebchannel/qwebchannel.js'))
    m.get_root().html.add_child(
        JavascriptLink('https://cdnjs.cloudflare.com/ajax/libs/leaflet.awesome-markers/2.0.4/leaflet.awesome-markers.min.js'))

    script = """
    function moveMap(lat, lng, zoom) {
        let mapElement = document.querySelector("div[id^='map_']");
        if (mapElement) {
            let map = window[mapElement.id]; // Folium stores the map as a global variable with its ID
            map.setView([lat, lng], zoom);
        }
    }

    pywebchannel = new QWebChannel(qt.webChannelTransport, function(channel) {
        if (!channel.objects.mapBridge) {
            console.error("mapBridge is not available.");
        }
    });

    document.addEventListener("DOMContentLoaded", function() {
        window.markerMap = {};
        let mapElement = document.querySelector("div[id^='map_']");
        if (mapElement) {
            let map = window[mapElement.id];
            map.on("click", function(event) {
                pywebchannel.objects.mapBridge.on_map_clicked(event.latlng.lat, event.latlng.lng);
            });
    """
    for loc in locations:
        logger.debug(f"Adding location to map: {repr(loc)}")
        script += f"""
            var marker = L.marker([{float(loc.lat)}, {float(loc.lon)}], {{icon: {marker_icon_js(loc)}}}).addTo(map)
                .bindTooltip({js_string(loc.to_html())}, {{permanent: false}})
                .bindPopup({js_string(loc.to_html())});
            window.markerMap[{js_string(loc.lid)}] = marker;
            marker.on("click", function() {{
                pywebchannel.objects.mapBridge.on_marker_clicked({js_string(loc.lid)});
            }});
        """
    script += """
        }
    });
    """
    m.get_root().script.add_child(Element(script))
    m.add_child(folium.ClickForMarker(popup="Click location"))

    data = io.BytesIO()
    m.save(data, close_file=False)
    return data.getvalue().decode()
