import io
import json
import unittest
from contextlib import redirect_stdout
from http import HTTPStatus
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from kaynakca.__main__ import main
from kaynakca.crossref import lookup
from kaynakca.parse import parse
from kaynakca.report import build, render, to_json
from kaynakca.web import MAX_BODY, Handler

ENTRY = "Işık, A. (2022). Kurgusal iz. Örnek Yay. doi:10.0000/ornek.iz"


class ReportTests(unittest.TestCase):
    @patch("kaynakca.crossref.urlopen")
    def test_offline_reports(self, request):
        report = build(ENTRY)
        request.assert_not_called()
        self.assertIsNone(report["references"][0]["crossref"])
        self.assertEqual(json.loads(to_json(report)), report)
        self.assertIn("0 hata", render(report))
        markdown = render(report, markdown=True)
        self.assertIn("| Kaynak | Baskın stil |", markdown)
        self.assertIn("- [ ] [Google Scholar]", markdown)
        self.assertIn("https://doi.org/10.0000/ornek.iz", markdown)
        self.assertIn("[TR Dizin]", markdown)
        self.assertIn("[YÖK Tez]", markdown)
        self.assertNotIn("doğrulandı", markdown)

    def test_cli_formats_and_codes(self):
        for option, match in (("--md", "# Kaynakça"), ("--json", '"references"')):
            with patch("sys.stdin", io.StringIO(ENTRY)), redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(["-", option]), 0)
                self.assertIn(match, output.getvalue())
        with patch("sys.stdin", io.StringIO("Kurgusal eksik künye")), redirect_stdout(io.StringIO()):
            self.assertEqual(main(["-"]), 1)


class CrossrefTests(unittest.TestCase):
    @patch("kaynakca.crossref.time.sleep")
    @patch("kaynakca.crossref.time.monotonic", return_value=0)
    @patch("kaynakca.crossref.urlopen")
    def test_metadata_match_mismatch_cache_errors_and_throttle(self, request, monotonic, sleep):
        data = {"message": {"title": ["Kurgusal iz"], "author": [{"family": "IŞIK"}],
                            "published": {"date-parts": [[2022]]}}}
        request.side_effect = [
            io.BytesIO(json.dumps(data).encode()),
            HTTPError("https://api.crossref.org", 404, "missing", {}, None),
            URLError("kapalı"),
            io.BytesIO(b"{}"),
        ]
        references = parse("\n".join([
            ENTRY, ENTRY.replace("2022", "2023"), ENTRY.replace("ornek.iz", "ornek.yok"),
            ENTRY.replace("ornek.iz", "ornek.ag"), ENTRY.replace("ornek.iz", "ornek.yanit"),
            ENTRY.replace("10.0000/ornek.iz", "bozuk"),
        ]))
        result = lookup(references)
        self.assertEqual([item.status for item in result.values()],
                         ["match", "mismatch", "not_found", "network_error", "response_error", "invalid"])
        self.assertIn("yıl", result[2].message)
        self.assertEqual(result[3].message, "DOI bulunamadı (404)")
        self.assertIn("ağ hatası", result[4].message)
        self.assertEqual(request.call_count, 4)
        first = request.call_args_list[0]
        self.assertEqual(first.args[0].full_url, "https://api.crossref.org/works/10.0000/ornek.iz")
        self.assertEqual(first.args[0].get_header("User-agent"), "kaynakca-denetcisi/0.1")
        self.assertEqual(first.kwargs, {"timeout": 10})
        self.assertEqual([call.args for call in sleep.call_args_list], [(0.5,)] * 3)


class MemoryConnection:
    """Run the HTTP handler on bytes without opening a listening socket."""

    def __init__(self, request):
        self.reader = io.BytesIO(request)
        self.output = b""

    def makefile(self, mode, *args):
        return self.reader

    def sendall(self, data):
        self.output += data

    def settimeout(self, value):
        pass


def exchange(method, path, headers=None, body=b""):
    lines = [f"{method} {path} HTTP/1.1", "Host: 127.0.0.1"]
    lines.extend(f"{key}: {value}" for key, value in (headers or {}).items())
    connection = MemoryConnection(("\r\n".join(lines) + "\r\n\r\n").encode() + body)
    Handler(connection, ("127.0.0.1", 12345), None)
    head, response = connection.output.split(b"\r\n\r\n", 1)
    return int(head.split()[1]), head, response


class HTTPTests(unittest.TestCase):
    @patch("kaynakca.crossref.urlopen")
    def test_post(self, request):
        route = "/api/denetle"
        self.assertEqual(exchange("POST", route)[0], HTTPStatus.FORBIDDEN)
        headers = {"X-Kaynakca-Request": "1", "Content-Length": str(MAX_BODY + 1)}
        self.assertEqual(exchange("POST", route, headers)[0], HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        body = ENTRY.encode()
        headers["Content-Length"] = str(len(body))
        status, head, content = exchange("POST", route, headers, body)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIn(b"no-store", head)
        self.assertEqual(json.loads(content)["summary"]["references"], 1)
        self.assertFalse(json.loads(content)["crossref_enabled"])

        body = json.dumps({"kaynakca": ENTRY, "crossref": True}).encode()
        headers.update({"Content-Length": str(len(body)), "Content-Type": "application/json"})
        self.assertEqual(exchange("POST", route, headers, body)[0], HTTPStatus.OK)
        request.assert_not_called()

    def test_body_limit_at_exact_boundary_and_invalid_body(self):
        headers = {"X-Kaynakca-Request": "1", "Content-Length": str(MAX_BODY)}
        self.assertEqual(exchange("POST", "/api/denetle", headers, b" " * MAX_BODY)[0], HTTPStatus.OK)
        headers["Content-Length"] = "1"
        self.assertEqual(exchange("POST", "/api/denetle", headers, b"\xff")[0], HTTPStatus.BAD_REQUEST)

    def test_get_assets(self):
        for path in ("/", "/app.js", "/style.css"):
            self.assertEqual(exchange("GET", path)[0], HTTPStatus.OK)
        self.assertEqual(exchange("GET", "/bilinmeyen")[0], HTTPStatus.NOT_FOUND)
