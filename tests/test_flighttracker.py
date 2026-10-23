import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from flighttracker import config, stats
from flighttracker.demo import FLIGHTS, flights
from flighttracker.eta import estimate_eta
from flighttracker.feed import Aircraft, fetch_aircraft
from datetime import datetime

import requests
from PIL import Image, ImageDraw, ImageOps

import io

from flighttracker import lookup as lookup_module
from flighttracker import photos
from flighttracker.lookup import Details
from flighttracker.render import _fit, _font, FONT_CANDIDATES, render_card, render_clock, render_error, render_night
from flighttracker.main import is_night
from flighttracker.select import pick
from flighttracker.sightings import FIELDS, log_sighting


class PickTests(unittest.TestCase):
    def setUp(self):
        self.near = Aircraft("abc123", "FLT1", 51.5, -0.1, 5000, 200, 10)
        self.far = Aircraft("def456", "FLT2", 51.6, -0.1, 6000, 200, 20)

    def test_picks_nearest_eligible_aircraft(self):
        self.assertEqual(pick([self.far, self.near], 20, 500).hex, "abc123")

    def test_keeps_current_aircraft_while_eligible(self):
        self.assertEqual(pick([self.far, self.near], 20, 500, "def456").hex, "def456")

    def test_excludes_aircraft_outside_limits_or_without_callsign(self):
        no_callsign = Aircraft("ghi789", "", 51.5, -0.1, 5000, 200, 5)
        self.assertIsNone(pick([self.near, self.far, no_callsign], 9, 500))
        self.assertIsNone(pick([self.near, self.far], 20, 6001))


class FeedTests(unittest.TestCase):
    @patch("flighttracker.feed.requests.get")
    def test_parses_receiver_aircraft_format_and_skips_ground(self, get):
        response = Mock()
        response.json.return_value = {
            "aircraft": [
                {"hex": "abc123", "flight": " FLT1 ", "lat": 51.5, "lon": -0.1,
                 "alt_baro": 12000, "gs": 220, "t": "B738", "r": "G-ABCD"},
                {"hex": "def456", "lat": 51.5, "lon": -0.1, "alt_baro": "ground"},
            ]
        }
        get.return_value = response

        aircraft = fetch_aircraft("http://receiver/aircraft.json", 51.5, -0.1)

        self.assertEqual(len(aircraft), 1)
        self.assertEqual(aircraft[0].callsign, "FLT1")
        self.assertEqual(aircraft[0].altitude_ft, 12000)
        self.assertEqual(aircraft[0].type_code, "B738")
        self.assertEqual(aircraft[0].distance_km, 0)
        get.assert_called_once_with("http://receiver/aircraft.json", timeout=5)

    @patch("flighttracker.feed.requests.get")
    def test_accepts_ac_feed_format(self, get):
        response = Mock()
        response.json.return_value = {
            "ac": [{"hex": "abc123", "lat": 51.5, "lon": -0.1, "alt_baro": 12000}]
        }
        get.return_value = response

        self.assertEqual(len(fetch_aircraft("http://feed", 51.5, -0.1)), 1)


class SightingTests(unittest.TestCase):
    def test_writes_header_once_and_records_aircraft_details(self):
        aircraft = Aircraft("abc123", "FLT1", 51.5, -0.1, 12000, 220, 3.26, "B738", "G-ABCD")
        details = Details(airline="Example Air", origin_code="LHR", destination_code="EDI")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sightings.csv"
            log_sighting(aircraft, details, path)
            log_sighting(aircraft, details, path)

            with path.open(newline="") as file:
                rows = list(csv.reader(file))

        self.assertEqual(rows[0], FIELDS)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1][1:10], ["abc123", "FLT1", "G-ABCD", "Example Air", "LHR", "EDI", "B738", "12000", "3.3"])


