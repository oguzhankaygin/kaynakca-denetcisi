"""İsteğe bağlı DOI meta verisi karşılaştırması."""

import json
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .parse import DOI, normalize, surname


@dataclass
class CrossrefResult:
    status: str
    message: str


def _compare(ref, metadata):
    title = (metadata.get("title") or [""])[0]
    authors = metadata.get("author") or []
    first_author = authors[0].get("family") or authors[0].get("name", "") if authors else ""
    year = None
    for field in ("published", "issued", "published-print", "published-online"):
        parts = (metadata.get(field) or {}).get("date-parts") or []
        if parts and parts[0]:
            year = parts[0][0]
            break
    differences = []
    for label, local, remote in (
        ("başlık", normalize(ref.title), normalize(title)),
        ("yıl", ref.year, year),
        ("ilk yazar", surname(ref.authors[0]) if ref.authors else "", normalize(first_author)),
    ):
        if not local or not remote:
            differences.append(f"{label} karşılaştırılamadı")
        elif local != remote:
            differences.append(label)
    if differences:
        return CrossrefResult("mismatch", "DOI kaydıyla uyumsuz: " + ", ".join(differences))
    return CrossrefResult("match", "DOI kaydıyla uyumlu")


def lookup(references):
    results = {}
    cache = {}
    last_start = None
    for index, ref in enumerate(references, 1):
        if not ref.doi:
            continue
        if not DOI.fullmatch(ref.doi):
            results[index] = CrossrefResult("invalid", "Geçersiz DOI biçimi; sorgu yapılmadı.")
            continue
        key = ref.doi.casefold()
        if key not in cache:
            if last_start is not None:
                time.sleep(max(0, 0.5 - (time.monotonic() - last_start)))
            request = Request(
                "https://api.crossref.org/works/" + quote(ref.doi, safe="/"),
                headers={"User-Agent": "kaynakca-denetcisi/0.1", "Accept": "application/json"},
            )
            last_start = time.monotonic()
            try:
                with urlopen(request, timeout=10) as response:
                    metadata = json.load(response)["message"]
                if not isinstance(metadata, dict):
                    raise ValueError("Nesne bekleniyordu.")
                cache[key] = metadata
            except HTTPError as error:
                error.close()
                cache[key] = (
                    CrossrefResult("not_found", "DOI bulunamadı (404)") if error.code == 404
                    else CrossrefResult("network_error", f"Crossref ağ hatası (HTTP {error.code}).")
                )
            except (URLError, OSError) as error:
                cache[key] = CrossrefResult("network_error", f"Crossref ağ hatası: {error}")
            except (AttributeError, KeyError, TypeError, ValueError) as error:
                cache[key] = CrossrefResult("response_error", f"Crossref yanıtı okunamadı: {error}")
        value = cache[key]
        try:
            results[index] = value if isinstance(value, CrossrefResult) else _compare(ref, value)
        except (AttributeError, IndexError, TypeError, ValueError) as error:
            results[index] = CrossrefResult("response_error", f"Crossref yanıtı okunamadı: {error}")
    return results
