"""Ortak rapor modeli ve çıktı biçimleri."""

import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict
from html import escape
from urllib.parse import quote, urlencode

from . import crossref
from .parse import normalize, parse
from .rules import audit, majority

NOTICE = "Biçim denetimi ve DOI meta verisi karşılaştırması kaynak gerçekliğini kanıtlamaz."


def links(ref):
    query = ref.title or " ".join(ref.authors) or ref.raw
    result = {
        "Google Scholar": "https://scholar.google.com/scholar?" + urlencode({"q": query}),
        "Crossref": "https://search.crossref.org/?" + urlencode({"q": query}),
    }
    if ref.doi:
        result["DOI"] = "https://doi.org/" + quote(ref.doi, safe="/")
    language = normalize(ref.language)
    sample = f"{ref.title} {ref.source} {ref.author_text}"
    if (language in {"tr", "tr tr", "tur", "turkish", "türkçe"}
            or re.search(r"[çğıöşüİÇĞÖŞÜ]", sample)
            or re.search(r"\b(?:ve|icin|yayinlari|dergisi)\b", normalize(sample))):
        result["TR Dizin"] = "https://search.trdizin.gov.tr/tr/yayin/ara"
        result["YÖK Tez"] = "https://tez.yok.gov.tr/UlusalTezMerkezi/"
    return result


def build(text, *, bibtex=False, document=None, online=False, crossref_responses=None):
    refs = parse(text, bibtex)
    findings = audit(refs, document)
    by_reference = defaultdict(list)
    counts = Counter(f.severity for f in findings)
    for finding in findings:
        by_reference[finding.reference].append(asdict(finding))
    if crossref_responses is not None:
        results = crossref.compare_responses(refs, crossref_responses)
    else:
        results = crossref.lookup(refs) if online else {}
    return {
        "notice": NOTICE,
        "crossref_enabled": online or crossref_responses is not None,
        "summary": {
            "references": len(refs), "style": majority(refs),
            **{level: counts[level] for level in ("hata", "uyari", "bilgi")},
        },
        "findings": by_reference[None],
        "references": [
            {
                **asdict(ref), "index": index, "findings": by_reference[index],
                "links": links(ref), "crossref": asdict(results[index]) if index in results else None,
            }
            for index, ref in enumerate(refs, 1)
        ],
    }


def to_json(report):
    return json.dumps(report, ensure_ascii=False, indent=2)


def _markdown(value):
    return re.sub(r"([\\`*_{}\[\]()#+.!|~\-])", r"\\\1", escape(str(value)))


def _findings(items, markdown):
    safe = _markdown if markdown else str
    return [
        f"- [{item['severity']}] {item['code']} — {safe(item['message'])} Öneri: {safe(item['suggestion'])}"
        for item in items
    ]


def render(report, *, markdown=False):
    summary = report["summary"]
    heading = "#" if markdown else ""
    lines = [
        f"{heading} Kaynakça denetim raporu".lstrip(), "", report["notice"],
        "Crossref: " + ("açık" if report["crossref_enabled"] else "kapalı"), "",
    ]
    if markdown:
        lines += [
            "| Kaynak | Baskın stil | Hata | Uyarı | Bilgi |",
            "| ---: | --- | ---: | ---: | ---: |",
            f"| {summary['references']} | {summary['style']} | {summary['hata']} | {summary['uyari']} | {summary['bilgi']} |",
        ]
    else:
        lines.append(
            f"{summary['references']} kaynak · Baskın stil: {summary['style']} · "
            f"{summary['hata']} hata, {summary['uyari']} uyarı, {summary['bilgi']} bilgi"
        )
    if report["findings"]:
        lines += ["", "## Belge bulguları" if markdown else "Belge bulguları", ""]
        lines += _findings(report["findings"], markdown)
    for ref in report["references"]:
        title = ref["title"] or "Başlık ayrıştırılamadı"
        if markdown:
            title = _markdown(title)
        lines += [
            "", ("## " if markdown else "") + f"{ref['index']}. {title}", "",
            f"Stil tahmini: {ref['style']} ({ref['confidence']:.0%})",
        ]
        # Keep finding lists and checklists separate in Markdown.
        if ref["findings"]:
            lines += ["", *_findings(ref["findings"], markdown)]
        else:
            lines += ["", "Biçim bulgusu yok."]
        if ref["crossref"]:
            message = ref["crossref"]["message"]
            lines += ["", _markdown(message) if markdown else message]
        lines += ["", "Elle doğrulama kontrol listesi", ""]
        for name, url in ref["links"].items():
            lines.append(f"- [ ] [{name}](<{url}>)" if markdown else f"[ ] {name}: {url}")
    return "\n".join(lines)
