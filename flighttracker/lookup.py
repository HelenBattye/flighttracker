"""Route and aircraft details from the free adsbdb.com API, cached in memory."""

from dataclasses import dataclass
from functools import lru_cache

import requests

BASE = "https://api.adsbdb.com/v0"


@dataclass(frozen=True)
class Details:
    airline: str = ""
    origin_code: str = ""
    origin_name: str = ""
    destination_code: str = ""
    destination_name: str = ""
    aircraft_type: str = ""


def _get(path: str) -> dict:
    try:
        r = requests.get(f"{BASE}/{path}", timeout=5)
        return r.json().get("response", {}) if r.ok else {}
    except (requests.RequestException, ValueError):
        return {}


@lru_cache(maxsize=256)
def lookup(callsign: str, hex_code: str) -> Details:
    route = _get(f"callsign/{callsign}")
    route = route.get("flightroute", {}) if isinstance(route, dict) else {}
    plane = _get(f"aircraft/{hex_code}")
    plane = plane.get("aircraft", {}) if isinstance(plane, dict) else {}

    origin = route.get("origin") or {}
    dest = route.get("destination") or {}
    airline = route.get("airline") or {}
    return Details(
        airline=airline.get("name", ""),
        origin_code=origin.get("iata_code", ""),
        origin_name=origin.get("name", ""),
        destination_code=dest.get("iata_code", ""),
        destination_name=dest.get("name", ""),
        aircraft_type=" ".join(filter(None, [plane.get("manufacturer"), plane.get("type")])),
    )
