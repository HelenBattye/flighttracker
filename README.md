# flighttracker

Shows the aircraft currently overhead on a small e-paper display, using a local ADS-B receiver
(RTL-SDR dongle on a Raspberry Pi running readsb/dump1090/tar1090) for live positions and
adsbdb.com for route and aircraft details.

## Run (browser view, no hardware)

Defaults to `--display web`: open http://localhost:8000 and the card refreshes itself.
Use `--display preview` to write `preview.png` instead.


```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export AIRCRAFT_URL=http://<receiver-pi>/tar1090/data/aircraft.json
export HOME_LAT=51.5 HOME_LON=-0.12
python -m flighttracker.main --display preview --once   # writes preview.png
python -m flighttracker.main             # browser view on :8000
```

Optional: `RADIUS_KM` (25), `MIN_ALTITUDE_FT` (500), `POLL_SECONDS` (20).

## On the display Pi

Install the Waveshare `waveshare_epd` library, then run with `--display epaper`.

## Airline logos

Logos are fetched automatically by airline ICAO code from
[Jxck-S/airline-logos](https://github.com/Jxck-S/airline-logos) and cached in `logos/`
(git-ignored, as they are trademarks). To use your own, save `logos/<ICAO>.png` (e.g. `TOM.png`).
