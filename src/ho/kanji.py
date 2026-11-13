"""Kanji cards, checked against KANJIDIC2 and KanjiVG, and the kanji drill.

Cards live in `content/kanji/*.toml`. `book.toml` holds the 15-minute kanji
book's cards (with its number and JLPT level); other files hold our own
cards for kanji the lessons use. Readings are written as the book prints
them: hiragana = kun, katakana = on, "-" splits off okurigana (う-まれます),
"(…)" marks a secondary reading and a trailing "*" a special one that
lives only in set words (なん in 何歳). Every reading that is not special
must be one KANJIDIC2 knows; stroke order always comes from KanjiVG.
"""

from __future__ import annotations

import re
import tomllib
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ho import furigana
from ho.errors import ContentError
from ho.kana import kata_to_hira, romaji
from ho.fields import Line, Text, check_keys, japanese, line, translations
from ho.lessons import Lesson
from ho.refdata import KANJI_CHAR, NOT_KANJI, Kanji

_HIRAGANA = re.compile(r"[ぁ-ゖ]+(-[ぁ-ゖ]+)?")
_KATAKANA = re.compile(r"[ァ-ヺー]+")


@dataclass(frozen=True)
class Reading:
    kana: str  # as printed, okurigana after "-"
    on: bool
    secondary: bool
    special: bool


@dataclass(frozen=True)
class CardWord:
    ja: str
    tr: Text
    example: Line


@dataclass(frozen=True)
class Card:
    char: str
    number: int | None  # position in the 15-minute book
    level: int | None  # JLPT level the book prints
    readings: tuple[Reading, ...]
    meaning: Text
    words: tuple[CardWord, ...]


def kanji_in(text: str) -> list[str]:
    """The kanji characters of a text, in order, iteration marks excluded."""
    return [c for c in KANJI_CHAR.findall(furigana.plain(text)) if c not in NOT_KANJI]


def parse_reading(text: str, where: str) -> Reading:
    secondary = text.startswith("(") and text.endswith(")")
    core = text[1:-1] if secondary else text
    special = core.endswith("*")
    core = core.removesuffix("*")
    if _KATAKANA.fullmatch(core):
        return Reading(core, True, secondary, special)
    if _HIRAGANA.fullmatch(core):
        return Reading(core, False, secondary, special)
    raise ContentError(f"{where}: reading {text!r} must be hiragana (kun, okurigana after -) or katakana (on)")


def _word(row: dict[str, Any], char: str, where: str) -> CardWord:
    check_keys(row, {"ja", "tr", "example"}, set(), where)
    word = CardWord(japanese(row["ja"], where), translations(row["tr"], f"{where} tr"),
                    line(row["example"], f"{where} example"))
    if char not in furigana.plain(word.ja) or char not in furigana.plain(word.example.ja):
        raise ContentError(f"{where}: both the word and its example must contain {char}")
    return word


def _card(row: dict[str, Any], where: str) -> Card:
    check_keys(row, {"char", "readings", "meaning"}, {"number", "level", "word"}, where)
    char = row["char"]
    if kanji_in(char) != [char]:
        raise ContentError(f"{where}: char must be a single kanji, got {char!r}")
    where = f"{where} ({char})"
    if ("number" in row) != ("level" in row):
        raise ContentError(f"{where}: number and level come together (book cards) or not at all")
    if not row["readings"]:
        raise ContentError(f"{where}: no readings")
    return Card(
        char=char,
        number=row.get("number"),
        level=row.get("level"),
        readings=tuple(parse_reading(r, where) for r in row["readings"]),
        meaning=translations(row["meaning"], f"{where} meaning"),
        words=tuple(_word(w, char, f"{where} word #{i + 1}") for i, w in enumerate(row.get("word", ()))),
    )


def load_file(path: Path) -> tuple[Card, ...]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    check_keys(data, {"kanji"}, set(), str(path))
    return tuple(_card(row, f"{path} kanji #{i + 1}") for i, row in enumerate(data["kanji"]))


