"""Generation of the Leaflet map page and of the JavaScript snippets that update it.

The page talks back to Python through a QWebChannel on which a MapBridge is
registered as "mapBridge".
"""
import html
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
DEFAULT_ZOOM = 12
ROUTE_COLOR = "#3b6fd8"
# Do not zoom closer than street level when fitting a few nearby locations
FIT_MAX_ZOOM = 15
DEFAULT_MARKER_COLOR = "blue"
HIGHLIGHT_ICON_URL = "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png"


class MapBridge(QObject):
    """Object exposed to the map page; relays its events as Qt signals."""
    mapClicked = Signal(float, float)  # latitude, longitude
    markerClicked = Signal(str)  # location id
    markerHovered = Signal(str)  # location id, or "" when the mouse leaves the marker
    viewChanged = Signal(float, float, int)  # center latitude, center longitude, zoom

    @Slot(float, float)
    def on_map_clicked(self, lat, lon):
        self.mapClicked.emit(lat, lon)

    @Slot(str)
    def on_marker_clicked(self, marker_id):
        self.markerClicked.emit(marker_id)

    @Slot(str)
    def on_marker_hovered(self, marker_id):
        self.markerHovered.emit(marker_id)

    @Slot(float, float, int)
    def on_view_changed(self, lat, lon, zoom):
        self.viewChanged.emit(lat, lon, zoom)


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


def tooltip_html(loc: Location) -> str:
    """Return a marker's tooltip: the location's title and a preview of its note, escaped."""
    preview = loc.preview()
    text = f"<b>{loc.to_html()}</b>"
    if preview:
        text += "<br>" + html.escape(preview).replace("\n", "<br>")
    return text


def hover_marker_js(marker_id: str, hovered: bool) -> str:
    """Return JavaScript showing or hiding a marker's hover highlight and tooltip."""
    return f"hoverMarker({js_string(marker_id)}, {'true' if hovered else 'false'});"


def update_marker_text_js(loc: Location) -> str:
    """Return JavaScript updating a marker's tooltip and popup to the location's current note.

    Leaflet renders both as HTML: give them escaped text.
    """
    return f"""
    if (window.markerMap[{js_string(loc.lid)}]) {{
        window.markerMap[{js_string(loc.lid)}].setTooltipContent({js_string(tooltip_html(loc))});
        window.markerMap[{js_string(loc.lid)}].setPopupContent({js_string(loc.to_html())});
    }}
    """


def move_map_js(lat: float, lon: float) -> str:
    return f"moveMap({float(lat)}, {float(lon)});"


def build_map_html(locations: Iterable[Location], fit_all: bool = False, view=None, route=None) -> str:
    """Return the full HTML page showing the locations.

    With fit_all, the map is zoomed to show all the locations. Otherwise it shows
    view, a (latitude, longitude, zoom) tuple, if given, else it is centered on
    the last location. route is a list of (latitude, longitude) points drawn as a line.
    """
    locations = list(locations)
    if view is not None and not fit_all:
        center, zoom = [float(view[0]), float(view[1])], int(view[2])
    else:
        center, zoom = (locations[-1].location() if locations else DEFAULT_CENTER), DEFAULT_ZOOM
    m = folium.Map(location=center, zoom_start=zoom)
    if fit_all and len(locations) > 1:
        lats = [loc.lat for loc in locations]
        lons = [loc.lon for loc in locations]
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(30, 30), max_zoom=FIT_MAX_ZOOM)
    m.get_root().html.add_child(
        JavascriptLink('qrc:///qtwebchannel/qwebchannel.js'))
    # Hover highlight of markers (Leaflet positions them with transform: use a filter)
    m.get_root().header.add_child(Element(
        "<style>.otripy-hover { filter: drop-shadow(0 0 6px #ffd400) brightness(1.15); z-index: 10000 !important; }</style>"))
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

    // Hover highlight of a marker, when its location is hovered in the list
    function hoverMarker(id, hovered) {
        let marker = window.markerMap && window.markerMap[id];
        if (!marker) {
            return;
        }
        let element = marker.getElement();
        if (element) {
            element.classList.toggle("otripy-hover", hovered);
        }
        if (hovered) {
            marker.openTooltip();
        } else {
            marker.closeTooltip();
        }
    }

    // Tell Python where the map is, so that redrawing it keeps the view.
    function reportView() {
        let mapElement = document.querySelector("div[id^='map_']");
        let bridge = pywebchannel.objects && pywebchannel.objects.mapBridge;
        if (mapElement && bridge) {
            let map = window[mapElement.id];
            let center = map.getCenter();
            bridge.on_view_changed(center.lat, center.lng, map.getZoom());
        }
    }

    pywebchannel = new QWebChannel(qt.webChannelTransport, function(channel) {
        if (!channel.objects.mapBridge) {
            console.error("mapBridge is not available.");
        }
        // The map may have settled before the channel was ready
        reportView();
    });

    document.addEventListener("DOMContentLoaded", function() {
        window.markerMap = {};
        let mapElement = document.querySelector("div[id^='map_']");
        if (mapElement) {
            let map = window[mapElement.id];
            map.on("click", function(event) {
                pywebchannel.objects.mapBridge.on_map_clicked(event.latlng.lat, event.latlng.lng);
            });
            map.on("moveend", reportView);
    """
    for loc in locations:
        logger.debug(f"Adding location to map: {repr(loc)}")
        script += f"""
            var marker = L.marker([{float(loc.lat)}, {float(loc.lon)}], {{icon: {marker_icon_js(loc)}}}).addTo(map)
                .bindTooltip({js_string(tooltip_html(loc))}, {{permanent: false}})
                .bindPopup({js_string(loc.to_html())});
            window.markerMap[{js_string(loc.lid)}] = marker;
            marker.on("mouseover", function() {{
                pywebchannel.objects.mapBridge.on_marker_hovered({js_string(loc.lid)});
            }});
            marker.on("mouseout", function() {{
                pywebchannel.objects.mapBridge.on_marker_hovered("");
            }});
            marker.on("click", function() {{
                pywebchannel.objects.mapBridge.on_marker_clicked({js_string(loc.lid)});
            }});
        """
    script += """
        }
    });
    """
    m.get_root().script.add_child(Element(script))
    if route:
        folium.PolyLine([[float(lat), float(lon)] for lat, lon in route], color=ROUTE_COLOR, weight=5, opacity=0.7).add_to(m)
    m.add_child(folium.ClickForMarker(popup="Click location"))

    data = io.BytesIO()
    m.save(data, close_file=False)
    return data.getvalue().decode()
