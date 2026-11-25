"""Kaynakça alanları ve sezgisel stil ayrıştırma."""

import re
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import unquote

APA = "APA 7"
IEEE = "IEEE"
MLA = "MLA"
CHICAGO = "Chicago (yazar-tarih)"
UNKNOWN = "bilinmeyen"
YEAR = r"(?:1[0-9]{3}|2[0-9]{3})"
NUMBER = re.compile(r"^\s*(?:\[(\d+)\]|(\d+)\.)\s*")
BULLET = re.compile(r"^\s*[-*•–]\s+")
DOI = re.compile(r"10\.\d{4,9}/[^\s<>\"?#]+", re.I)
URL = re.compile(r"https?://[^\s<>\"\]\}\)]+", re.I)
ACCESS = re.compile(
    r"(?:erişim(?: tarihi)?|accessed|retrieved)\s*[:.,]?\s*"
    r"(\d{4}-\d{2}-\d{2}|\d{1,2}[./-]\d{1,2}[./-]\d{4}|"
    r"\d{1,2}\.?\s+[^\W\d_]+\.?\s+\d{4}|[^\W\d_]+\s+\d{1,2},?\s+\d{4})", re.I
)


@dataclass
class Reference:
    raw: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    title: str = ""
    source: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doi: str = ""
    url: str = ""
    access_date: str = ""
    style: str = UNKNOWN
    confidence: float = 0.0
    number: int | None = None
    kind: str = ""
    language: str = ""
    author_text: str = ""
    doi_from_url: bool = False


def normalize(value):
    value = unicodedata.normalize("NFC", value).translate(str.maketrans("Iİı", "iii"))
    return " ".join(re.findall(r"[^\W_]+", value.casefold()))


def surname(author):
    if "," in author:
        return normalize(author.split(",", 1)[0])
    words = [word for word in author.split() if word.strip(".")]
    return normalize(words[-1]) if words else ""


def _authors(value, style):
    value = re.sub(r"\b(?:et\s+al|ve\s+ark)\.?", "", value, flags=re.I)
    parts = re.split(r"\s*(?:;|\s+&|\s+ve\s+|\s+and\s+)\s*", value, flags=re.I)
    result = []
    for part in parts:
        part = part.strip(" ,;")
        if not part:
            continue
        inverted = re.findall(r"(?:^|,\s*)([^,]+,\s*(?:[^\W\d_]\.\s*)+)(?=,|$)", part)
        if len(inverted) > 1:
            result.extend(author.strip() for author in inverted)
        elif style == IEEE:
            result.extend(re.split(r",\s*(?=[^\W\d_]\.)", part))
        else:
            result.append(part)
    return result


def _period(value):
    """Find the first sentence separator, skipping initials and abbreviations."""
    for match in re.finditer(r"\.(?=\s|$)", value):
        prefix = value[:match.start()]
        token = re.search(r"[^\W\d_]+$", prefix)
        if token and (len(token[0]) == 1 or token[0].casefold() in {
            "ark", "al", "yay", "vol", "no", "pp", "ed", "eds", "dr",
        }):
            continue
        return prefix.strip(), value[match.end():].strip()
    return value.strip(" ."), ""


def _metadata(ref, source):
    # Explicit labels take precedence over an unlabelled volume(issue) tuple.
    for name, label in (("volume", r"vol\.?|cilt"), ("issue", r"no\.?|sayı"),
                        ("pages", r"pp?\.?|s\.|sayfa")):
        match = re.search(rf"(?:^|[,;])\s*(?:{label})(?=\s|:|\d)\s*:?\s*([^,;]+)", source, re.I)
        if match:
            setattr(ref, name, match[1].strip(" ."))
    compact = re.search(
        r"(?P<separator>,\s*|\s+)(\d+)(?:\s*\(\s*(\d+)\s*\))?\s*[:,]\s*([^,;]+)", source
    ) if not ref.volume else None
    if compact:
        ref.volume = compact[2]
        ref.issue = ref.issue or compact[3] or ""
        ref.pages = ref.pages or compact[4].strip(" .")
    boundary = re.search(
        r"[,;]\s*(?:(?:vol\.?|cilt|no\.?|sayı|pp?\.|s\.|sayfa)\s*:?\s*\d|\d+(?:\s*[(:,]|\s*$))",
        source, re.I
    )
    separator = boundary or compact
    ref.source = (source[:separator.start()] if separator else source).strip(" ,.;:")


