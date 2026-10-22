# flighttracker

Shows the aircraft currently overhead on a small e-paper display, using a local ADS-B receiver
(RTL-SDR dongle on a Raspberry Pi running readsb/dump1090/tar1090) for live positions and
adsbdb.com for route and aircraft details.

## Run (preview mode, no hardware)

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export AIRCRAFT_URL=http://<receiver-pi>/tar1090/data/aircraft.json
export HOME_LAT=51.5 HOME_LON=-0.12
python -m flighttracker.main --once      # writes preview.png
python -m flighttracker.main             # keeps polling
```

Optional: `RADIUS_KM` (25), `MIN_ALTITUDE_FT` (500), `POLL_SECONDS` (20).

## On the display Pi

Install the Waveshare `waveshare_epd` library, then run with `--display epaper`.
