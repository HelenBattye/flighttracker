"""Aircraft photos from the Planespotters.net API, fetched once per aircraft and cached in ./photos.

The photos belong to their photographers, so the photos folder is git-ignored and the card credits
the photographer. Planespotters requires a descriptive User-Agent: https://www.planespotters.net/photo/api
"""

from pathlib import Path

import requests
from PIL import Image, ImageOps

PHOTO_DIR = Path("photos")
API = "https://api.planespotters.net/pub/photos/hex/{hex}"
HEADERS = {"User-Agent": "flighttracker/1.0 (+https://github.com/HelenBattye/flighttracker)"}
PHOTO_BOX = (130, 76)


def _download(hex_code: str, base: Path) -> bool:
    """Fetch the photo and photographer for an aircraft. Only a definite 'no photo' is remembered."""
    try:
        r = requests.get(API.format(hex=hex_code), headers=HEADERS, timeout=5)
        if not r.ok:
            return False  # rate limited or down: try again later
        photos = r.json().get("photos") or []
        if not photos:
            base.with_suffix(".missing").touch()
            return False
        image = requests.get(photos[0]["thumbnail"]["src"], headers=HEADERS, timeout=5)
        if not image.ok:
            return False
        base.with_suffix(".jpg").write_bytes(image.content)
        base.with_suffix(".txt").write_text(photos[0].get("photographer") or "")
        return True
    except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError):
        return False


def load_photo(hex_code: str, box: tuple[int, int] = PHOTO_BOX) -> tuple[Image.Image, str] | None:
    """Return (1-bit dithered photo fitted inside box, photographer) or None if there isn't one."""
    if len(hex_code) != 6 or not all(c in "0123456789abcdefABCDEF" for c in hex_code):
        return None
    PHOTO_DIR.mkdir(exist_ok=True)
    base = PHOTO_DIR / hex_code.lower()
    if not base.with_suffix(".jpg").exists():
        if base.with_suffix(".missing").exists() or not _download(hex_code.lower(), base):
            return None
    try:
        img = Image.open(base.with_suffix(".jpg")).convert("L")
    except OSError:
        return None  # corrupt download
    img = ImageOps.autocontrast(img, cutoff=2)  # dithering needs the contrast on a 1-bit panel
    img.thumbnail(box, Image.LANCZOS)
    credit = base.with_suffix(".txt").read_text() if base.with_suffix(".txt").exists() else ""
    return img.convert("1"), credit
