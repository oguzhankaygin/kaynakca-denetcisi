"""Komut satırı giriş noktası."""

import argparse
import sys
from pathlib import Path

from .report import build, render, to_json


def main(argv=None):
    parser = argparse.ArgumentParser(description="Kaynakça tutarlılık ve doğrulama denetçisi.")
    parser.add_argument("kaynakca", help="UTF-8 dosya yolu, standart girdi için - veya web")
    parser.add_argument("--metin", type=Path, help="Metin içi atıfları denetlenecek UTF-8 dosya")
    parser.add_argument("--crossref", action="store_true", help="DOI meta verisini çevrimiçi karşılaştır")
    formats = parser.add_mutually_exclusive_group()
    formats.add_argument("--json", action="store_true", help="JSON raporu")
    formats.add_argument("--md", action="store_true", help="Markdown raporu")
    args = parser.parse_args(argv)
    try:
        if args.kaynakca == "web":
            if args.metin or args.crossref or args.json or args.md:
                parser.error("web komutu ek seçenek almaz.")
            from .web import serve
            serve()
            return 0
        path = Path(args.kaynakca)
        text = sys.stdin.read() if args.kaynakca == "-" else path.read_text(encoding="utf-8-sig")
        document = args.metin.read_text(encoding="utf-8-sig") if args.metin else None
        report = build(text, bibtex=path.suffix.lower() == ".bib", document=document, online=args.crossref)
    except (OSError, ValueError) as error:
        print(f"Hata: {error}", file=sys.stderr)
        return 1
    print(to_json(report) if args.json else render(report, markdown=args.md))
    return int(report["summary"]["hata"] > 0)


if __name__ == "__main__":
    sys.exit(main())