class ConfigTests(unittest.TestCase):
    def test_defaults_to_public_feed_around_home(self):
        with patch.dict("os.environ", {"HOME_LAT": "51.5", "HOME_LON": "-0.12", "RADIUS_KM": "37"}, clear=True), \
                patch("flighttracker.config.load_dotenv"):
            cfg = config.load()
        self.assertEqual(cfg.aircraft_url, "https://api.adsb.lol/v2/point/51.5/-0.12/20")

    def test_explicit_feed_url_wins(self):
        env = {"HOME_LAT": "1", "HOME_LON": "2", "AIRCRAFT_URL": "http://pi/aircraft.json"}
        with patch.dict("os.environ", env, clear=True), patch("flighttracker.config.load_dotenv"):
            self.assertEqual(config.load().aircraft_url, "http://pi/aircraft.json")

    def test_placeholder_location_gives_a_clear_error(self):
        with patch.dict("os.environ", {"HOME_LAT": "<lat>", "HOME_LON": "2"}, clear=True), \
                patch("flighttracker.config.load_dotenv"):
            with self.assertRaises(SystemExit):
                config.load()

    def test_dotenv_fills_gaps_but_never_overrides_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("# comment\nHOME_LAT=51.5\nexport HOME_LON='-0.12'\nPOLL_SECONDS=5\n")
            with patch.dict("os.environ", {"POLL_SECONDS": "99"}, clear=True):
                config.load_dotenv(path)
                self.assertEqual(os.environ["HOME_LAT"], "51.5")
                self.assertEqual(os.environ["HOME_LON"], "-0.12")
                self.assertEqual(os.environ["POLL_SECONDS"], "99")


class NightTests(unittest.TestCase):
    def test_window_crossing_midnight(self):
        self.assertTrue(is_night(23, 23, 7))
        self.assertTrue(is_night(3, 23, 7))
        self.assertFalse(is_night(7, 23, 7))
        self.assertFalse(is_night(12, 23, 7))

    def test_equal_start_and_end_disables_it(self):
        self.assertFalse(any(is_night(h, 0, 0) for h in range(24)))


class StatsTests(unittest.TestCase):
    def test_summarises_airlines_routes_and_hours(self):
        rows = [
            {"time": "2026-10-23T09:49:26", "hex": "a", "airline": "Ryanair", "origin": "STN", "destination": "DUB",
             "aircraft_type": "Boeing 737", "distance_km": "8.5"},
            {"time": "2026-10-23T09:51:08", "hex": "b", "airline": "Ryanair", "origin": "STN", "destination": "DUB",
             "aircraft_type": "Boeing 737", "distance_km": "3.2"},
            {"time": "2026-10-23T10:02:00", "hex": "b", "airline": "easyJet", "origin": "", "destination": "",
             "aircraft_type": "", "distance_km": "20"},
        ]
        s = stats.summarise(rows)
        self.assertEqual((s["total"], s["unique_aircraft"], s["closest_km"]), (3, 2, 3.2))
        self.assertEqual(s["airlines"][0], ("Ryanair", 2))
        self.assertEqual(s["routes"], [("STN > DUB", 2)])
        self.assertEqual(dict(s["hours"])["09:00"], 2)

    def test_empty_log_is_handled(self):
        s = stats.summarise([])
        self.assertIn("No sightings", stats.format_text(s))
        self.assertIn(b"No sightings", stats.render_html(s))

    def test_html_escapes_values(self):
        s = stats.summarise([{"time": "2026-10-23T09:00:00", "hex": "a", "airline": "<b>x</b>", "distance_km": "1"}])
        self.assertNotIn(b"<b>x</b>", stats.render_html(s))


class DemoTests(unittest.TestCase):
    def test_cycles_forever_through_recorded_flights(self):
        it = flights()
        seen = [next(it) for _ in range(len(FLIGHTS) + 1)]
        self.assertEqual(seen[0], seen[-1])

    def test_every_flight_has_a_callsign_and_route(self):
        for ac, details in FLIGHTS:
            self.assertTrue(ac.callsign and details.origin_code and details.destination_code)


def _json_response(payload, ok=True):
    response = Mock(ok=ok)
    response.json.return_value = payload
    return response


class LookupTests(unittest.TestCase):
    def setUp(self):
        lookup_module.lookup.cache_clear()

    @patch("flighttracker.lookup.requests.get")
    def test_combines_route_and_aircraft_details(self, get):
        route = {"response": {"flightroute": {
            "airline": {"name": "Example Air", "icao": "EXA"},
            "origin": {"iata_code": "LHR", "name": "London Heathrow"},
            "destination": {"iata_code": "EDI", "name": "Edinburgh"},
        }}}
        plane = {"response": {"aircraft": {"manufacturer": "Boeing", "type": "737-800"}}}
        get.side_effect = [_json_response(route), _json_response(plane)]

        d = lookup_module.lookup("EXA1", "abc123")

        self.assertEqual((d.airline, d.airline_icao, d.origin_code, d.destination_code), ("Example Air", "EXA", "LHR", "EDI"))
        self.assertEqual(d.aircraft_type, "Boeing 737-800")

    @patch("flighttracker.lookup.requests.get")
    def test_network_failure_gives_empty_details(self, get):
        get.side_effect = requests.ConnectionError("offline")
        self.assertEqual(lookup_module.lookup("EXA1", "abc123"), Details())

    @patch("flighttracker.lookup.requests.get")
    def test_unknown_flight_and_string_responses_are_tolerated(self, get):
        # adsbdb answers "unknown callsign" with a string in "response"
        get.return_value = _json_response({"response": "unknown callsign"})
        self.assertEqual(lookup_module.lookup("N123", "abc123"), Details())

    @patch("flighttracker.lookup.requests.get")
    def test_results_are_cached(self, get):
        get.return_value = _json_response({"response": {}})
        lookup_module.lookup("EXA1", "abc123")
        lookup_module.lookup("EXA1", "abc123")
        self.assertEqual(get.call_count, 2)  # one route + one aircraft request, not four


