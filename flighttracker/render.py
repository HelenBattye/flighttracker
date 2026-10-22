from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from .feed import Aircraft
from .logos import load_logo
from .lookup import Details

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


def render_card(
    ac: Aircraft | None,
    d: Details | None,
    width: int = 400,
    height: int = 300,
    now: datetime | None = None,
) -> Image.Image:
    img = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)
    m = 16
    inner = width - 2 * m

    if ac is None or d is None:
        now = now or datetime.now()
        clock = _font(BOLD_CANDIDATES, 96)
        date = _font(FONT_CANDIDATES, 22)
        text = now.strftime("%H:%M")
        draw.text((width / 2, height / 2 - 20), text, font=clock, fill=0, anchor="mm")
        draw.text((width / 2, height / 2 + 55), now.strftime("%A %-d %B"), font=date, fill=0, anchor="mm")
        return img

    title = _font(BOLD_CANDIDATES, 28)
    big = _font(BOLD_CANDIDATES, 34)
    small = _font(FONT_CANDIDATES, 15)
    mid = _font(BOLD_CANDIDATES, 26)

    logo_box = (110, 80)
    # airline callsigns start with the 3-letter ICAO code (EXS2PT -> EXS) when the lookup has none
    cs = ac.callsign
    icao = d.airline_icao or (cs[:3] if cs[:3].isalpha() and cs[3:4].isdigit() else "")
    logo = load_logo(icao, logo_box) if icao else None
    if logo:
        # top-right, level with the route line
        img.paste(logo, (width - m - logo.width, 70 + (logo_box[1] - logo.height) // 2))

    y = m
    draw.text((m, y), _fit(draw, d.airline or ac.callsign, title, inner), font=title, fill=0)
    y += 36
    draw.text((m, y), ac.callsign, font=small, fill=0)
    y += 28
    route = f"{d.origin_code or '???'} > {d.destination_code or '???'}"
    draw.text((m, y), route, font=big, fill=0)
    y += 46
    draw.text((m, y), d.aircraft_type, font=small, fill=0)
    y += 28
    draw.line((m, y, width - m, y), fill=0)
    y += 10
    kmh = round(ac.speed_kt * 1.852)
    metres = round(ac.altitude_ft * 0.3048)
    draw.text((m, y), f"{kmh} km/h", font=mid, fill=0)
    draw.text((m + 180, y), f"{metres} m", font=mid, fill=0)
    y += 42
    if d.origin_name:
        draw.text((m, y), _fit(draw, f"Departing: {d.origin_name}", small, inner), font=small, fill=0)
        y += 22
    if d.destination_name:
        draw.text((m, y), _fit(draw, f"Arriving: {d.destination_name}", small, inner), font=small, fill=0)
    return img
