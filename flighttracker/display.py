from pathlib import Path

from PIL import Image


class PreviewDisplay:
    """Saves the card as a PNG so you can develop without the e-paper hardware."""

    def __init__(self, path: str = "preview.png"):
        self.path = Path(path)

    def show(self, img: Image.Image) -> None:
        img.convert("RGB").save(self.path)


class EpaperDisplay:
    """Waveshare 4.2" (400x300) e-paper. Needs the vendor library: https://github.com/waveshareteam/e-Paper"""

    def __init__(self):
        from waveshare_epd import epd4in2  # imported lazily so preview mode works anywhere

        self.epd = epd4in2.EPD()
        self.epd.init()
        self.epd.Clear()

    def show(self, img: Image.Image) -> None:
        self.epd.display(self.epd.getbuffer(img))
        self.epd.sleep()
        self.epd.init()
