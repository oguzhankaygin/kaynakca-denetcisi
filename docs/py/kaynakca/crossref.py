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


def doi_requests(references):
    """Tekil geçerli DOI'leri ilk yazımlarıyla döndür."""
    requests = {}
    for ref in references:
        if ref.doi and DOI.fullmatch(ref.doi):
            requests.setdefault(ref.doi.casefold(), ref.doi)
    return requests


def lookup(references, fetch=None):
    results = {}
    cache = {}
    if fetch is None:
        fetch = _network_fetcher()
    for index, ref in enumerate(references, 1):
        if not ref.doi:
            continue
        if not DOI.fullmatch(ref.doi):
            results[index] = CrossrefResult("invalid", "Geçersiz DOI biçimi; sorgu yapılmadı.")
            continue
        key = ref.doi.casefold()
        if key not in cache:
            cache[key] = fetch(ref.doi)
        value = cache[key]
        try:
            results[index] = value if isinstance(value, CrossrefResult) else _compare(ref, value)
        except (AttributeError, IndexError, TypeError, ValueError) as error:
            results[index] = CrossrefResult("response_error", f"Crossref yanıtı okunamadı: {error}")
    return results


def _network_fetcher():
    last_start = None

    def fetch(doi):
        nonlocal last_start
        if last_start is not None:
            time.sleep(max(0, 0.5 - (time.monotonic() - last_start)))
        request = Request(
            "https://api.crossref.org/works/" + quote(doi, safe="/"),
            headers={"User-Agent": "kaynakca-denetcisi/0.1", "Accept": "application/json"},
        )
        last_start = time.monotonic()
        try:
            with urlopen(request, timeout=10) as response:
                metadata = json.load(response)["message"]
            if not isinstance(metadata, dict):
                raise ValueError("Nesne bekleniyordu.")
            return metadata
        except HTTPError as error:
            error.close()
            return (
                CrossrefResult("not_found", "DOI bulunamadı (404)") if error.code == 404
                else CrossrefResult("network_error", f"Crossref ağ hatası (HTTP {error.code}).")
            )
        except (URLError, OSError) as error:
            return CrossrefResult("network_error", f"Crossref ağ hatası: {error}")
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            return CrossrefResult("response_error", f"Crossref yanıtı okunamadı: {error}")

    return fetch


def compare_responses(references, responses):
    """Tarayıcının aldığı Crossref yanıtlarını ağ isteği yapmadan karşılaştır."""
    def fetch(doi):
        response = responses.get(doi.casefold(), {})
        status = response.get("status")
        if status == 404:
            return CrossrefResult("not_found", "DOI bulunamadı (404)")
        if not status:
            return CrossrefResult("network_error", "Crossref isteği başarısız oldu veya zaman aşımına uğradı.")
        if not 200 <= status < 300:
            return CrossrefResult("network_error", f"Crossref ağ hatası (HTTP {status}).")
        payload = response.get("payload")
        metadata = payload.get("message") if isinstance(payload, dict) else None
        if not isinstance(metadata, dict):
            return CrossrefResult("response_error", "Crossref yanıtı okunamadı.")
        return metadata

    return lookup(references, fetch)
