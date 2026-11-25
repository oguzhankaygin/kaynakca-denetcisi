import unittest

from kaynakca.parse import APA, IEEE, MLA, UNKNOWN, Reference, parse
from kaynakca.rules import audit, majority


def codes(references, document=None):
    return {item.code for item in audit(references, document)}


class RuleTests(unittest.TestCase):
    def test_missing_required_fields(self):
        findings = audit([Reference("")])
        self.assertEqual({finding.code for finding in findings},
                         {"EKSIK_YEAR", "EKSIK_AUTHORS", "EKSIK_TITLE", "EKSIK_SOURCE"})
        for finding in findings:
            self.assertEqual(finding.severity, "hata")
            self.assertEqual(finding.reference, 1)
            self.assertTrue(finding.message and finding.suggestion)

    def test_doi_shape_and_repetition(self):
        entries = parse("Örnek, A. (2022). Kurgusal eser. Örnek Yay. DOI: 10.0/bozuk\n"
                        "Örnek, A. (2023). Kurgusal tekrar. Örnek Yay. "
                        "doi:10.0000/ornek.doi https://doi.org/10.0000/ORNEK.DOI\n"
                        "Örnek, A. (2024). Kurgusal bağlantı. Örnek Yay. https://doi.org/10.0000/ornek.url")
        findings = {item.reference: item.code for item in audit(entries)}
        self.assertEqual(findings, {1: "DOI_BICIMI", 2: "DOI_TEKRARI"})

    def test_year_and_pages(self):
        entries = parse("Örnek, A. (2999). Kurgusal eser. Örnek Dergisi, 2(1), 14–3.\n"
                        "Örnek, B. (2021). Kurgusal başka eser. Örnek Dergisi, 2(1), 6/9.\n"
                        "Örnek, C. (2021). Kurgusal üçüncü eser. Örnek Dergisi, cilt 2, sayı 1, s. 3–5.")
        self.assertEqual(codes(entries), {"GELECEK_YIL", "SAYFA_BICIMI", "SAYFA_TERS"})
        self.assertEqual(entries[2].pages, "3–5")

    def test_style_duplicate_and_alpha_order(self):
        entries = parse("Şen, A. et al. (2021). KURGUSAL İZ. Örnek Yay.\n"
                        "Işık, B. ve ark. (2021). Kurgusal iz. Örnek Yay.\n"
                        '[1] A. Example, "Imaginary", Fictional Press, 2020.')
        self.assertEqual(majority(entries), APA)
        self.assertEqual(codes(entries), {"YINELENEN", "KARISIK_STIL", "YAZAR_KISALTMASI", "ALFABETIK_SIRA"})
        self.assertEqual(majority(entries[1:]), UNKNOWN)
        self.assertIn("ALFABETIK_SIRA", codes([
            Reference("", authors=["Z, Z."], style=MLA), Reference("", authors=["A, A."], style=MLA)
        ]))

    def test_number_order(self):
        entries = [Reference("", number=n, style=IEEE) for n in (1, 3, 2, None)]
        self.assertEqual([item.reference for item in audit(entries) if item.code == "NUMARA_SIRASI"], [2, 3, 4])

    def test_web_access_date(self):
        entries = parse("Örnek, A. (2022). Kurgusal web. Örnek Site. https://example.invalid/\n"
                        "Örnek, B. (2022). Başka kurgu. Örnek Site. https://example.invalid/ "
                        "Accessed 4 May 2024.\n"
                        "Örnek, C. (2022). Kurgusal makale. Örnek Dergisi, 4(2), 1–2. https://example.invalid/")
        self.assertEqual([item.reference for item in audit(entries) if item.code == "ERISIM_TARIHI"], [1])

    def test_citations(self):
        entries = parse("Işık, A. (2021). Kurgusal eser. Örnek Yay.\n"
                        '[1] C. Example, "Imaginary Tools," Fictional Press, 2022.\n'
                        "Örnek, E. (2020). Atıfsız kurgusal eser. Örnek Yay.")
        findings = audit(entries, "Bilgi (IŞIK ve ark., 2021; Kurgu, 2020, s. 3) ve [1, 9].")
        unmatched = [item.message for item in findings if item.code == "ATIF_KARSILIKSIZ"]
        self.assertEqual(len(unmatched), 2)
        self.assertIn("Kurgu", unmatched[0])
        self.assertIn("[9]", unmatched[1])
        self.assertEqual([item.reference for item in findings if item.code == "ATIF_YOK"], [3])


class DoiDuplicateTest(unittest.TestCase):
    def test_same_doi_different_titles(self):
        text = ("Örnek, A. (2020). Birinci başlık. Kurgu Dergisi, 1(1), 1–5. https://doi.org/10.0000/ornek.ayni\n"
                "Deneme, B. (2021). İkinci başlık. Kurgu Dergisi, 2(1), 6–9. https://doi.org/10.0000/ornek.ayni\n")
        found = [f for f in audit(parse(text)) if f.code == "DOI_YINELENEN"]
        self.assertEqual([f.reference for f in found], [2])

