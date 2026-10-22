import math
from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class Aircraft:
    hex: str
    callsign: str
    lat: float
    lon: float
    altitude_ft: int
    speed_kt: float
    distance_km: float


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def fetch_aircraft(url: str, home_lat: float, home_lon: float) -> list[Aircraft]:
    """Read readsb/dump1090/tar1090 aircraft.json and keep airborne aircraft with a position."""
    data = requests.get(url, timeout=5).json()
    out = []
    # local receivers use "aircraft"; adsb.lol / airplanes.live use "ac"
    for a in data.get("aircraft") or data.get("ac") or []:
        alt = a.get("alt_baro")
        if "lat" not in a or "lon" not in a or not isinstance(alt, (int, float)):
            continue  # no position, or "ground"
        out.append(
            Aircraft(
                hex=a["hex"],
                callsign=(a.get("flight") or "").strip(),
                lat=a["lat"],
                lon=a["lon"],
                altitude_ft=int(alt),
                speed_kt=float(a.get("gs") or 0),
                distance_km=haversine_km(home_lat, home_lon, a["lat"], a["lon"]),
            )
        )
    return out
