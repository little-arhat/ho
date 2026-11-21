"""Reading texts: short stories built from the vocabulary learned so far.

A text is `content/reading/<id>.toml`, plus `<id>.jpg`, its illustration,
once `illustrate` has drawn it (a text without one still ships).
Each text tells one scene twice: as a story (`[[prose]]` paragraphs) and as
a conversation (`[[dialog]]` lines, each with its `speaker`).
Japanese is written pre-segmented: tokens joined by "|", each in furigana
notation. A token links to a word so the reader can tap it:

    私[わたし]|は|デパート|へ|行[い]きました=行[い]きます|。

`surface=word` names the dictionary form when the surface is inflected.
Every token with kanji or katakana must be a vocabulary word of the text's
lesson or an earlier one, or a word the text declares under [[new]]. Tokens
written only in hiragana (particles, endings) need not link; if one matches
a word, it links anyway. A speaker is one token and must be a word.

A text's `lessons` are the ones it draws from: its own, and every lesson
whose words it uses.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ho import furigana
from ho.errors import ContentError
from ho.fields import LANGS, Text, by_lang, check_keys, japanese, translations
from ho.kanji import kanji_in
from ho.lessons import Lesson, word_key

_ID = re.compile(r"\d\d-[a-z0-9-]+")
_NEEDS_LINK = re.compile(f"[{furigana.KANJI}ァ-ヺー]")


@dataclass(frozen=True)
class Word:
    ja: str
    tr: Text
    lesson: int | None  # None: new in this text


@dataclass(frozen=True)
class Token:
    ja: str
    word: int | None  # index into Reading.words


@dataclass(frozen=True)
class Paragraph:
    tokens: tuple[Token, ...]
    tr: Text

    @property
    def ja(self) -> str:
        return "".join(t.ja for t in self.tokens)


@dataclass(frozen=True)
class Line:
    speaker: Token
    tokens: tuple[Token, ...]
    tr: Text

    @property
    def ja(self) -> str:
        return "".join(t.ja for t in self.tokens)


@dataclass(frozen=True)
class Reading:
    id: str
    lesson: int
    lessons: tuple[int, ...]  # the lessons it draws from, ascending; includes `lesson`
    title: Text
    scene: str  # the illustration's prompt, kept so it can be redrawn
    prose: tuple[Paragraph, ...]
    dialog: tuple[Line, ...]
    words: tuple[Word, ...]
    image: Path | None  # the illustration, once it has been drawn


def _vocabulary(lessons: tuple[Lesson, ...], upto: int) -> dict[str, Word]:
    out: dict[str, Word] = {}
    for lesson in lessons:
        if lesson.number > upto:
            continue
        for w in lesson.vocab:
            out.setdefault(word_key(w.furigana), Word(w.furigana, w.tr, lesson.number))
    return out


def _new_words(rows: list[dict[str, Any]], where: str) -> dict[str, Word]:
    out = {}
    for i, row in enumerate(rows):
        w = f"{where} new #{i + 1}"
        check_keys(row, {"ja", *LANGS}, set(), w)
        out[word_key(japanese(row["ja"], w))] = Word(row["ja"], translations({k: row[k] for k in LANGS}, w), None)
    return out


class _Linker:
    """Resolves tokens to words, collecting the words in order of first use."""

    def __init__(self, lookup: dict[str, Word], lesson: int):
        self.lookup = lookup
        self.lesson = lesson
        self.index: dict[str, int] = {}
        self.words: list[Word] = []

    def token(self, raw: str, where: str, *, must_link: bool = False) -> Token:
        surface, _, target = raw.partition("=")
        japanese(surface, where)
        key = word_key(japanese(target, where) if target else surface)
        word = self.lookup.get(key)
        if word is None and (must_link or target or _NEEDS_LINK.search(furigana.plain(surface))):
            raise ContentError(f"{where}: {key!r} is not a word of lessons 1–{self.lesson}; declare it under [[new]]")
        if word is None:
            return Token(surface, None)
        if key not in self.index:
            self.index[key] = len(self.words)
            self.words.append(word)
        return Token(surface, self.index[key])

    def tokens(self, ja: str, where: str) -> tuple[Token, ...]:
        return tuple(self.token(raw, where) for raw in ja.split("|"))


def _rows(data: dict[str, Any], key: str, where: str) -> list[dict[str, Any]]:
    rows = data[key]
    if not isinstance(rows, list) or not rows:
        raise ContentError(f"{where}: [[{key}]] needs at least one entry")
    return rows


def load_reading(path: Path, lessons: tuple[Lesson, ...]) -> Reading:
    where = str(path)
    if not _ID.fullmatch(path.stem):
        raise ContentError(f"{where}: name must be NN-words.toml, NN the lesson")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    check_keys(data, {"lesson", "title", "scene", "prose", "dialog"}, {"new"}, where)
    lesson = data["lesson"]
    if f"{lesson:02d}" != path.stem[:2] or lesson not in {x.number for x in lessons}:
        raise ContentError(f"{where}: lesson {lesson} must exist and match the file name")
    known = _vocabulary(lessons, lesson)
    new = _new_words(data.get("new", []), where)
    clash = sorted(set(new) & set(known))
    if clash:
        raise ContentError(f"{where}: declared new but already in the vocabulary: {', '.join(clash)}")
    link = _Linker({**known, **new}, lesson)
    prose = []
    for i, row in enumerate(_rows(data, "prose", where)):
        w = f"{where} prose #{i + 1}"
        check_keys(row, {"ja", *LANGS}, set(), w)
        prose.append(Paragraph(link.tokens(row["ja"], w), translations({k: row[k] for k in LANGS}, w)))
    dialog = []
    for i, row in enumerate(_rows(data, "dialog", where)):
        w = f"{where} dialog #{i + 1}"
        check_keys(row, {"speaker", "ja", *LANGS}, set(), w)
        dialog.append(Line(link.token(row["speaker"], w, must_link=True), link.tokens(row["ja"], w),
                           translations({k: row[k] for k in LANGS}, w)))
    unused = sorted(set(new) - set(link.index))
    if unused:
        raise ContentError(f"{where}: new words never used: {', '.join(unused)}")
    drawn = {lesson} | {w.lesson for w in link.words if w.lesson is not None}
    image = path.with_suffix(".jpg")
    return Reading(path.stem, lesson, tuple(sorted(drawn)), translations(data["title"], f"{where} title"),
                   data["scene"].strip(), tuple(prose), tuple(dialog), tuple(link.words),
                   image if image.exists() else None)


def load_readings(directory: Path, lessons: tuple[Lesson, ...]) -> tuple[Reading, ...]:
    return tuple(load_reading(p, lessons) for p in sorted(directory.glob("*.toml")))


def words_view(r: Reading, cards: set[str], slug: Callable[[str], str]) -> list[dict[str, Any]]:
    """The tappable words; `k` lists the word's kanji that have a card, `slug` names its word page."""
    return [{"ja": furigana.segments_json(w.ja), **by_lang(w.tr), "slug": slug(w.ja),
             "lesson": w.lesson, "k": [c for c in dict.fromkeys(kanji_in(w.ja)) if c in cards]}
            for w in r.words]
