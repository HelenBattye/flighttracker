import os
from dataclasses import dataclass
from pathlib import Path

# Public community feed, used when AIRCRAFT_URL isn't set so the project runs without a receiver.
# Takes lat, lon and a radius in nautical miles.
PUBLIC_FEED = "https://api.adsb.lol/v2/point/{lat}/{lon}/{radius_nm}"
KM_PER_NM = 1.852


@dataclass(frozen=True)
class Config:
    # URL of an aircraft.json feed: your receiver Pi (e.g. http://192.168.1.50/tar1090/data/aircraft.json)
    # or a public one (adsb.lol, airplanes.live)
    aircraft_url: str
    home_lat: float
    home_lon: float
    radius_km: float = 25.0
    min_altitude_ft: int = 500
    poll_seconds: int = 20
    night_start: int = 23  # hour (0-23) the display goes quiet; equal start and end disables it
    night_end: int = 7
    width: int = 400
    height: int = 300
    show_photos: bool = True  # aircraft photo from Planespotters; SHOW_PHOTOS=0 turns it off


def load_dotenv(path: Path | None = None) -> None:
    """Read KEY=value lines from a .env file into the environment. Real environment variables win.

    Looks in the current folder, then next to the code, so it works from anywhere."""
    paths = [path] if path else [Path(".env"), Path(__file__).resolve().parent.parent / ".env"]
    for p in paths:
        if not p.is_file():
            continue
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.removeprefix("export ").strip()
            os.environ.setdefault(key, value.strip().strip("\"'"))


def _number(name: str, cast):
    raw = os.environ.get(name)
    if raw is None:
        raise SystemExit(f"{name} isn't set. Copy .env.example to .env and fill it in, or export {name}.")
    try:
        return cast(raw)
    except ValueError:
        raise SystemExit(f"{name}={raw!r} isn't a number. Use your real value, not a <placeholder>.")


def load() -> Config:
    load_dotenv()
    home_lat = _number("HOME_LAT", float)
    home_lon = _number("HOME_LON", float)
    radius_km = float(os.environ.get("RADIUS_KM", 25))
    url = os.environ.get("AIRCRAFT_URL") or PUBLIC_FEED.format(
        lat=home_lat, lon=home_lon, radius_nm=round(radius_km / KM_PER_NM) or 1
    )
    return Config(
        aircraft_url=url,
        home_lat=home_lat,
        home_lon=home_lon,
        radius_km=radius_km,
        min_altitude_ft=int(os.environ.get("MIN_ALTITUDE_FT", 500)),
        poll_seconds=int(os.environ.get("POLL_SECONDS", 20)),
        night_start=int(os.environ.get("NIGHT_START", 23)),
        night_end=int(os.environ.get("NIGHT_END", 7)),
        show_photos=os.environ.get("SHOW_PHOTOS", "1") != "0",
    )


def demo() -> Config:
    """Settings for --demo: no location or feed needed, and night mode off so there's always a card."""
    return Config(aircraft_url="demo", home_lat=0, home_lon=0, poll_seconds=8, night_start=0, night_end=0, show_photos=False)
