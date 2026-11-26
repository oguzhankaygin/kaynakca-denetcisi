"""GitHub Pages için ortak kaynakları kopyalar."""

import json
from pathlib import Path
from shutil import copyfile


def build_site():
    package = Path(__file__).resolve().parent
    docs = package.parent / "docs"
    destination = docs / "py" / "kaynakca"
    destination.mkdir(parents=True, exist_ok=True)
    sources = sorted(package.glob("*.py"))
    names = {source.name for source in sources}
    for old_copy in destination.glob("*.py"):
        if old_copy.name not in names:
            old_copy.unlink()
    for source in sources:
        copyfile(source, destination / source.name)
    (destination.parent / "manifest.json").write_text(
        json.dumps([source.name for source in sources], indent=2) + "\n", encoding="utf-8"
    )
    for name in ("app.js", "style.css"):
        copyfile(package / "static" / name, docs / name)