def _plain(raw):
    ref = Reference(raw)
    raw = " ".join(raw.split())
    numbered = NUMBER.match(raw)
    if numbered:
        ref.number = int(numbered[1] or numbered[2])
        raw = raw[numbered.end():]
    raw = BULLET.sub("", raw)
    links = list(URL.finditer(raw))
    if links:
        ref.url = next(
            (m[0].rstrip(".,;") for m in links if "doi.org/" in m[0].lower()),
            links[0][0].rstrip(".,;")
        )
        linked_doi = re.match(r"https?://(?:dx\.)?doi\.org/(.+)", ref.url, re.I)
        if linked_doi:
            ref.doi = unquote(linked_doi[1])
            ref.doi_from_url = True
    raw = URL.sub("", raw)
    explicit_doi = re.search(r"\bdoi\s*:\s*([^\s,;]+)", raw, re.I)
    bare_doi = DOI.search(raw)
    doi = explicit_doi or bare_doi
    if doi:
        ref.doi = (doi[1] if explicit_doi else doi[0]).rstrip(".,;")
        ref.doi_from_url = False
        raw = raw[:doi.start()] + raw[doi.end():]
    access = ACCESS.search(raw)
    if access:
        ref.access_date = access[1]
        raw = raw[:access.start()] + raw[access.end():]
    raw = re.sub(r"\s+\.", ".", raw).strip(" ,;[]")
    quoted = re.search(r'["“]([^"”]+)["”]', raw)
    apa = re.search(rf"\(\s*({YEAR}|t\.y\.|n\.d\.)[a-z]?(?:\s*,[^()]*)?\s*\)\s*\.", raw, re.I)
    chicago = re.search(rf"\.\s+({YEAR})[a-z]?\.\s*", raw)
    year = re.search(rf"\b({YEAR})[a-z]?\b", raw)
    if apa:
        ref.style, ref.confidence = APA, 0.95
        ref.author_text = raw[:apa.start()].strip(" ,")
        ref.title, source = _period(raw[apa.end():])
        year = re.search(YEAR, apa[1])
    elif chicago and (not quoted or chicago.end() <= quoted.start()):
        ref.style, ref.confidence = CHICAGO, 0.9
        ref.author_text = raw[:chicago.start() + 1].strip(" ,")
        if quoted:
            ref.title, source = quoted[1].strip(" .,"), raw[quoted.end():]
        else:
            ref.title, source = _period(raw[chicago.end():])
    elif quoted:
        ieee = ref.number is not None or bool(re.search(r"\bvol\.\s*\d.*\bno\.", raw, re.I)
                                              and re.match(r"\s*[^\W\d_]\.", raw))
        ref.style, ref.confidence = (IEEE, 0.95) if ieee else (MLA, 0.8)
        ref.author_text = raw[:quoted.start()].strip(" ,")
        ref.title = quoted[1].strip(" .,")
        source = raw[quoted.end():]
        year = re.search(rf"\b({YEAR})[a-z]?\b", source)
    else:
        ref.author_text, tail = _period(raw)
        ref.title, source = _period(tail)
        if year and re.search(rf",\s*{YEAR}\.?\s*$", raw):
            if ref.number is not None and re.match(r"\s*[^\W\d_]\.", raw):
                ref.style, ref.confidence = IEEE, 0.75
            elif "," in ref.author_text and source:
                ref.style, ref.confidence = MLA, 0.7
        if not tail:
            ref.author_text, ref.title = "", ref.author_text
    if year:
        ref.year = int(year[0][:4])
        source = re.sub(rf"(?:[, (]|^){ref.year}[a-z]?(?=\W|$)\)?", "", source)
    ref.authors = _authors(ref.author_text, ref.style)
    _metadata(ref, source.strip(" .,;"))
    if ref.url and not ref.doi and not ref.volume and not ref.pages:
        ref.kind = "web"
    return ref


# BibTeX values may be quoted, nested braces, bare macros, or concatenations.
_BIB_TOKEN = re.compile(r'\s*(?:%[^\n]*\s*)*')
_BIB_ENTRY = re.compile(r"@(\w+)\s*([({])")


def _bib_space(text, pos):
    return _BIB_TOKEN.match(text, pos).end()


def _bib_value(text, pos):
    start = pos
    opener = text[pos:pos + 1]
    if opener not in {"{", '"'}:
        match = re.match(r"[^\s,#})]+", text[pos:])
        if not match:
            raise ValueError("BibTeX alan değeri eksik.")
        return match[0], pos + len(match[0]), False
    pos += 1
    depth = 0
    while pos < len(text):
        char = text[pos]
        if char == "\\":
            pos += 2
            continue
        if depth == 0 and char == ('}' if opener == '{' else '"'):
            return text[start + 1:pos], pos + 1, True
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        pos += 1
    raise ValueError("Kapanmamış BibTeX alan değeri.")


