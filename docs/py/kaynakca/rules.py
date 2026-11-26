"""Çevrimdışı kaynakça ve atıf denetimleri."""

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from urllib.parse import unquote

from .parse import APA, DOI, IEEE, MLA, UNKNOWN, YEAR, normalize, surname


@dataclass
class Finding:
    code: str
    severity: str
    message: str
    suggestion: str
    reference: int | None = None


def majority(references):
    counts = Counter(ref.style for ref in references if ref.style != UNKNOWN)
    leading = counts.most_common(2)
    if not leading or (len(leading) == 2 and leading[0][1] == leading[1][1]):
        return UNKNOWN
    return leading[0][0]


def _citations(references, document, add):
    names = defaultdict(set)
    numbers = defaultdict(set)
    for index, ref in enumerate(references, 1):
        if ref.authors and ref.year:
            for name in {surname(ref.authors[0]), normalize(ref.authors[0])}:
                names[name, ref.year].add(index)
        if ref.number is not None:
            numbers[ref.number].add(index)

    cited = set()

    def record(label, matches):
        if matches:
            cited.update(matches)
        else:
            add("ATIF_KARSILIKSIZ", "uyari", f"Kaynakçada karşılığı yok: {label}",
                "Kaynakçayı veya metindeki atfı düzeltin.")

    for group in re.finditer(r"\(([^()]+)\)", document):
        for part in group[1].split(";"):
            match = re.fullmatch(rf"\s*(.+?),\s*({YEAR})[a-z]?(?:\s*,\s*.+)?\s*", part)
            if not match or not re.search(r"[^\W\d_]", match[1]):
                continue
            first = re.split(r"\s+(?:ve\s+ark\.?|et\s+al\.?|&|and|ve)\s*", match[1], maxsplit=1, flags=re.I)[0]
            record(f"({part.strip()})", names[normalize(first), int(match[2])])
    for match in re.finditer(r"\[\s*(\d+(?:\s*,\s*\d+)*)\s*\]", document):
        for number in re.findall(r"\d+", match[1]):
            record(f"[{number}]", numbers[int(number)])
    for index in range(1, len(references) + 1):
        if index not in cited:
            add("ATIF_YOK", "bilgi", "Bu kaynağa metinde atıf bulunamadı.",
                "Metindeki atfı kontrol edin.", index)


def audit(references, document=None):
    findings = []

    def add(code, severity, message, suggestion, reference=None):
        findings.append(Finding(code, severity, message, suggestion, reference))

    style = majority(references)
    seen = {}
    seen_doi = {}
    short_forms = defaultdict(list)
    last_author = ()
    ieee_numbers = [ref.number for ref in references if ref.style == IEEE]
    check_numbers = style == IEEE or bool(ieee_numbers)
    expected_number = 0

    for index, ref in enumerate(references, 1):
        for field, label in (("year", "Yıl"), ("title", "Başlık"), ("authors", "Yazar"),
                             ("source", "Dergi, yayınevi veya site adı")):
            if not getattr(ref, field):
                add("EKSIK_" + field.upper(), "hata", f"{label} eksik.",
                    f"{label} bilgisini kaynağın künyesinden ekleyin.", index)
        if ref.doi and not DOI.fullmatch(ref.doi):
            add("DOI_BICIMI", "hata", "DOI biçimi geçersiz.",
                "DOI’yi 10.xxxx/… biçiminde kontrol edin.", index)
        if (ref.doi and not ref.doi_from_url and re.fullmatch(
                r"https?://(?:dx\.)?doi\.org/" + re.escape(ref.doi), unquote(ref.url), re.I)):
            add("DOI_TEKRARI", "uyari", "DOI, URL alanında da yer alıyor.",
                "DOI’yi stilinizin gerektirdiği tek gösterimle yazın.", index)
        if ref.year and ref.year > date.today().year:
            add("GELECEK_YIL", "hata", f"Yayın yılı gelecekte: {ref.year}.",
                "Yayın tarihini kontrol edin.", index)
        if ref.pages:
            match = re.fullmatch(r"([A-Za-z]?)(\d+)(?:\s*(?:--?|[–—])\s*([A-Za-z]?)(\d+))?", ref.pages)
            if not match:
                add("SAYFA_BICIMI", "uyari", "Sayfa aralığı okunamadı.",
                    "Sayfaları 12–18 biçiminde yazın.", index)
            elif match[4] and int(match[2]) > int(match[4]):
                add("SAYFA_TERS", "uyari", "Başlangıç sayfası bitiş sayfasından büyük.",
                    "Sayfa sırasını kontrol edin.", index)
        if style != UNKNOWN and ref.style not in {UNKNOWN, style}:
            add("KARISIK_STIL", "uyari", f"{ref.style} tahmini, baskın {style} stilinden farklı.",
                "Kaynakçayı tek atıf stiline göre düzenleyin.", index)
        key = normalize(ref.title), ref.year
        if all(key):
            if key in seen:
                add("YINELENEN", "uyari", f"Başlık ve yıl {seen[key]}. kaynakla aynı.",
                    "Kayıtları karşılaştırıp mükerrer kaydı kaldırın.", index)
            else:
                seen[key] = index
        if ref.doi and DOI.fullmatch(ref.doi):
            doi_key = ref.doi.lower()
            duplicate_title = any(f.code == "YINELENEN" and f.reference == index for f in findings)
            if doi_key in seen_doi and not duplicate_title:
                add("DOI_YINELENEN", "uyari", f"DOI {seen_doi[doi_key]}. kaynakla aynı.",
                    "Aynı DOI iki farklı künyede olamaz; DOI'nin hangi kaynağa ait olduğunu kontrol edin.",
                    index)
            seen_doi.setdefault(doi_key, index)
        for label, pattern in (("et al.", r"\bet\s+al\."), ("ve ark.", r"\bve\s+ark\.")):
            if re.search(pattern, ref.author_text, re.I):
                short_forms[label].append(index)
        if ref.url and not ref.access_date and ref.kind in {"web", "online", "www", "electronic", "misc"}:
            add("ERISIM_TARIHI", "uyari", "Web kaynağında erişim tarihi eksik.",
                "Kaynağa eriştiğiniz tarihi ekleyin.", index)
        if style in {APA, MLA} and ref.authors:
            author = surname(ref.authors[0])
            alphabet = "abcçdefgğhijklmnoöpqrsştuüvwxyz"
            collation = tuple(alphabet.index(char) if char in alphabet else ord(char) + 100
                              for char in author)
            if last_author and collation < last_author:
                add("ALFABETIK_SIRA", "uyari", "İlk yazar kaynakça sırasına uymuyor.",
                    "Kaynakları ilk yazarın soyadına göre sıralayın.", index)
            last_author = collation
        if check_numbers and (style == IEEE or ref.style == IEEE):
            expected_number += 1
            if ref.number != expected_number:
                add("NUMARA_SIRASI", "uyari", f"Beklenen IEEE numarası [{expected_number}].",
                    "Kaynak numaralarını 1’den başlayarak ardışık yazın.", index)

    if len(short_forms) > 1:
        add("YAZAR_KISALTMASI", "uyari", "Kaynakçada hem “et al.” hem “ve ark.” kullanılmış.",
            "Atıf stiline ve belgenin diline uygun tek kısaltma kullanın.")
    if document is not None:
        _citations(references, document, add)
    return findings
