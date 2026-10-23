# flighttracker

Shows the aircraft overhead on a 400x300 e-paper card. Feed (`feed.py`) -> pick nearest (`select.py`) ->
route/type lookup (`lookup.py`, adsbdb.com) -> render with Pillow (`render.py`, `logos.py`) -> display
(`display.py`: web, preview PNG, or Waveshare e-paper). `main.py` is the loop; `sightings.py` logs to CSV;
`stats.py` summarises it; `demo.py` holds recorded flights; `photos.py` fetches aircraft photos
(Planespotters, cached, needs a descriptive User-Agent); `eta.py` estimates arrival time.

## Commands
- Run: `python -m flighttracker.main` (browser on :8000; `/stats` for the sightings summary)
- No feed or location needed: `python -m flighttracker.main --demo`
- One frame to `preview.png`: `--display preview --once`
- Tests: `python -m unittest discover -s tests` (stdlib only; no network)
- Text stats: `python -m flighttracker.stats`

## Config
Environment variables, or a `.env` file (see `.env.example`; real env vars win). `HOME_LAT` and `HOME_LON`
are required. With no `AIRCRAFT_URL` it uses the public adsb.lol feed around home. The feed code accepts
both receiver (`aircraft`) and public (`ac`) JSON.

## Conventions
- Keep dependencies to `requests` and `Pillow`; `.env` and `waveshare_epd` are handled without extra packages.
- Network calls must fail soft (the display shows an error card and recovers); tests mock `requests.get`.
- `logos/`, `photos/`, `sightings.csv`, `preview.png` and `.env` are git-ignored. Logos and photos are third-party; don't commit either.
- The e-paper is only redrawn when the card changes (`last_key` in `main.py`); keep that, it protects the panel.
- Add a test in `tests/test_flighttracker.py` for new behaviour.

## Gotchas
- Don't type `<placeholders>` from docs into the shell; `<` is a redirect. `config.py` reports non-numeric coordinates.
- adsb.lol takes its radius in nautical miles; `RADIUS_KM` is converted.
