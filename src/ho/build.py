"""Build the static site: load content, render pages, write the output tree."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from ho import kanji, katakana, lessons, phrasebook, refdata
from ho.errors import ContentError
from ho.site import Content, render_site
from ho.verbs import load_verbs

ROOT = Path(__file__).resolve().parents[2]
MARKER = ".nojekyll"


def load_content(content_dir: Path, ref_path: Path) -> Content:
    verbs = load_verbs(content_dir / "verbs.toml")
    lesson_list = lessons.load_lessons(content_dir / "lessons")
    cards = kanji.load_cards(content_dir / "kanji")
    ref = refdata.load(ref_path)
    book = [c.char for c in cards if c.number is not None]
    kanji.check(cards, ref, book + kanji.lesson_kanji(lesson_list))
    return Content(
        lessons=lesson_list,
        phrasebook=phrasebook.load(content_dir / "phrasebook.toml", verbs),
        katakana=katakana.load(content_dir / "katakana.toml"),
        kanji=cards,
        strokes={c.char: ref[c.char].strokes for c in cards},
    )


def _clear(out: Path) -> None:
    if not out.exists():
        return
    if any(out.iterdir()) and not (out / MARKER).exists():
        raise SystemExit(f"{out} is not empty and is not a previous build; refusing to delete it")
    shutil.rmtree(out)


def write_site(pages: dict[str, str], out: Path) -> None:
    _clear(out)
    shutil.copytree(ROOT / "web", out / "static", ignore=shutil.ignore_patterns(".*"))
    for rel, html in pages.items():
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
    (out / MARKER).write_text("")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the ho static site.")
    parser.add_argument("--out", type=Path, default=ROOT / "_site")
    args = parser.parse_args(argv)
    try:
        content = load_content(ROOT / "content", ROOT / "ref" / "kanji.json")
    except ContentError as e:
        print(f"content error: {e}", file=sys.stderr)
        return 1
    write_site(render_site(content, ROOT / "templates"), args.out)
    print(f"built {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
