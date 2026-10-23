from datetime import datetime, timedelta

from .feed import Aircraft, haversine_km
from .lookup import Details

KM_PER_NM = 1.852


def estimate_eta(ac: Aircraft, d: Details, now: datetime | None = None) -> datetime | None:
    """Rough arrival time: straight-line distance to the destination at the current ground speed.

    Ignores the route flown, wind and the slowdown on approach, so treat it as a guide (a few
    minutes out on short flights). Returns None when it can't say something sensible.
    """
    if d.destination_lat is None or d.destination_lon is None or ac.speed_kt < 100:
        return None  # no destination coordinates, or too slow to be cruising (taxiing, climbing out)
    km = haversine_km(ac.lat, ac.lon, d.destination_lat, d.destination_lon)
    hours = km / (ac.speed_kt * KM_PER_NM)
    if km < 1 or hours > 20:
        return None
    return (now or datetime.now()) + timedelta(hours=hours)