@patch("flighttracker.render.load_logo", return_value=None)
class RenderTests(unittest.TestCase):
    aircraft = Aircraft("abc123", "EXA1", 51.5, -0.1, 12000, 220, 3.3, "B738", "G-ABCD")

    def test_cards_are_one_bit_and_the_requested_size(self, _logo):
        details = Details("Example Air", "EXA", "LHR", "London Heathrow", "EDI", "Edinburgh", "Boeing 737-800")
        for img in (
            render_card(self.aircraft, details),
            render_card(self.aircraft, details, 200, 150),
            render_clock(now=datetime(2026, 10, 23, 9, 5)),
            render_night(7),
            render_error("pi.local: Timeout"),
        ):
            self.assertEqual(img.mode, "1")
        self.assertEqual(render_card(self.aircraft, details).size, (400, 300))
        self.assertEqual(render_card(self.aircraft, details, 200, 150).size, (200, 150))

    def test_card_draws_something_with_and_without_a_route(self, _logo):
        routed = Details("Example Air", "EXA", "LHR", "London Heathrow", "EDI", "Edinburgh", "Boeing 737-800")
        for details in (routed, Details()):
            img = render_card(self.aircraft, details)
            self.assertIsNotNone(img.convert("L").point(lambda p: 255 - p).getbbox())  # something non-white
        self.assertNotEqual(render_card(self.aircraft, routed).tobytes(), render_card(self.aircraft, Details()).tobytes())

    def test_long_text_is_shortened_to_fit(self, _logo):
        draw = ImageDraw.Draw(Image.new("1", (400, 300), 1))
        font = _font(FONT_CANDIDATES, 15)
        fitted = _fit(draw, "A very long airport name " * 5, font, 200)
        self.assertLessEqual(draw.textlength(fitted, font=font), 200)
        self.assertTrue(fitted.endswith("…"))
        self.assertEqual(_fit(draw, "Short", font, 200), "Short")


def _jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.linear_gradient("L").resize((200, 113)).convert("RGB").save(buf, "JPEG")
    return buf.getvalue()


def _photo_responses(photographer="Jane Spotter"):
    api = _json_response({"photos": [{"thumbnail_large": {"src": "https://t.example/a_280.jpg"}, "photographer": photographer}]})
    image = Mock(ok=True, content=_jpeg_bytes())
    return [api, image]


class PhotoTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        patcher = patch.object(photos, "PHOTO_DIR", Path(self.directory.name) / "photos")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.directory.cleanup)

    @patch("flighttracker.photos.requests.get")
    def test_downloads_once_then_uses_the_cache(self, get):
        get.side_effect = _photo_responses()

        first = photos.load_photo("400a1b")
        second = photos.load_photo("400A1B")

        image, credit = first
        self.assertEqual(credit, "Jane Spotter")
        self.assertEqual(image.mode, "1")
        self.assertLessEqual(image.width, photos.PHOTO_BOX[0])
        self.assertLessEqual(image.height, photos.PHOTO_BOX[1])
        self.assertIsNotNone(second)
        self.assertEqual(get.call_count, 2)  # one API call and one image download in total
        self.assertIn("User-Agent", get.call_args.kwargs["headers"])

    def test_flat_sky_goes_white_and_the_subject_stays_dark(self):
        sky = Image.new("L", (130, 73), 150)  # mid-grey sky, which plain dithering turns into a checkerboard
        for x in range(40, 90):
            for y in range(30, 40):
                sky.putpixel((x, y), 20)  # dark aircraft body
        out = photos._atkinson(ImageOps.autocontrast(photos._flatten(sky), cutoff=1))
        corner = out.crop((0, 0, 30, 20)).convert("L").getextrema()
        body = out.crop((50, 32, 80, 38)).convert("L").getextrema()
        self.assertEqual(corner, (255, 255))
        self.assertEqual(body, (0, 0))

    @patch("flighttracker.photos.requests.get")
    def test_aircraft_without_a_photo_are_remembered(self, get):
        get.return_value = _json_response({"photos": []})
        self.assertIsNone(photos.load_photo("400a1b"))
        self.assertIsNone(photos.load_photo("400a1b"))
        self.assertEqual(get.call_count, 1)

    @patch("flighttracker.photos.requests.get")
    def test_failures_are_not_remembered_so_it_retries(self, get):
        get.side_effect = requests.ConnectionError("offline")
        self.assertIsNone(photos.load_photo("400a1b"))
        get.side_effect = None
        get.return_value = _json_response({}, ok=False)  # rate limited
        self.assertIsNone(photos.load_photo("400a1b"))
        get.side_effect = _photo_responses()
        self.assertIsNotNone(photos.load_photo("400a1b"))

    @patch("flighttracker.photos.requests.get")
    def test_invalid_hex_codes_never_touch_the_network_or_disk(self, get):
        for bad in ("", "../etc", "zzzzzz", "12345"):
            self.assertIsNone(photos.load_photo(bad))
        get.assert_not_called()


