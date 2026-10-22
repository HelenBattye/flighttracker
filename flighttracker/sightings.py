import csv
from datetime import datetime
from pathlib import Path

from .feed import Aircraft
from .lookup import Details

LOG = Path("sightings.csv")
FIELDS = ["time", "hex", "callsign", "registration", "airline", "origin", "destination", "aircraft_type", "altitude_ft", "distance_km"]


def log_sighting(ac: Aircraft, d: Details, path: Path = LOG) -> None:
    new_file = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(FIELDS)
        w.writerow(
            [
                datetime.now().isoformat(timespec="seconds"),
                ac.hex,
                ac.callsign,
                ac.registration,
                d.airline,
                d.origin_code,
                d.destination_code,
                d.aircraft_type or ac.type_code,
                ac.altitude_ft,
                round(ac.distance_km, 1),
            ]
        )
