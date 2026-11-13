"""Import an Anki deck CSV (the ../ank format) as a lesson's vocabulary.

    uv run ank-import ANK.csv N TRANSLATIONS.tsv

ANK.csv has columns kanji,kana,furigana,translation,russian,context,audio,
example,example_translation,example_audio, with Anki furigana (the base is
the text after the preceding space: `お 茶[ちゃ]`). It becomes
content/lessons/NN.vocab.csv in ho's notation (the base is the kanji run).

Anki has no Ukrainian and no Russian for notes and examples, so
TRANSLATIONS.tsv supplies them: one line per CSV row, in order,
`uk<TAB>note_ru<TAB>note_uk<TAB>example_ru<TAB>example_uk`. A note_ru of
"-" drops that row's note (Anki notes about the scan, not the word).
Every conversion is checked to keep the same text and reading.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

from ho import furigana
from ho.errors import ContentError
from ho.lessons import VOCAB_COLUMNS, load_vocab

_ANKI = re.compile(r" ?([^ \[\]]+)\[([^\]]+)\]")
_KANJI_RUN = re.compile(f"[{furigana.KANJI}]+")
ANK_COLUMNS = ("kanji", "kana", "furigana", "translation", "russian", "context", "audio",
               "example", "example_translation", "example_audio")


def _squeeze(text: str) -> str:
    return text.replace(" ", "")


def convert(text: str) -> str:
    """Anki furigana (base = the word after a space) → ho furigana (base = the kanji run)."""
    def one(m: re.Match[str]) -> str:
        base, reading = m.groups()
        run = _KANJI_RUN.search(base)
        if not run or run.end() != len(base):
            raise ContentError(f"furigana base {base!r} does not end in kanji: {text!r}")
        return base[:run.start()] + run.group(0) + "[" + reading + "]"

    out = _ANKI.sub(one, text)
    same_text = _squeeze(furigana.plain(out)) == _squeeze(_ANKI.sub(r"\1", text))
    same_reading = _squeeze(furigana.reading(out)) == _squeeze(_ANKI.sub(r"\2", text))
    if not (same_text and same_reading):
        raise ContentError(f"conversion changed the text: {text!r} → {out!r}")
    return out


def _note(text: str) -> str:
    """Anki notes mark optional words with [ ]; in ho, brackets are furigana."""
    return text.replace("[", "(").replace("]", ")")


def rows(ank: list[dict[str, str]], extra: list[list[str]]) -> list[list[str]]:
    if len(extra) != len(ank):
        raise ContentError(f"{len(extra)} translation lines for {len(ank)} rows")
    out = []
    for i, (r, more) in enumerate(zip(ank, extra, strict=True)):
        uk, note_ru, note_uk, ex_ru, ex_uk = (more + [""] * 5)[:5]
        fg = convert(r["furigana"])
        if _squeeze(furigana.plain(fg)) != _squeeze(r["kanji"] or r["kana"]) \
                or _squeeze(furigana.reading(fg)) != _squeeze(r["kana"]):
            raise ContentError(f"row {i + 2}: furigana does not match kanji/kana")
        note = "" if note_ru == "-" else r["context"]
        notes = [_note(t) for t in (note, note_ru, note_uk)] if note else ["", "", ""]
        example = convert(r["example"]) if r["example"] else ""
        out.append([furigana.plain(fg) if r["kanji"] else "", furigana.reading(fg), fg,
                    r["translation"], r["russian"], uk, *notes,
                    example, r["example_translation"] if example else "",
                    ex_ru if example else "", ex_uk if example else ""])
    return out


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 3:
        print("usage: ank-import ANK.csv LESSON_NUMBER TRANSLATIONS.tsv", file=sys.stderr)
        return 2
    source, number, tsv = Path(args[0]), int(args[1]), Path(args[2])
    with source.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != ANK_COLUMNS:
            print(f"{source}: columns must be {','.join(ANK_COLUMNS)}", file=sys.stderr)
            return 1
        ank = list(reader)
    extra = [line.split("\t") for line in tsv.read_text(encoding="utf-8").splitlines()]
    out = Path(f"content/lessons/{number:02d}.vocab.csv")
    try:
        table = rows(ank, extra)
    except ContentError as e:
        print(f"{source}: {e}", file=sys.stderr)
        return 1
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(VOCAB_COLUMNS)
        w.writerows(table)
    load_vocab(out)  # the lesson loader's checks, before anyone builds
    print(f"{out}: {len(table)} words")
    return 0