@patch("flighttracker.render.load_logo", return_value=None)
class PhotoCardTests(unittest.TestCase):
    aircraft = Aircraft("abc123", "EXA1", 51.5, -0.1, 12000, 220, 3.3, "B738", "G-ABCD")
    details = Details("Example Air", "EXA", "LHR", "A very long airport name that would run under the photo",
                      "EDI", "Another very long airport name that would run under the photo", "Boeing 737-800")

    def _photo(self):
        return Image.linear_gradient("L").resize((130, 73)).convert("1"), "Jane Spotter"

    def test_photo_changes_the_card_and_keeps_its_size(self, _logo):
        plain = render_card(self.aircraft, self.details)
        with_photo = render_card(self.aircraft, self.details, photo=self._photo())
        self.assertEqual(with_photo.size, (400, 300))
        self.assertNotEqual(plain.tobytes(), with_photo.tobytes())

    def test_photo_sits_level_with_the_speed_row_and_airport_names_run_underneath(self, _logo):
        pic, credit = self._photo()
        img = render_card(self.aircraft, self.details, photo=(pic, credit))
        x = 400 - 16 - pic.width
        self.assertEqual(img.crop((x, 164, x + pic.width, 164 + pic.height)).tobytes(), pic.tobytes())
        # the departing line is below the photo and credit, so long names can use the full width
        below_photo = img.crop((16, 164 + pic.height + 19, 384, 164 + pic.height + 19 + 18))
        self.assertIsNotNone(below_photo.convert("L").point(lambda p: 255 - p).getbbox())


class EtaTests(unittest.TestCase):
    now = datetime(2026, 10, 23, 12, 0)
    edinburgh = Details(destination_lat=55.95, destination_lon=-3.3725)

    def test_straight_line_distance_over_ground_speed(self):
        # Leeds Bradford to Edinburgh is roughly 255 km, so about 23 minutes at 360 kt (667 km/h)
        ac = Aircraft("abc123", "EXA1", 53.87, -1.66, 20000, 360, 5)
        eta = estimate_eta(ac, self.edinburgh, self.now)
        self.assertTrue(20 <= (eta - self.now).total_seconds() / 60 <= 27)

    def test_no_estimate_without_destination_or_when_slow(self):
        fast = Aircraft("abc123", "EXA1", 53.87, -1.66, 20000, 360, 5)
        slow = Aircraft("abc123", "EXA1", 53.87, -1.66, 500, 60, 5)
        self.assertIsNone(estimate_eta(fast, Details(), self.now))
        self.assertIsNone(estimate_eta(slow, self.edinburgh, self.now))

    def test_card_shows_the_estimate_and_uses_feet_and_knots(self):
        ac = Aircraft("abc123", "EXA1", 53.87, -1.66, 20000, 360, 5)
        with patch("flighttracker.render.load_logo", return_value=None), \
                patch("flighttracker.render.ImageDraw.ImageDraw.text") as text:
            render_card(ac, self.edinburgh, eta=datetime(2026, 10, 23, 12, 40))
        drawn = [call.args[1] for call in text.call_args_list]
        self.assertIn("360 kt", drawn)
        self.assertIn("20,000 ft", drawn)
        self.assertIn("ETA ~12:40", drawn)


if __name__ == "__main__":
    unittest.main()