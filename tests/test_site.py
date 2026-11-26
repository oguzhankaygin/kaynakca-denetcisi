import json
from pathlib import Path
import unittest
from unittest.mock import patch

from kaynakca.browser import audit_json, collect_dois
from kaynakca.report import build, render

ROOT = Path(__file__).resolve().parent.parent
ENTRY = "Işık, A. (2022). Kurgusal iz. Örnek Yay. doi:10.0000/ornek.iz"


class SiteTests(unittest.TestCase):
    def test_published_copies_are_current(self):
        package = ROOT / "kaynakca"
        docs = ROOT / "docs"
        py = docs / "py"
        names = sorted(source.name for source in package.glob("*.py"))
        self.assertEqual(json.loads((py / "manifest.json").read_text(encoding="utf-8")), names)
        self.assertEqual(sorted(copy.name for copy in (py / "kaynakca").glob("*.py")), names)
        for name in names:
            with self.subTest(name=name):
                self.assertEqual((py / "kaynakca" / name).read_bytes(), (package / name).read_bytes())
        for name in ("app.js", "style.css"):
            with self.subTest(name=name):
                self.assertEqual((docs / name).read_bytes(), (package / "static" / name).read_bytes())
        self.assertTrue((docs / ".nojekyll").is_file())

    def test_service_worker_precache_files_exist(self):
        docs = ROOT / "docs"
        sw = (docs / "sw.js").read_text(encoding="utf-8")
        listing = json.loads(sw.split("const DOSYALAR = ", 1)[1].split(";\n", 1)[0])
        for name in listing[1:]:
            with self.subTest(name=name):
                self.assertTrue((docs / name).is_file())
        pages = (docs / "pages.js").read_text(encoding="utf-8")
        pinned = pages.split('const pyodideUrl = "', 1)[1].split('"', 1)[0]
        self.assertIn(f'const PYODIDE = "{pinned}";', sw)

    @patch("kaynakca.crossref.urlopen")
    def test_offline_report_and_markdown(self, request):
        for text in (ENTRY, (ROOT / "ornekler/kaynakca.bib").read_text(encoding="utf-8")):
            with self.subTest(text=text[:30]):
                result = json.loads(audit_json(text))
                report = build(text)
                self.assertEqual(result["report"], report)
                self.assertEqual(result["markdown"], render(report, markdown=True))
        request.assert_not_called()

    @patch("kaynakca.crossref.urlopen")
    def test_browser_supplied_crossref_responses(self, request):
        text = "\n".join([
            ENTRY, ENTRY.replace("2022", "2023").replace("ornek.iz", "ORNEK.IZ"),
            ENTRY.replace("ornek.iz", "yok"), ENTRY.replace("ornek.iz", "ag"),
            ENTRY.replace("ornek.iz", "yanit"), ENTRY.replace("ornek.iz", "limit"),
            ENTRY.replace("10.0000/ornek.iz", "bozuk"),
        ])
        self.assertEqual(json.loads(collect_dois(text)), {
            f"10.0000/{suffix}": f"10.0000/{suffix}"
            for suffix in ("ornek.iz", "yok", "ag", "yanit", "limit")
        })
        responses = {
            "10.0000/ornek.iz": {"status": 200, "payload": {"message": {
                "title": ["Kurgusal iz"], "author": [{"family": "IŞIK"}],
                "published": {"date-parts": [[2022]]},
            }}},
            "10.0000/yok": {"status": 404},
            "10.0000/ag": {"status": 0},
            "10.0000/yanit": {"status": 200},
            "10.0000/limit": {"status": 429},
        }
        result = json.loads(audit_json(text, json.dumps(responses)))
        self.assertTrue(result["report"]["crossref_enabled"])
        self.assertEqual(
            [ref["crossref"]["status"] for ref in result["report"]["references"]],
            ["match", "mismatch", "not_found", "network_error", "response_error", "network_error", "invalid"],
        )
        self.assertIn("DOI kaydıyla uyumlu", result["markdown"])
        request.assert_not_called()
