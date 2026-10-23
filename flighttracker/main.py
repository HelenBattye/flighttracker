import argparse
import time
from datetime import datetime
from urllib.parse import urlparse

from . import config
from .display import EpaperDisplay, PreviewDisplay, WebDisplay
from .demo import flights as demo_flights
from .eta import estimate_eta
from .feed import fetch_aircraft
from .lookup import lookup
from .photos import load_photo
from .render import render_card, render_clock, render_error, render_night
from .select import pick
from .sightings import log_sighting


def is_night(hour: int, start: int, end: int) -> bool:
    if start == end:
        return False
    return start <= hour < end if start < end else hour >= start or hour < end


def _photo(hex_code: str, cfg: config.Config):
    photo = load_photo(hex_code) if cfg.show_photos else None
    if photo and not cfg.show_photo_credit:
        photo = (photo[0], "")  # credit left off the card (PHOTO_CREDIT=1 to show it)
    return photo


def main() -> None:
    parser = argparse.ArgumentParser(description="Show the aircraft overhead on an e-paper display.")
    parser.add_argument("--display", choices=["web", "preview", "epaper"], default="web")
    parser.add_argument("--once", action="store_true", help="run a single update and exit")
    parser.add_argument("--demo", action="store_true", help="cycle through recorded flights; no feed or location needed")
    args = parser.parse_args()

    cfg = config.demo() if args.demo else config.load()
    demo = demo_flights() if args.demo else None
    display = {"web": WebDisplay, "preview": PreviewDisplay, "epaper": EpaperDisplay}[args.display]()
    size = (cfg.width, cfg.height)

    current_hex = None
    last_key = None  # what's on screen; e-paper is only redrawn when this changes

    while True:
        now = datetime.now()
        ac = None
        error = None

        if is_night(now.hour, cfg.night_start, cfg.night_end):
            key, card = "night", lambda: render_night(cfg.night_end, *size)
        else:
            try:
                if demo:
                    ac, details = next(demo)
                else:
                    aircraft = fetch_aircraft(cfg.aircraft_url, cfg.home_lat, cfg.home_lon)
                    ac = pick(aircraft, cfg.radius_km, cfg.min_altitude_ft, current_hex)
            except Exception as e:  # network blip, bad JSON: keep running and say so on the display
                error = f"{urlparse(cfg.aircraft_url).netloc or 'feed'}: {type(e).__name__}"
                print(f"feed error: {e}")

            if error:
                key, card = "error", lambda: render_error(error, *size)
            elif ac:
                if not demo:
                    details = lookup(ac.callsign, ac.hex)
                key, card = ac.hex, lambda: render_card(
                    ac, details, *size, photo=_photo(ac.hex, cfg), eta=estimate_eta(ac, details)
                )
            else:
                key, card = now.strftime("%H:%M"), lambda: render_clock(*size, now)  # redraw each minute

        current_hex = ac.hex if ac else None
        if key != last_key:
            display.show(card())
            if ac and not demo:
                log_sighting(ac, details)
            last_key = key
            print(f"showing: {ac.callsign if ac else key}")

        if args.once:
            break
        time.sleep(cfg.poll_seconds)


if __name__ == "__main__":
    main()
