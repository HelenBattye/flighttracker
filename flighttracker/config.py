import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # URL of the receiver Pi's aircraft feed, e.g. http://192.168.1.50/tar1090/data/aircraft.json
    aircraft_url: str
    home_lat: float
    home_lon: float
    radius_km: float = 25.0
    min_altitude_ft: int = 500
    poll_seconds: int = 20
    width: int = 400
    height: int = 300


def load() -> Config:
    return Config(
        aircraft_url=os.environ["AIRCRAFT_URL"],
        home_lat=float(os.environ["HOME_LAT"]),
        home_lon=float(os.environ["HOME_LON"]),
        radius_km=float(os.environ.get("RADIUS_KM", 25)),
        min_altitude_ft=int(os.environ.get("MIN_ALTITUDE_FT", 500)),
        poll_seconds=int(os.environ.get("POLL_SECONDS", 20)),
    )
