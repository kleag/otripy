import pytest

from otripy import routing
from otripy.routing import (Route, RoutingError, fetch_route, format_distance, format_duration, route_url,
                            straight_distance)

EIFFEL = (48.8584, 2.2945)
LOUVRE = (48.8606, 2.3376)
OPERA = (48.8720, 2.3316)


def osrm_answer(legs, coordinates):
    """A response shaped like the FOSSGIS OSRM servers' (code, routes, legs, GeoJSON geometry)."""
    return {"code": "Ok", "routes": [{
        "distance": sum(d for d, _ in legs), "duration": sum(t for _, t in legs),
        "legs": [{"distance": d, "duration": t} for d, t in legs],
        "geometry": {"type": "LineString", "coordinates": [[lon, lat] for lat, lon in coordinates]},
    }]}


def test_straight_distance():
    assert straight_distance(EIFFEL, LOUVRE) == pytest.approx(3170, rel=0.01)
    assert straight_distance((48.8566, 2.3522), (51.5074, -0.1278)) == pytest.approx(343_500, rel=0.005)  # Paris-London
    assert straight_distance(EIFFEL, EIFFEL) == 0


@pytest.mark.parametrize("meters, text", [(850, "850 m"), (4304, "4.3 km"), (343_500, "344 km")])
def test_format_distance(meters, text):
    assert format_distance(meters) == text


@pytest.mark.parametrize("seconds, text", [(634, "11 min"), (3002, "50 min"), (5400, "1 h 30"), (93_600, "1 d 2 h 00")])
def test_format_duration(seconds, text):
    assert format_duration(seconds) == text


def test_route_url_lists_points_as_lon_lat():
    url = route_url([EIFFEL, LOUVRE], "bike")
    assert url.startswith("https://routing.openstreetmap.de/routed-bike/route/v1/driving/2.294500,48.858400;2.337600,48.860600?")
    assert "geometries=geojson" in url and "overview=full" in url


def test_fetch_route_through_several_points():
    urls = []
    answer = osrm_answer([(4304, 634), (1500, 300)], [EIFFEL, (48.86, 2.31), LOUVRE, OPERA])
    route = fetch_route([EIFFEL, LOUVRE, OPERA], "car", fetch_json=lambda url: urls.append(url) or answer)
    assert len(urls) == 1, "the whole trip is one request"
    assert route == Route(distance=5804, duration=934, legs=[(4304, 634), (1500, 300)],
                          geometry=[EIFFEL, (48.86, 2.31), LOUVRE, OPERA])


def test_fetch_route_errors():
    with pytest.raises(RoutingError, match="at least two"):
        fetch_route([EIFFEL], "car", fetch_json=lambda url: {})
    with pytest.raises(RoutingError, match="Impossible route"):
        fetch_route([EIFFEL, LOUVRE], "car", fetch_json=lambda url: {"code": "NoRoute", "message": "Impossible route"})
    with pytest.raises(ValueError):
        fetch_route([EIFFEL, LOUVRE], "plane", fetch_json=lambda url: {})


def test_unreachable_server(monkeypatch):
    def fail(*args, **kwargs):
        raise routing.urllib.error.URLError("no network")
    monkeypatch.setattr(routing.urllib.request, "urlopen", fail)
    monkeypatch.setattr(routing, "MIN_INTERVAL", 0)
    with pytest.raises(RoutingError, match="could not be reached"):
        fetch_route([EIFFEL, LOUVRE], "foot")


def test_requests_are_rate_limited(monkeypatch):
    """The FOSSGIS usage policy allows one request per second."""
    now = [100.0]
    slept = []
    monkeypatch.setattr(routing.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(routing.time, "sleep", lambda s: slept.append(s) or now.__setitem__(0, now[0] + s))
    monkeypatch.setattr(routing, "_last_request", 0.0)
    routing._wait_for_rate_limit()
    now[0] += 0.25
    routing._wait_for_rate_limit()
    assert slept == [pytest.approx(0.75)]


def test_user_agent_identifies_otripy():
    assert routing.USER_AGENT.startswith("Otripy/")
