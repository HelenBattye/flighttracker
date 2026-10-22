"""Airline logos by ICAO code, fetched once from Jxck-S/airline-logos and cached in ./logos.

Logos are trademarks of their owners, so the logos folder is git-ignored. Drop your own
<ICAO>.png files in there to override the downloaded ones.
"""

import os
from pathlib import Path

import requests
from PIL import Image

LOGO_DIR = Path("logos")
URL = "https://raw.githubusercontent.com/Jxck-S/airline-logos/main/flightaware_logos/{icao}.png"


def _download(icao: str, path: Path) -> bool:
    try:
        r = requests.get(URL.format(icao=icao), timeout=5)
    except requests.RequestException:
        return False  # offline: try again next time
    if r.ok:
        path.write_bytes(r.content)
        return True
    path.with_suffix(".missing").touch()  # remember airlines that have no logo
    return False


def load_logo(icao: str, box: tuple[int, int], threshold: int | None = None) -> Image.Image | None:
    """Return the logo as a 1-bit image fitted inside box, or None if unavailable.

    threshold: 0 dithers (keeps shading, looks dotty); 1-254 makes every pixel darker than
    that value black and the rest white (crisp for solid logos). Defaults to $LOGO_THRESHOLD or 0.
    """
    if threshold is None:
        threshold = int(os.environ.get("LOGO_THRESHOLD", 0))
    if not icao.isalnum():
        return None
    LOGO_DIR.mkdir(exist_ok=True)
    path = LOGO_DIR / f"{icao.upper()}.png"
    if not path.exists():
        if path.with_suffix(".missing").exists() or not _download(icao.upper(), path):
            return None

    img = Image.open(path).convert("RGBA")
    flat = Image.new("RGBA", img.size, "white")  # transparent areas become white
    img = Image.alpha_composite(flat, img).convert("L")
    img.thumbnail(box, Image.LANCZOS)
    if threshold:
        return img.point(lambda p: 255 if p >= threshold else 0).convert("1", dither=Image.Dither.NONE)
    return img.convert("1")  # Floyd-Steinberg dithering keeps colour logos recognisable
