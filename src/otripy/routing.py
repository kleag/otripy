"""Distances and routes between locations (issues #3 and #6).

Routes come from the OSRM servers run by FOSSGIS for openstreetmap.org
(https://routing.openstreetmap.de). Their usage policy asks for a valid user
agent, at most one request per second, no heavy usage, and an attribution with
a link to fix the map (see attribution_html).
"""
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, List, Sequence, Tuple

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication

try:
    from . import __version__
except ImportError:
    from __init__ import __version__

SERVER = "https://routing.openstreetmap.de"
# Mode -> (label, server path); the FOSSGIS servers use one OSRM instance per profile.
# Labels are translated when shown, with mode_label().
MODES = {
    "car": (QT_TRANSLATE_NOOP("Routing", "Car"), "routed-car"),
    "bike": (QT_TRANSLATE_NOOP("Routing", "Bicycle"), "routed-bike"),
    "foot": (QT_TRANSLATE_NOOP("Routing", "Foot"), "routed-foot"),
}
USER_AGENT = f"Otripy/{__version__} (+https://github.com/kleag/otripy)"
TIMEOUT = 20  # seconds
MIN_INTERVAL = 1.0  # seconds between requests, per the usage policy
def mode_label(mode: str) -> str:
    """The translated label of a mode of MODES."""
    return QCoreApplication.translate("Routing", MODES[mode][0])


def attribution_html() -> str:
    """The attribution required by the routing service, translated."""
    return QCoreApplication.translate(
        "Routing",
        'Routes by <a href="https://routing.openstreetmap.de/about.html">FOSSGIS OSRM</a>, '
        'data © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> '
        '(<a href="https://www.openstreetmap.org/fixthemap">fix the map</a>)')
EARTH_RADIUS = 6371008.8  # meters, mean radius

Point = Tuple[float, float]  # latitude, longitude


class RoutingError(Exception):
    """The route could not be computed; the message is meant for the user."""


@dataclass
class Route:
    distance: float  # meters
    duration: float  # seconds
    legs: List[Tuple[float, float]]  # (distance, duration) between consecutive points
    geometry: List[Point]  # the path, as (latitude, longitude) points


def straight_distance(a: Point, b: Point) -> float:
    """Great-circle distance between two points, in meters."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS * math.asin(math.sqrt(h))


def format_distance(meters: float) -> str:
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000:.1f} km" if meters < 100_000 else f"{meters / 1000:.0f} km"


def format_duration(seconds: float) -> str:
    minutes = round(seconds / 60)
    if minutes < 60:
        return QCoreApplication.translate("Routing", "{minutes} min").format(minutes=minutes)
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return QCoreApplication.translate("Routing", "{hours} h {minutes:02d}").format(hours=hours, minutes=minutes)
    return QCoreApplication.translate("Routing", "{days} d {hours} h {minutes:02d}").format(
        days=hours // 24, hours=hours % 24, minutes=minutes)


_last_request = 0.0


def _wait_for_rate_limit():
    global _last_request
    delay = _last_request + MIN_INTERVAL - time.monotonic()
    if delay > 0:
        time.sleep(delay)
    _last_request = time.monotonic()


def _fetch_json(url: str) -> dict:
    _wait_for_rate_limit()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.load(response)
    except urllib.error.HTTPError as e:
        # OSRM answers errors with a JSON body too
        try:
            return json.load(e)
        except ValueError:
            raise RoutingError(QCoreApplication.translate("Routing", "The routing server answered: {status}").format(
                status=f"{e.code} {e.reason}")) from e
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise RoutingError(QCoreApplication.translate("Routing", "The routing server could not be reached: {error}").format(
            error=e)) from e


def route_url(points: Sequence[Point], mode: str) -> str:
    path = MODES[mode][1]
    coordinates = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in points)
    query = urllib.parse.urlencode({"overview": "full", "geometries": "geojson"})
    return f"{SERVER}/{path}/route/v1/driving/{coordinates}?{query}"


def fetch_route(points: Sequence[Point], mode: str, fetch_json: Callable[[str], dict] = _fetch_json) -> Route:
    """Return the route through the points, in order, for a mode of MODES."""
    if mode not in MODES:
        raise ValueError(f"Unknown mode {mode}")
    if len(points) < 2:
        raise RoutingError(QCoreApplication.translate("Routing", "A route needs at least two locations."))
    data = fetch_json(route_url(points, mode))
    if data.get("code") != "Ok" or not data.get("routes"):
        message = data.get("message") or data.get("code") or ""
        raise RoutingError(QCoreApplication.translate("Routing", "No route found: {reason}").format(reason=message))
    route = data["routes"][0]
    return Route(
        distance=route["distance"],
        duration=route["duration"],
        legs=[(leg["distance"], leg["duration"]) for leg in route["legs"]],
        geometry=[(lat, lon) for lon, lat in route["geometry"]["coordinates"]],
    )
