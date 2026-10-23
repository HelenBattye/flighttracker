from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from .feed import Aircraft
from .logos import load_logo
from .lookup import Details
from .photos import PHOTO_BOX

FONT_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
BOLD_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _fit(draw, text, font, max_width) -> str:
    while text and draw.textlength(text, font=font) > max_width:
        text = text[:-2].rstrip() + "…" if not text.endswith("…") else text[:-2] + "…"
    return text


def _blank(width: int, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("1", (width, height), 1)
    return img, ImageDraw.Draw(img)


def render_clock(width: int = 400, height: int = 300, now: datetime | None = None) -> Image.Image:
    now = now or datetime.now()
    img, draw = _blank(width, height)
    draw.text((width / 2, height / 2 - 20), now.strftime("%H:%M"), font=_font(BOLD_CANDIDATES, 96), fill=0, anchor="mm")
    draw.text((width / 2, height / 2 + 55), now.strftime("%A %-d %B"), font=_font(FONT_CANDIDATES, 22), fill=0, anchor="mm")
    return img


def render_night(wake_hour: int, width: int = 400, height: int = 300) -> Image.Image:
    """Nearly blank so the panel isn't redrawn all night."""
    img, draw = _blank(width, height)
    draw.text((width / 2, height / 2), f"Night mode - back at {wake_hour:02d}:00", font=_font(FONT_CANDIDATES, 16), fill=0, anchor="mm")
    return img


def render_error(message: str, width: int = 400, height: int = 300, now: datetime | None = None) -> Image.Image:
    now = now or datetime.now()
    img, draw = _blank(width, height)
    big, small = _font(BOLD_CANDIDATES, 30), _font(FONT_CANDIDATES, 15)
    draw.text((width / 2, height / 2 - 30), "Receiver unreachable", font=big, fill=0, anchor="mm")
    draw.text((width / 2, height / 2 + 12), _fit(draw, message, small, width - 32), font=small, fill=0, anchor="mm")
    draw.text((width / 2, height / 2 + 36), f"since {now.strftime('%H:%M')}", font=small, fill=0, anchor="mm")
    return img


def render_card(
    ac: Aircraft,
    d: Details,
    width: int = 400,
    height: int = 300,
    photo: Image.Image | None = None,
    eta: datetime | None = None,
) -> Image.Image:
    img, draw = _blank(width, height)
    m = 16
    inner = width - 2 * m
    title = _font(BOLD_CANDIDATES, 28)
    big = _font(BOLD_CANDIDATES, 34)
    small = _font(FONT_CANDIDATES, 15)
    mid = _font(BOLD_CANDIDATES, 26)

    has_route = bool(d.origin_code or d.destination_code)
    # fall back to what the receiver itself reported when adsbdb doesn't know the flight
    plane_type = d.aircraft_type or ac.type_code
    headline = d.airline or ac.registration or ac.callsign

    logo_box = (110, 80)
    # airline callsigns start with the 3-letter ICAO code (EXS2PT -> EXS) when the lookup has none
    cs = ac.callsign
    icao = d.airline_icao or (cs[:3] if cs[:3].isalpha() and cs[3:4].isdigit() else "")
    logo = load_logo(icao, logo_box) if icao else None
    if logo:
        img.paste(logo, (width - m - logo.width, 70 + (logo_box[1] - logo.height) // 2))

    y = m
    draw.text((m, y), _fit(draw, headline, title, inner), font=title, fill=0)
    y += 36
    sub = cs if cs == headline or not ac.registration else f"{cs}  {ac.registration}"
    draw.text((m, y), sub, font=small, fill=0)
    y += 28
    if has_route:
        draw.text((m, y), f"{d.origin_code or '-'} > {d.destination_code or '-'}", font=big, fill=0)
        draw.text((m, y + 46), plane_type, font=small, fill=0)
    else:
        # no route (private/light aircraft): the aircraft type is the interesting part
        draw.text((m, y), _fit(draw, plane_type or "Unknown aircraft", big, inner), font=big, fill=0)
    y = 154  # divider sits at the same height whether or not there's a route
    draw.line((m, y, width - m, y), fill=0)
    y += 10
    speed = f"{round(ac.speed_kt)} kt"
    draw.text((m, y), speed, font=mid, fill=0)
    draw.text((m + draw.textlength(speed, font=mid) + 24, y), f"{ac.altitude_ft:,} ft", font=mid, fill=0)
    y += 42
    # the photo sits top right, level with the speed row; ETA goes beside it and the airport
    # names go underneath at full width so they're less likely to be cut off
    if eta:
        draw.text((m, y), f"ETA ~{eta.strftime('%H:%M')}", font=small, fill=0)
        y += 24
    if photo:
        x, top = width - m - photo.width, 164
        img.paste(photo, (x, top))
        y = max(y, top + photo.height + 8)
    if d.origin_name:
        draw.text((m, y), _fit(draw, f"Departing: {d.origin_name}", small, inner), font=small, fill=0)
        y += 22
    if d.destination_name:
        draw.text((m, y), _fit(draw, f"Arriving: {d.destination_name}", small, inner), font=small, fill=0)
    return img
