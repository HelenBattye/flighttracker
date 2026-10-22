import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from PIL import Image


class PreviewDisplay:
    """Saves the card as a PNG so you can develop without the e-paper hardware."""

    def __init__(self, path: str = "preview.png"):
        self.path = Path(path)

    def show(self, img: Image.Image) -> None:
        img.convert("RGB").save(self.path)


class WebDisplay:
    """Serves the latest card in a browser (auto-refreshing), for use before the e-paper arrives."""

    PAGE = (
        b"<!doctype html><meta charset=utf-8><title>Flight tracker</title>"
        b"<body style='margin:0;background:#ddd;display:grid;place-items:center;height:100vh'>"
        b"<img id=c src=card.png style='border:12px solid #c9a36b;background:#fff;image-rendering:pixelated;max-width:90vw;max-height:85vh;aspect-ratio:4/3'>"
        b"<script>setInterval(()=>c.src='card.png?'+Date.now(),3000)</script>"
    )

    def __init__(self, port: int = 8000):
        self.png = b""
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.startswith("/card.png"):
                    body, kind = outer.png, "image/png"
                else:
                    body, kind = outer.PAGE, "text/html"
                self.send_response(200)
                self.send_header("Content-Type", kind)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
        Thread(target=self.server.serve_forever, daemon=True).start()
        print(f"Open http://localhost:{port}")

    def show(self, img: Image.Image) -> None:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, "PNG")
        self.png = buf.getvalue()


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
