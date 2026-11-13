"""Reading texts: short stories built from the vocabulary learned so far.

A text is `content/reading/<id>.toml`, plus `<id>.jpg`, its illustration,
once `illustrate` has drawn it (a text without one still ships).
Paragraphs are written pre-segmented: tokens joined by "|", each in furigana
notation. A token links to a word so the reader can tap it:

    私[わたし]|は|デパート|へ|行[い]きました=行[い]きます|。

`surface=word` names the dictionary form when the surface is inflected.
Every token with kanji or katakana must be a vocabulary word of the text's
lesson or an earlier one, or a word the text declares under [[new]]. Tokens
written only in hiragana (particles, endings) need not link; if one matches
a word, it links anyway.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ho import furigana
from ho.errors import ContentError
from ho.fields import LANGS, Text, check_keys, japanese, translations
from ho.lessons import Lesson

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
    word: int | None  # index into Text.words


@dataclass(frozen=True)
class Paragraph:
    tokens: tuple[Token, ...]
    tr: Text


@dataclass(frozen=True)
class Reading:
    id: str
    lesson: int
    title: Text
    scene: str  # the illustration's prompt, kept so it can be redrawn
    paragraphs: tuple[Paragraph, ...]
    words: tuple[Word, ...]
    image: Path | None  # the illustration, once it has been drawn


def _key(ja: str) -> str:
    """Words match on their furigana with the reading, so 何[なに] ≠ 何[なん]."""
    return ja.replace("～", "").strip()


def _vocabulary(lessons: tuple[Lesson, ...], upto: int) -> dict[str, Word]:
    out: dict[str, Word] = {}
    for lesson in lessons:
        if lesson.number > upto:
            continue
        for w in lesson.vocab:
            out.setdefault(_key(w.furigana), Word(w.furigana, w.tr, lesson.number))
    return out


def _new_words(rows: list[dict[str, Any]], where: str) -> dict[str, Word]:
    out = {}
    for i, row in enumerate(rows):
        w = f"{where} new #{i + 1}"
        check_keys(row, {"ja", *LANGS}, set(), w)
        out[_key(japanese(row["ja"], w))] = Word(row["ja"], translations({k: row[k] for k in LANGS}, w), None)
    return out


def load_reading(path: Path, lessons: tuple[Lesson, ...]) -> Reading:
    where = str(path)
    if not _ID.fullmatch(path.stem):
        raise ContentError(f"{where}: name must be NN-words.toml, NN the lesson")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    check_keys(data, {"lesson", "title", "scene", "paragraph"}, {"new"}, where)
    lesson = data["lesson"]
    if f"{lesson:02d}" != path.stem[:2] or lesson not in {x.number for x in lessons}:
        raise ContentError(f"{where}: lesson {lesson} must exist and match the file name")
    known = _vocabulary(lessons, lesson)
    new = _new_words(data.get("new", []), where)
    clash = sorted(set(new) & set(known))
    if clash:
        raise ContentError(f"{where}: declared new but already in the vocabulary: {', '.join(clash)}")
    lookup = {**known, **new}
    used: dict[str, int] = {}
    words: list[Word] = []
    paragraphs = []
    for i, row in enumerate(data["paragraph"]):
        w = f"{where} paragraph #{i + 1}"
        check_keys(row, {"ja", *LANGS}, set(), w)
        tokens = []
        for raw in row["ja"].split("|"):
            surface, _, target = raw.partition("=")
            japanese(surface, w)
            key = _key(japanese(target, w) if target else surface)
            word = lookup.get(key)
            if word is None and (target or _NEEDS_LINK.search(furigana.plain(surface))):
                raise ContentError(f"{w}: {key!r} is not a word of lessons 1–{lesson}; declare it under [[new]]")
            index = None
            if word is not None:
                index = used.setdefault(key, len(words))
                if index == len(words):
                    words.append(word)
            tokens.append(Token(surface, index))
        paragraphs.append(Paragraph(tuple(tokens), translations({k: row[k] for k in LANGS}, w)))
    unused = sorted(set(new) - set(used))
    if unused:
        raise ContentError(f"{where}: new words never used: {', '.join(unused)}")
    image = path.with_suffix(".jpg")
    return Reading(path.stem, lesson, translations(data["title"], f"{where} title"),
                   data["scene"].strip(), tuple(paragraphs), tuple(words),
                   image if image.exists() else None)


def load_readings(directory: Path, lessons: tuple[Lesson, ...]) -> tuple[Reading, ...]:
    return tuple(load_reading(p, lessons) for p in sorted(directory.glob("*.toml")))


def words_view(r: Reading) -> list[dict[str, Any]]:
    return [{"ja": furigana.segments_json(w.ja), "en": w.tr.en, "ru": w.tr.ru, "uk": w.tr.uk,
             "lesson": w.lesson} for w in r.words]
