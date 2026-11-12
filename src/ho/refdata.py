"""Reference data for kanji, derived from KanjiVG and KANJIDIC2.

`uv run refdata KANJIVG_MAIN_ZIP KANJIDIC2_XML_GZ` writes ref/kanji.json:
for every jōyō kanji (KANJIDIC2 grades 1–8) and every other kanji that
appears anywhere under content/ (鞄, say), its on/kun readings and
English meanings (KANJIDIC2) and its stroke paths in order (KanjiVG).
The build reads only that file; it never downloads anything.

Third-party data, see ref/NOTICE: KanjiVG © Ulrich Apel, CC BY-SA 3.0;
KANJIDIC2 © EDRDG, CC BY-SA 4.0.
"""

from __future__ import annotations

import gzip
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

from ho.furigana import KANJI

KANJI_CHAR = re.compile(f"[{KANJI}]")
NOT_KANJI = set("々〆ヶ")  # in the furigana run class, but marks, not characters

SVG = "{http://www.w3.org/2000/svg}"


@dataclass(frozen=True)
class Kanji:
    on: tuple[str, ...]
    kun: tuple[str, ...]
    meanings: tuple[str, ...]
    strokes: tuple[str, ...]


def read_kanjidic(xml: bytes, also: set[str]) -> dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]]:
    """Jōyō kanji and those in `also` → (on, kun, English meanings)."""
    out = {}
    for ch in ET.fromstring(xml).iter("character"):
        grade = ch.findtext("misc/grade")
        literal = ch.findtext("literal") or ""
        if (grade is None or int(grade) > 8) and literal not in also:
            continue
        rm = ch.find("reading_meaning/rmgroup")
        if rm is None:
            continue
        on = tuple(r.text or "" for r in rm.findall("reading") if r.get("r_type") == "ja_on")
        kun = tuple(r.text or "" for r in rm.findall("reading") if r.get("r_type") == "ja_kun")
        meanings = tuple(m.text or "" for m in rm.findall("meaning") if m.get("m_lang") is None)
        out[literal] = (on, kun, meanings)
    return out


def stroke_paths(svg: bytes) -> tuple[str, ...]:
    """The stroke paths of a KanjiVG file, in stroke order."""
    root = ET.fromstring(svg)
    group = next(g for g in root.iter(f"{SVG}g") if (g.get("id") or "").startswith("kvg:StrokePaths_"))
    return tuple(p.get("d") or "" for p in group.iter(f"{SVG}path"))


def content_kanji(content: Path) -> set[str]:
    return {c for p in sorted(content.rglob("*")) if p.is_file()
            for c in KANJI_CHAR.findall(p.read_text(encoding="utf-8"))}


def build(kanjivg_zip: Path, kanjidic_gz: Path, also: set[str]) -> dict[str, Kanji]:
    dic = read_kanjidic(gzip.decompress(kanjidic_gz.read_bytes()), also)
    unknown = also - set(dic) - NOT_KANJI
    if unknown:
        raise SystemExit(f"not in KANJIDIC2: {''.join(sorted(unknown))}")
    out = {}
    with zipfile.ZipFile(kanjivg_zip) as z:
        for c, (on, kun, meanings) in sorted(dic.items()):
            name = f"kanji/{ord(c):05x}.svg"
            out[c] = Kanji(on, kun, meanings, stroke_paths(z.read(name)))
    return out


def dump(ref: dict[str, Kanji]) -> str:
    """One kanji per line, sorted by code point, so diffs stay readable."""
    lines = [f"{json.dumps(c, ensure_ascii=False)}: "
             + json.dumps({"on": k.on, "kun": k.kun, "meanings": k.meanings, "strokes": k.strokes},
                          ensure_ascii=False, separators=(",", ":"))
             for c, k in ref.items()]
    return "{\n" + ",\n".join(lines) + "\n}\n"


def load(path: Path) -> dict[str, Kanji]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {c: Kanji(tuple(v["on"]), tuple(v["kun"]), tuple(v["meanings"]), tuple(v["strokes"]))
            for c, v in raw.items()}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: refdata KANJIVG_MAIN_ZIP KANJIDIC2_XML_GZ", file=sys.stderr)
        return 2
    ref = build(Path(args[0]), Path(args[1]), content_kanji(Path("content")))
    out = Path("ref/kanji.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(dump(ref), encoding="utf-8")
    print(f"{len(ref)} kanji → {out}")
    return 0