def _bib_entries(text):
    pos = 0
    macros = {}
    while pos < len(text):
        pos = _bib_space(text, pos)
        if pos == len(text):
            break
        entry = _BIB_ENTRY.match(text, pos)
        if not entry:
            raise ValueError("BibTeX kayıt başlığı bekleniyor.")
        kind, opener = entry[1].lower(), entry[2]
        closer = "}" if opener == "{" else ")"
        start = pos
        pos = _bib_space(text, entry.end())
        if kind == "comment":
            _, pos, _ = _bib_value(text, entry.end() - 1) if opener == "{" else ("", text.find(")", pos) + 1, True)
            if not pos:
                raise ValueError("Kapanmamış BibTeX yorumu.")
            continue
        if kind not in {"string", "preamble"}:
            key = re.match(r"[^\s,})]+", text[pos:])
            if not key:
                raise ValueError("BibTeX kayıt anahtarı eksik.")
            pos = _bib_space(text, pos + len(key[0]))
            if text[pos:pos + 1] == ",":
                pos += 1
            elif text[pos:pos + 1] != closer:
                raise ValueError("BibTeX kayıt anahtarından sonra virgül bekleniyor.")
        fields = {}
        while True:
            pos = _bib_space(text, pos)
            if text[pos:pos + 1] == closer:
                pos += 1
                break
            name = re.match(r"(\w+)\s*=\s*", text[pos:])
            if not name and kind != "preamble":
                raise ValueError("BibTeX alanı veya kayıt sonu bekleniyor.")
            pos += name.end() if name else 0
            pieces = []
            while True:
                value, pos, literal = _bib_value(text, _bib_space(text, pos))
                pieces.append(value if literal else macros.get(value.lower(), value))
                pos = _bib_space(text, pos)
                if text[pos:pos + 1] != "#":
                    break
                pos += 1
            if name:
                fields[name[1].lower()] = "".join(pieces)
            if text[pos:pos + 1] == ",":
                pos += 1
            elif text[pos:pos + 1] != closer:
                raise ValueError("BibTeX alanından sonra virgül bekleniyor.")
        if kind == "string":
            macros.update(fields)
        elif kind != "preamble":
            yield kind, fields, text[start:pos]


def _bib(text):
    for kind, fields, raw in _bib_entries(text):
        author_text = fields.get("author") or fields.get("editor", "")
        # Split only top-level conjunctions, preserving institutional names.
        authors = []
        depth = start = 0
        for token in re.finditer(r"[{}]|\s+and\s+", author_text, re.I):
            if token[0] == "{":
                depth += 1
            elif token[0] == "}":
                depth -= 1
            elif not depth:
                authors.append(author_text[start:token.start()].strip())
                start = token.end()
        authors.append(author_text[start:].strip())
        clean = lambda value: value.replace("{", "").replace("}", "").strip()
        year = re.search(YEAR, fields.get("year") or fields.get("date", ""))
        doi = re.sub(r"^(?:doi:\s*|https?://(?:dx\.)?doi\.org/)", "", fields.get("doi", ""), flags=re.I)
        url = clean(fields.get("url", ""))
        if not doi:
            linked = re.fullmatch(r"https?://(?:dx\.)?doi\.org/(.+)", url, re.I)
            doi = linked[1] if linked else ""
        yield Reference(
            raw, [clean(a) for a in authors if clean(a)],
            int(year[0]) if year else None, clean(fields.get("title", "")),
            clean(next((fields[k] for k in ("journaltitle", "journal", "booktitle", "publisher",
                                           "institution", "school", "organization", "howpublished")
                        if fields.get(k)), "")),
            clean(fields.get("volume", "")), clean(fields.get("number", "")),
            clean(fields.get("pages", "")), clean(doi), url,
            clean(fields.get("urldate", "")), kind=kind,
            language=clean(fields.get("langid") or fields.get("language", "")),
            author_text=clean(author_text),
            doi_from_url=bool(doi and not fields.get("doi")),
        )


def parse(text, bibtex=False):
    text = text.lstrip("\ufeff").strip()
    bib_start = re.sub(r"^(?:%[^\n]*(?:\n|$)\s*)+", "", text)
    if bibtex or _BIB_ENTRY.match(bib_start):
        return list(_bib(text))
    entries = []
    pending = ""
    for line in text.splitlines():
        line = line.rstrip()
        if not line.strip():
            if pending:
                entries.append(pending)
                pending = ""
        elif pending and line[0].isspace() and not (NUMBER.match(line) or BULLET.match(line)):
            pending += " " + line.strip()
        else:
            if pending:
                entries.append(pending)
            pending = line.strip()
    if pending:
        entries.append(pending)
    return [_plain(entry) for entry in entries]