def load_cards(directory: Path) -> tuple[Card, ...]:
    """All cards: the book's in its order, then ours in file order."""
    cards = [c for p in sorted(directory.glob("*.toml")) for c in load_file(p)]
    seen: set[str] = set()
    for c in cards:
        if c.char in seen:
            raise ContentError(f"{directory}: two cards for {c.char}")
        seen.add(c.char)
    numbers = [c.number for c in cards if c.number is not None]
    if len(set(numbers)) != len(numbers):
        raise ContentError(f"{directory}: a book number is used twice")
    return tuple(sorted(cards, key=lambda c: (c.number is None, c.number or 0)))


def _kun_stems(k: Kanji) -> set[str]:
    return {r.strip("-").split(".")[0] for r in k.kun}


def check(cards: Iterable[Card], ref: dict[str, Kanji], required: Iterable[str]) -> None:
    """Every card is a kanji KanjiVG and KANJIDIC2 know, every ordinary reading
    is one KANJIDIC2 lists, and every required kanji has a card."""
    have = set()
    for card in cards:
        have.add(card.char)
        k = ref.get(card.char)
        if k is None:
            raise ContentError(f"kanji card {card.char}: not in ref/kanji.json (run refdata)")
        for r in card.readings:
            if r.special:
                continue
            stem = r.kana.split("-")[0]
            if not (stem in k.on if r.on else stem in _kun_stems(k)):
                raise ContentError(f"kanji card {card.char}: reading {r.kana} is not in KANJIDIC2 "
                                   f"(on {list(k.on)}, kun {list(k.kun)}); mark it * if it is special")
    missing = sorted(set(required) - have, key=ord)
    if missing:
        raise ContentError(f"no kanji card for {''.join(missing)}")


def lesson_kanji(lessons: Iterable[Lesson]) -> list[str]:
    """Kanji that lesson vocabulary uses, first appearance first."""
    out: dict[str, None] = {}
    for lesson in lessons:
        for w in lesson.vocab:
            out.update(dict.fromkeys(kanji_in(w.kanji)))
    return list(out)


@dataclass(frozen=True)
class LessonWord:
    """A lesson vocabulary word, as a kanji card lists it."""
    lesson: int
    furigana: str
    tr: Text


def lesson_words(lessons: Iterable[Lesson]) -> dict[str, tuple[LessonWord, ...]]:
    """Kanji → the lesson words that use it, in lesson order."""
    out: dict[str, list[LessonWord]] = {}
    for lesson in lessons:
        for w in lesson.vocab:
            for c in dict.fromkeys(kanji_in(w.kanji)):
                out.setdefault(c, []).append(LessonWord(lesson.number, w.furigana, w.tr))
    return {c: tuple(ws) for c, ws in out.items()}


