import unittest

from kaynakca.parse import APA, CHICAGO, IEEE, MLA, UNKNOWN, normalize, parse, surname


class ParseTests(unittest.TestCase):
    def test_styles_and_fields(self):
        cases = [
            ("• Işık, A., Şen, B., & Örnek, C. (2021). Kurgusal Şehir. Örnek Yay., 4(2), 8–12.",
             APA, "Kurgusal Şehir", "Örnek Yay", "4", "2", "8–12", 2021),
            ("[1] A. Example, “Imaginary Tools,” Fictional Journal, vol. 4, no. 2, pp. 8–12, 2021.",
             IEEE, "Imaginary Tools", "Fictional Journal", "4", "2", "8–12", 2021),
            ('1. Example, Alex. "Imaginary Tools." Fictional Journal, vol. 4, no. 2, 2021, pp. 8–12.',
             IEEE, "Imaginary Tools", "Fictional Journal", "4", "2", "8–12", 2021),
            ('Example, Alex. "Imaginary Tools." Fictional Journal, vol. 4, no. 2, 2021, pp. 8–12.',
             MLA, "Imaginary Tools", "Fictional Journal", "4", "2", "8–12", 2021),
            ("Example, Alex. Imaginary Tools. Fictional Press, 2021.",
             MLA, "Imaginary Tools", "Fictional Press", "", "", "", 2021),
            ('Örnek, Ayşe. 2021. “Kurgusal Şehir.” Örnek Dergisi 4 (2): 8–12.',
             CHICAGO, "Kurgusal Şehir", "Örnek Dergisi", "4", "2", "8–12", 2021),
            ("Örnek, Ayşe. Kurgusal Şehir. Örnek Yay.",
             UNKNOWN, "Kurgusal Şehir", "Örnek Yay", "", "", "", None),
        ]
        for raw, style, title, source, volume, issue, pages, year in cases:
            with self.subTest(style=style, raw=raw):
                ref, = parse(raw)
                self.assertEqual(
                    (ref.style, ref.title, ref.source, ref.volume, ref.issue, ref.pages, ref.year),
                    (style, title, source, volume, issue, pages, year),
                )
                self.assertTrue(ref.authors)
                self.assertEqual(ref.confidence > 0, style != UNKNOWN)

    def test_turkish_authors_and_date(self):
        ref, = parse("  - Işık, A., Şen, B., & Örnek, C. (2022, 4 Mayıs). Kurgusal arşiv. Örnek Site.\n"
                     "    https://example.invalid/arsiv Erişim tarihi: 4 Mayıs 2024.")
        self.assertEqual(ref.authors, ["Işık, A.", "Şen, B.", "Örnek, C."])
        self.assertEqual(ref.access_date, "4 Mayıs 2024")
        self.assertEqual(ref.url, "https://example.invalid/arsiv")
        self.assertEqual(ref.year, 2022)
        self.assertEqual(normalize("IŞIK, İNCİ, ÇAĞRI"), normalize("ışık, inci, çağrı"))
        self.assertEqual(normalize("S\u0327EN"), normalize("şen"))
        self.assertEqual(surname("A. Işık"), surname("IŞIK, A."))

    def test_bibtex_nested_macros_and_fields(self):
        entries = parse('''% kurgusal
@string{press="Örnek"}
@comment{Bu {yorum} atlanır.}
@preamble{"Örnek"}
@article(anahtar,
    author={Örnek, A. and {Research and Fiction Group}},
    title={Bir {Kurgusal} Çalışma},
    journal=press # " Yay.",
    date={2023-06-01}, volume=2, number=1, pages={2--8},
    doi={10.0000/ornek.bib}, url={https://example.invalid/},
    urldate={2024-06-03}, langid={turkish}
)''')
        ref, = entries
        self.assertEqual(ref.authors, ["Örnek, A.", "Research and Fiction Group"])
        self.assertEqual((ref.title, ref.source, ref.year), ("Bir Kurgusal Çalışma", "Örnek Yay.", 2023))
        self.assertEqual((ref.volume, ref.issue, ref.pages), ("2", "1", "2--8"))
        self.assertEqual(ref.doi, "10.0000/ornek.bib")
        self.assertEqual(ref.access_date, "2024-06-03")
        self.assertEqual(ref.language, "turkish")
        self.assertEqual(ref.style, UNKNOWN)
        with self.assertRaises(ValueError):
            parse("@book{k, title={Kapanmamış", bibtex=True)
