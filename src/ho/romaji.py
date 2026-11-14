"""Romaji for reading along: word-spaced Hepburn of our own furigana reading.

MeCab (fugashi + unidic-lite) only finds word boundaries and particles; the
sounds always come from the text's furigana, so a dictionary misreading can
never reach the page. Particles are written as spoken (は wa, へ e, を o);
auxiliaries, suffixes and the conjunctive て・で・ば join the word
before them (飲みませんか → nomimasen ka, 行って → itte).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import cache

import fugashi

from ho import furigana
from ho.kana import kata_to_hira, romaji

_HEARD = {("は", "わ"), ("へ", "え")}  # spelt / said: the topic and direction particles, こんにちは
_LONG_MARK = set("あいうえお")  # MeCab writes a long vowel as ー where we write the vowel
_PUNCT = {"。": ".", "、": ",", "？": "?", "！": "!", "…": "…", "・": "/", "～": "~", "「": "\"", "」": "\"", "（": "(", "）": ")"}
_PUNCT_POS = {"補助記号", "空白"}
_KANJI = re.compile(f"[{furigana.KANJI}]")
_CONJUNCTIVE = {"て", "で", "ば"}  # itte, yonde, ikeba; but が/けど/のに stay separate


@dataclass(frozen=True)
class _Unit:
    """A stretch of plain text that must be read as one: a ruby run, or one character."""
    start: int
    end: int
    kana: str


@cache
def _tagger() -> fugashi.Tagger:
    return fugashi.Tagger()


def _units(text: str) -> tuple[str, tuple[_Unit, ...]]:
    plain, units, pos = [], [], 0
    for seg in furigana.parse(text):
        if seg.ruby is not None:
            units.append(_Unit(pos, pos + len(seg.text), seg.ruby))
        else:
            units.extend(_Unit(pos + i, pos + i + 1, c) for i, c in enumerate(seg.text))
        plain.append(seg.text)
        pos += len(seg.text)
    return "".join(plain), tuple(units)


@dataclass
class _Word:
    start: int
    end: int
    function: bool  # a particle or です-like auxiliary: it ends the phrase it follows
    pron: str = ""  # MeCab's pronunciation of the word, in hiragana ("" if unknown)
    before: str = ""
    after: str = ""


def _foreign(c: str) -> bool:
    """Neither kana nor kanji: Latin, digits, 〇 placeholders. Runs of these stay one word."""
    return not (_KANJI.fullmatch(c) or "\u3041" <= c <= "\u30ff")


def _joins_previous(tok: fugashi.UnidicNode, prev: fugashi.UnidicNode) -> bool:
    f = tok.feature
    if prev.feature.pos1 == "接頭辞":
        return True
    if f.pos1 == "助動詞":
        return f.lemma not in ("です", "だ")  # the copula stands alone: gakusei desu
    if f.pos1 == "接尾辞" or (f.pos2 == "接続助詞" and tok.surface in _CONJUNCTIVE):
        return True
    if f.pos1 == "形容詞" and f.lemma == "無い" and prev.feature.pos1 in ("形容詞", "動詞", "助動詞"):  # takaku nai → takakunai
        return True
    return _foreign(prev.surface[-1]) and _foreign(tok.surface[0])


@dataclass(frozen=True)
class _Token:
    start: int
    end: int
    node: fugashi.UnidicNode


def _tokens(plain: str) -> tuple[_Token, ...]:
    out, pos = [], 0
    for node in _tagger()(plain):
        start = plain.index(node.surface, pos)
        pos = start + len(node.surface)
        out.append(_Token(start, pos, node))
    return tuple(out)


def _split_runs(units: tuple[_Unit, ...], tokens: tuple[_Token, ...]) -> tuple[_Unit, ...]:
    """Cut a ruby run where MeCab sees a word break inside it (一番好[いちばんす]き),
    but only when MeCab's reading of the first part is exactly the start of ours."""
    out = []
    for u in units:
        rest = u
        for t in tokens:
            if not rest.start < t.start < rest.end:
                continue
            head = [x for x in tokens if rest.start <= x.start and x.end <= t.start]
            if not head or head[0].start != rest.start:
                continue
            kana = kata_to_hira("".join(x.node.feature.kana or "\0" for x in head))
            if rest.kana.startswith(kana) and len(kana) < len(rest.kana):
                out.append(_Unit(rest.start, t.start, kana))
                rest = _Unit(t.start, rest.end, rest.kana[len(kana):])
        out.append(rest)
    return tuple(out)


def _words(text: str) -> tuple[str, tuple[_Unit, ...], list[_Word]]:
    """The line cut into words, with the punctuation that opens or closes each."""
    plain, units = _units(text)
    tokens = _tokens(plain)
    units = _split_runs(units, tokens)
    boundaries = {u.start for u in units}
    words: list[_Word] = []
    opening = ""
    prev = None
    for t in tokens:
        f = t.node.feature
        if f.pos1 in _PUNCT_POS and all(c in _PUNCT or c.isspace() for c in t.node.surface):
            marks = t.node.surface.strip()
            if f.pos2 == "括弧開" or not words:
                opening += marks
            else:
                words[-1].after += marks
            prev = None
            continue
        last = words[-1] if words else None
        pron = kata_to_hira(f.pron or "") if f.pron and f.pron != "*" else ""
        if last and last.end == t.start and not last.after and (
                t.start not in boundaries or (prev is not None and _joins_previous(t.node, prev))):
            last.end = t.end
            last.pron = last.pron + pron if last.pron and pron else ""
        else:
            words.append(_Word(t.start, t.end, f.pos1 in ("助詞", "助動詞"), pron, before=opening))
            opening = ""
        prev = t.node
    return plain, units, words


def _spoken(kana: str, pron: str) -> str:
    """Our kana with は/へ turned into わ/え where MeCab hears them so (先生は, こんにちは),
    trusted only when its pronunciation otherwise says exactly our kana."""
    if len(kana) != len(pron):
        return kana
    out = []
    for ours, heard in zip(kana, pron, strict=True):
        o = kata_to_hira(ours)
        if (o, heard) in _HEARD:
            out.append(heard)
        elif o == heard or (heard == "ー" and o in _LONG_MARK) or (o == "を" and heard == "お"):
            out.append(ours)
        else:
            return kana
    return "".join(out)


def _kana(units: tuple[_Unit, ...], w: _Word) -> str:
    """The word as it is said, in our kana (katakana words stay katakana)."""
    return _spoken("".join(u.kana for u in units if w.start <= u.start < w.end), w.pron)


def _marks(text: str) -> str:
    return "".join(_PUNCT.get(c, "") for c in text)


def romanize(text: str) -> str:
    """Display romaji for a furigana-annotated line: 私[わたし]は学[がく]生[せい]です。 → watashi wa gakusei desu."""
    plain, units, words = _words(text)
    out = []
    for w in words:
        sound = romaji(_kana(units, w))
        out.append(_marks(w.before) + unicodedata.normalize("NFKC", sound) + _marks(w.after))
    return " ".join(out)


def speech(text: str) -> str:
    """What the browser's Japanese voice is given: our own reading in kana, so it
    never has to guess a kanji, in phrases (a word with its particles, as
    children's books space them) with は and へ spelt as spoken (わ, え).
    私[わたし]は学[がく]生[せい]です。 → わたしわ がくせいです。"""
    plain, units, words = _words(text)
    phrases: list[str] = []
    for w in words:
        sound = _kana(units, w)
        piece = w.before + sound + w.after
        if phrases and w.function and not w.before:
            phrases[-1] += piece
        else:
            phrases.append(piece)
    return " ".join(phrases)
