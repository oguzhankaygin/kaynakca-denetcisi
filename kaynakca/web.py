"""Bellekte çalışan yerel HTTP arayüzü."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .report import build

MAX_BODY = 200 * 1024
STATIC = Path(__file__).with_name("static")
ASSETS = {
    "/": ("index.html", "text/html"),
    "/app.js": ("app.js", "text/javascript"),
    "/style.css": ("style.css", "text/css"),
}


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, format, *args):
        pass

    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status, data):
        self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json")

    def do_GET(self):
        asset = ASSETS.get(self.path)
        if asset is None:
            self._json(404, {"error": "Sayfa bulunamadı."})
            return
        filename, content_type = asset
        self._send(200, (STATIC / filename).read_bytes(), content_type)

    def do_POST(self):
        if self.path != "/api/denetle":
            self._json(404, {"error": "Uç bulunamadı."})
            return
        if self.headers.get_all("X-Kaynakca-Request") != ["1"]:
            self._json(403, {"error": "X-Kaynakca-Request başlığı gerekli."})
            return
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get("Transfer-Encoding") is not None or len(lengths) != 1:
            self._json(400, {"error": "Tek bir Content-Length başlığı gerekli."})
            return
        length = lengths[0]
        if not length.isascii() or not length.isdecimal():
            self._json(400, {"error": "Geçersiz gövde uzunluğu."})
            return
        digits = length.lstrip("0") or "0"
        if len(digits) > len(str(MAX_BODY)) or int(digits) > MAX_BODY:
            self._json(413, {"error": "Gövde en fazla 200 KB olabilir."})
            return
        try:
            body = self.rfile.read(int(digits))
            if len(body) != int(digits):
                raise ValueError("İstek gövdesi eksik.")
            text = body.decode("utf-8")
            if self.headers.get_content_type() == "application/json":
                payload = json.loads(text)
                if not isinstance(payload, dict) or not isinstance(payload.get("kaynakca"), str):
                    raise ValueError("JSON gövdesinde kaynakca metni gerekli.")
                text = payload["kaynakca"]
            report = build(text)
        except TimeoutError:
            self._json(408, {"error": "İstek gövdesi zamanında alınamadı."})
            return
        except (ValueError, RecursionError):
            self._json(400, {"error": "Girdiyi okuyamadık. UTF-8 metni ve varsa BibTeX sözdizimini kontrol edin."})
            return
        self._json(200, report)


def serve():
    with ThreadingHTTPServer(("127.0.0.1", 8791), Handler) as server:
        print("Kaynakça Denetçisi · http://127.0.0.1:8791", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
