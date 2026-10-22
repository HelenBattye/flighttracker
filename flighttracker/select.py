from .feed import Aircraft


def pick(
    aircraft: list[Aircraft],
    radius_km: float,
    min_altitude_ft: int,
    current_hex: str | None = None,
) -> Aircraft | None:
    """Nearest airborne aircraft in range. Sticks with the current one while it's still in range,
    so the display doesn't flip between two planes at similar distances."""
    candidates = [
        a for a in aircraft if a.distance_km <= radius_km and a.altitude_ft >= min_altitude_ft and a.callsign
    ]
    if not candidates:
        return None
    for a in candidates:
        if a.hex == current_hex:
            return a
    return min(candidates, key=lambda a: a.distance_km)
