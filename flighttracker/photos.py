"""Aircraft photos from the Planespotters.net API, fetched once per aircraft and cached in ./photos.

The photos folder is git-ignored, so no photos are committed. Planespotters requires a descriptive User-Agent: https://www.planespotters.net/photo/api
"""

from pathlib import Path

import requests
from PIL import Image, ImageFilter, ImageOps

PHOTO_DIR = Path("photos")
API = "https://api.planespotters.net/pub/photos/hex/{hex}"
HEADERS = {"User-Agent": "flighttracker/1.0 (+https://github.com/HelenBattye/flighttracker)"}
PHOTO_BOX = (130, 76)


def _download(hex_code: str, base: Path) -> bool:
    """Fetch the photo for an aircraft. Only a definite 'no photo' is remembered."""
    try:
        r = requests.get(API.format(hex=hex_code), headers=HEADERS, timeout=5)
        if not r.ok:
            return False  # rate limited or down: try again later
        photos = r.json().get("photos") or []
        if not photos:
            base.with_suffix(".missing").touch()
            return False
        # the large image (about 500 px) gives the 1-bit conversion far more to work with than the thumbnail
        source = (photos[0].get("thumbnail_large") or photos[0]["thumbnail"])["src"]
        image = requests.get(source, headers=HEADERS, timeout=5)
        if not image.ok:
            return False
        _jpg(base).write_bytes(image.content)
        return True
    except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError):
        return False


def _jpg(base: Path) -> Path:
    return base.with_name(base.name + "-large.jpg")


def _flatten(img: Image.Image, radius: int = 10, strength: float = 0.97) -> Image.Image:
    """Divide each pixel by its local average so flat areas (sky) go white and detail stays dark.

    Without this, a grey sky dithers into a busy checkerboard that fights with the aircraft."""
    average = img.filter(ImageFilter.GaussianBlur(radius)).tobytes()
    out = bytes(min(255, int(255 * p / (a + 1) * strength)) if a else 255 for p, a in zip(img.tobytes(), average))
    return Image.frombytes("L", img.size, out)


def _atkinson(img: Image.Image) -> Image.Image:
    """Atkinson dithering: crisper than Floyd-Steinberg on small images, as on the early Macs."""
    w, h = img.size
    px = [float(p) for p in img.tobytes()]
    for y in range(h):
        for x in range(w):
            i = y * w + x
            old = px[i]
            new = 255.0 if old >= 128 else 0.0
            px[i] = new
            err = (old - new) / 8
            for dx, dy in ((1, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (0, 2)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    px[ny * w + nx] += err
    out = Image.new("1", (w, h))
    out.putdata([255 if p >= 128 else 0 for p in px])
    return out


def load_photo(hex_code: str, box: tuple[int, int] = PHOTO_BOX) -> Image.Image | None:
    """Return the photo as a 1-bit dithered image fitted inside box, or None if there isn't one."""
    if len(hex_code) != 6 or not all(c in "0123456789abcdefABCDEF" for c in hex_code):
        return None
    PHOTO_DIR.mkdir(exist_ok=True)
    base = PHOTO_DIR / hex_code.lower()
    if not _jpg(base).exists():
        if base.with_suffix(".missing").exists() or not _download(hex_code.lower(), base):
            return None
    try:
        img = Image.open(_jpg(base)).convert("L")
    except OSError:
        return None  # corrupt download
    img.thumbnail(box, Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=150, threshold=2))
    img = ImageOps.autocontrast(_flatten(img), cutoff=1)  # a 1-bit panel needs all the contrast it can get
    return _atkinson(img)