def stroke_frames(strokes: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    """The book's stroke-order boxes: box i draws strokes 1..i."""
    return tuple(strokes[:i] for i in range(1, len(strokes) + 1))


@dataclass(frozen=True)
class DrillItem:
    ja: str  # furigana notation
    written: str
    reading: str
    tr: Text
    source: str  # "book", or the lesson number


def drill_items(cards: Iterable[Card], lessons: Iterable[Lesson]) -> tuple[DrillItem, ...]:
    """Every word with kanji that the site teaches, once per spelling+reading."""
    out: dict[tuple[str, str], DrillItem] = {}
    for card in cards:
        if card.number is None:
            continue
        for w in card.words:
            item = DrillItem(w.ja, furigana.plain(w.ja), furigana.reading(w.ja), w.tr, "book")
            out.setdefault((item.written, item.reading), item)
    for lesson in lessons:
        for w in lesson.vocab:
            if kanji_in(w.kanji):
                item = DrillItem(w.furigana, furigana.plain(w.furigana), furigana.reading(w.furigana),
                                 w.tr, str(lesson.number))
                out.setdefault((item.written, item.reading), item)
    return tuple(out.values())


def _closeness(a: DrillItem, b: DrillItem, field: str) -> int:
    shared = len(set(kanji_in(a.written)) & set(kanji_in(b.written)))
    x, y = getattr(a, field), getattr(b, field)
    return 2 * shared + (len(x) == len(y)) + (x[:1] == y[:1])


def distractors(items: tuple[DrillItem, ...], i: int, field: str, n: int = 8) -> list[int]:
    """The n items most easily confused with item i on `field` ("reading" or
    "written"). An item sharing either the spelling or the reading is never a
    wrong answer: 何 is both なに and なん, and homophones are not mistakes."""
    a = items[i]
    pool = [j for j, b in enumerate(items)
            if b.written != a.written and b.reading != a.reading and getattr(b, field) != getattr(a, field)]
    out: dict[str, int] = {}  # one item per shown value: two buttons never read the same
    for j in sorted(pool, key=lambda j: (-_closeness(a, items[j], field), j)):
        out.setdefault(getattr(items[j], field), j)
    return list(out.values())[:n]


def fold(text: str) -> str:
    """How typed answers compare: width, case, ё/е, katakana/hiragana and every
    space or punctuation mark folded away. web/js/kanji-drill.js folds input
    the same way (tests pin both to the same cases)."""
    t = kata_to_hira(unicodedata.normalize("NFKC", text).lower().replace("ё", "е"))
    return re.sub(r"[\W_]+", "", t)


_PARENS = re.compile(r"\([^)]*\)")
_LEADING = re.compile(r"^(?:to|a|an|the) ", re.IGNORECASE)


def meaning_answers(meaning: Text) -> tuple[str, ...]:
    """Typed meanings accepted for a gloss, in any of the three languages:
    each part between , ; / on its own, with or without its (…) remark, and
    without a leading "to" / article ("to eat" → eat)."""
    out: dict[str, None] = {}
    for gloss in (meaning.en, meaning.ru, meaning.uk):
        for part in re.split(r"[,;/]", _PARENS.sub(lambda m: m.group(0).replace(",", " "), gloss)):
            for variant in (part, _PARENS.sub("", part)):
                variant = variant.strip()
                for v in (variant, _LEADING.sub("", variant)):
                    if fold(v):
                        out[fold(v)] = None
    return tuple(out)


def reading_answers(reading: str) -> tuple[str, ...]:
    """A reading typed in kana, or in Hepburn romaji (an apostrophe after n is optional)."""
    ro = romaji(reading)
    return tuple(dict.fromkeys(fold(x) for x in (reading, ro, ro.replace("ō", "ou").replace("ū", "uu"))))


def kanji_sets(cards: Iterable[Card], lessons: Iterable[Lesson]) -> dict[str, list[str]]:
    """Named subsets for the drill: the book's kanji in its order, and each lesson's vocabulary kanji."""
    sets = {"book": [c.char for c in cards if c.number is not None]}
    for lesson in lessons:
        sets[str(lesson.number)] = list(dict.fromkeys(c for w in lesson.vocab for c in kanji_in(w.kanji)))
    return sets


def drill_view(cards: tuple[Card, ...], lessons: tuple[Lesson, ...]) -> dict[str, Any]:
    items = drill_items(cards, lessons)
    return {
        "words": [
            {"ja": furigana.segments_json(it.ja), "w": it.written, "r": it.reading, "k": kanji_in(it.written),
             "en": it.tr.en, "ru": it.tr.ru, "uk": it.tr.uk, "src": it.source,
             "am": meaning_answers(it.tr), "ar": reading_answers(it.reading),
             "dr": distractors(items, i, "reading"), "dw": distractors(items, i, "written")}
            for i, it in enumerate(items)],
        "kanji": [
            {"c": c.char, "no": c.number, "rd": [r.kana for r in c.readings if not r.secondary][:3],
             "en": c.meaning.en, "ru": c.meaning.ru, "uk": c.meaning.uk, "am": meaning_answers(c.meaning)}
            for c in cards],
        "sets": kanji_sets(cards, lessons),
    }
