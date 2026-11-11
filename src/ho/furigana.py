"""Furigana notation: `漢字[かんじ]`.

The ruby base is the run of kanji directly before `[`, so kana around it
needs no separator: `お願[ねが]いします` puts ねが over 願 alone. Readings are
kana only. Anything else in brackets is a mistake in the content, and parsing
refuses it rather than rendering a wrong reading.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ho.errors import ContentError

KANJI = "㐀-鿿豈-﫿々〆ヶ"
_RUBY = re.compile(rf"([{KANJI}]+)\[([^\[\]]*)\]")
_KANA = re.compile(r"[ぁ-ゖァ-ヺー]+")


@dataclass(frozen=True)
class Segment:
    text: str
    ruby: str | None


def parse(text: str) -> tuple[Segment, ...]:
    out: list[Segment] = []
    pos = 0
    for m in _RUBY.finditer(text):
        _plain(text, text[pos : m.start()], out)
        base, ruby = m.groups()
        if not _KANA.fullmatch(ruby):
            raise ContentError(f"reading {ruby!r} for {base!r} is not kana in {text!r}")
        out.append(Segment(base, ruby))
        pos = m.end()
    _plain(text, text[pos:], out)
    return tuple(out)


def _plain(whole: str, chunk: str, out: list[Segment]) -> None:
    if not chunk:
        return
    if "[" in chunk or "]" in chunk:
        raise ContentError(f"bracket without a kanji base in {whole!r}")
    out.append(Segment(chunk, None))


def plain(text: str) -> str:
    return "".join(s.text for s in parse(text))


def reading(text: str) -> str:
    return "".join(s.ruby or s.text for s in parse(text))


def segments_json(text: str) -> list[list[str]]:
    return [[s.text] if s.ruby is None else [s.text, s.ruby] for s in parse(text)]
