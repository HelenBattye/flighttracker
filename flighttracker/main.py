import argparse
import time

from . import config
from .display import EpaperDisplay, PreviewDisplay, WebDisplay
from .feed import fetch_aircraft
from .lookup import lookup
from .render import render_card
from .select import pick


def main() -> None:
    parser = argparse.ArgumentParser(description="Show the aircraft overhead on an e-paper display.")
    parser.add_argument("--display", choices=["web", "preview", "epaper"], default="web")
    parser.add_argument("--once", action="store_true", help="run a single update and exit")
    args = parser.parse_args()

    cfg = config.load()
    display = {"web": WebDisplay, "preview": PreviewDisplay, "epaper": EpaperDisplay}[args.display]()

    current_hex = None
    last_shown = object()  # avoid refreshing e-paper when nothing changed

    while True:
        try:
            aircraft = fetch_aircraft(cfg.aircraft_url, cfg.home_lat, cfg.home_lon)
            ac = pick(aircraft, cfg.radius_km, cfg.min_altitude_ft, current_hex)
        except Exception as e:  # network blip, bad JSON: keep running
            print(f"feed error: {e}")
            ac = None

        current_hex = ac.hex if ac else None
        key = ac.hex if ac else None
        if key != last_shown:
            details = lookup(ac.callsign, ac.hex) if ac else None
            display.show(render_card(ac, details, cfg.width, cfg.height))
            last_shown = key
            print(f"showing: {ac.callsign if ac else 'nothing'}")

        if args.once:
            break
        time.sleep(cfg.poll_seconds)


if __name__ == "__main__":
    main()
