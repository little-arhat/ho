"""Every word on the site in one list: lesson vocabulary, the book's topic
lists (content/words/<id>.toml + <id>.csv), and the words that kanji cards and
reading texts bring. A topic list is kept whole; the words kanji cards and
reading texts bring are listed only if no earlier group has them."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ho import furigana
from ho.errors import ContentError
from ho.fields import Line, Text, check_keys, translations
from ho.kanji import Card, search_tokens, word_search_tokens
from ho.lessons import Lesson, load_vocab, word_key
from ho.lessons import Word as VocabWord
from ho.reading import Reading
from ho.romaji import romanize


@dataclass(frozen=True)
class Topic:
    id: str
    title: Text
    lesson: int  # the lesson the book prints the list with
    words: tuple[VocabWord, ...]


def load_topic(path: Path, lessons: Iterable[int]) -> Topic:
    where = str(path)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    check_keys(data, {"title", "lesson"}, set(), where)
    if data["lesson"] not in set(lessons):
        raise ContentError(f"{where}: lesson {data['lesson']} does not exist")
    csv = path.with_suffix(".csv")
    if not csv.exists():
        raise ContentError(f"{where}: its words go in {csv.name}, which is missing")
    return Topic(path.stem, translations(data["title"], f"{where} title"), data["lesson"], load_vocab(csv))


def load_topics(directory: Path, lessons: Iterable[int]) -> tuple[Topic, ...]:
    numbers = set(lessons)
    orphans = sorted(p.name for p in directory.glob("*.csv") if not p.with_suffix(".toml").exists())
    if orphans:
        raise ContentError(f"{directory}: word lists without a .toml (title, lesson): {', '.join(orphans)}")
    return tuple(load_topic(p, numbers) for p in sorted(directory.glob("*.toml")))


@dataclass(frozen=True)
class Entry:
    ja: str  # furigana notation
    tr: Text
    note: Text | None
    example: Line | None


class Kind(Enum):
    LESSON = "lesson"  # a lesson's vocabulary
    TOPIC = "topic"  # a reference list the book prints with a lesson
    ELSEWHERE = "elsewhere"  # words kanji cards or reading texts bring


@dataclass(frozen=True)
class Group:
    id: str  # the filter key: l6, a topic id, cards, reading
    kind: Kind
    lesson: int | None  # the lesson of a LESSON or TOPIC group
    label: str  # the filter button
    kicker: str  # what the group is, before its title
    title: Text
    entries: tuple[Entry, ...]


CARDS_TITLE = Text("Words on kanji cards", "Слова с карточек кандзи", "Слова з карток кандзі",
                   "Palabras de las tarjetas de kanji")
READING_TITLE = Text("New words in reading texts", "Новые слова из текстов для чтения", "Нові слова з текстів для читання",
                     "Palabras nuevas de los textos de lectura")
SCENES_TITLE = Text("Words in scenes", "Слова из сценок", "Слова зі сценок", "Palabras de las escenas")


def _vocab(words: Iterable[VocabWord]) -> tuple[Entry, ...]:
    return tuple(Entry(w.furigana, w.tr, w.note, w.example) for w in words)


def groups(lessons: Iterable[Lesson], topics: Iterable[Topic], cards: Iterable[Card],
           readings: Iterable[Reading]) -> tuple[Group, ...]:
    """Lessons in order, each followed by the topic lists printed with it,
    then card words and reading words not in any of those."""
    out: list[Group] = []
    by_lesson: dict[int, list[Topic]] = {}
    for t in topics:
        by_lesson.setdefault(t.lesson, []).append(t)
    for lesson in lessons:
        out.append(Group(f"l{lesson.number}", Kind.LESSON, lesson.number, f"L{lesson.number}",
                         f"Lesson {lesson.number}", lesson.title, _vocab(lesson.vocab)))
        for t in by_lesson.get(lesson.number, []):
            out.append(Group(t.id, Kind.TOPIC, t.lesson, t.title.en.upper(),
                             f"Reference words · lesson {t.lesson}", t.title, _vocab(t.words)))
    seen = {word_key(e.ja) for g in out for e in g.entries}

    def fresh(entries: Iterable[Entry]) -> tuple[Entry, ...]:
        kept = []
        for e in entries:
            if word_key(e.ja) not in seen:
                seen.add(word_key(e.ja))
                kept.append(e)
        return tuple(kept)

    card_words = fresh(Entry(w.ja, w.tr, None, w.example) for c in cards for w in c.words)
    reading_words = fresh(Entry(w.ja, w.tr, None, None)
                          for r in readings if r.lesson is not None for w in r.words if w.lesson is None)
    scene_words = fresh(Entry(w.ja, w.tr, None, None)
                        for r in readings if r.lesson is None for w in r.words if w.lesson is None)
    if card_words:
        out.append(Group("cards", Kind.ELSEWHERE, None, "KANJI CARDS", "Elsewhere", CARDS_TITLE, card_words))
    if reading_words:
        out.append(Group("reading", Kind.ELSEWHERE, None, "READING", "Elsewhere", READING_TITLE, reading_words))
    if scene_words:
        out.append(Group("scenes", Kind.ELSEWHERE, None, "SCENES", "Elsewhere", SCENES_TITLE, scene_words))
    return tuple(out)


def search_index(e: Entry) -> str:
    """What finds a word in the list: as written, in kana or romaji, or by each
    word of its meaning in any language; tokens joined by spaces."""
    entries = [*word_search_tokens(e.ja, e.tr), *search_tokens(romanize(e.ja))]
    return " ".join(dict.fromkeys(x for x in entries if x))


# A word's own page: the word, the lists it is in, and a few sentences that use it.

KANJI_IN = re.compile(f"[{furigana.KANJI}]")
READING_LINES = 5  # reading-text lines a word page shows at most: the shortest ones


def slug(ja: str) -> str:
    """A word page's path segment: the word as written, plus its kana when
    that differs (時計-とけい), so homographs (人[じん], 人[ひと]) get their
    own page. Depends on the word alone, so adding words never moves a page."""
    key = word_key(ja)
    plain, kana = furigana.plain(key), furigana.reading(key)
    return re.sub(r"\W+", "-", plain if plain == kana else f"{plain}-{kana}").strip("-")


@dataclass(frozen=True)
class Source:
    href: str  # from the site root
    label: str


@dataclass(frozen=True)
class Example:
    parts: tuple[tuple[str, bool], ...]  # furigana runs in order; True marks the word itself
    tr: Text
    source: Source

    @property
    def ja(self) -> str:
        return "".join(ja for ja, _ in self.parts)


@dataclass(frozen=True)
class WordPage:
    slug: str
    entry: Entry  # as the first list that has it gives it
    groups: tuple[Group, ...]  # every list it is in, in list order
    examples: tuple[Example, ...]


def _marked(ja: str, key: str) -> tuple[tuple[str, bool], ...]:
    """A sentence (furigana notation) in parts, each verbatim use of a word marked.

    Only a word with kanji is looked for: its furigana, reading included, then
    names that word alone. A kana word would also turn up inside other words
    (もう in もうしわけ), and an inflected use (食べました for 食べます) is not
    verbatim; neither is marked."""
    if not KANJI_IN.search(key):
        return ((ja, False),)
    pieces = ja.split(key)
    parts = [(p, False) for p in pieces]
    for i in range(len(pieces) - 1, 0, -1):
        parts.insert(i, (key, True))
    return tuple(p for p in parts if p[0])


def _whole(line: Line, key: str, source: Source) -> Example:
    return Example(_marked(line.ja, key), line.tr, source)


def _vocab_examples(groups: Iterable[Group]) -> dict[str, list[Example]]:
    out: dict[str, list[Example]] = {}
    for g in groups:
        if g.lesson is None:
            continue
        for e in g.entries:
            if e.example:
                source = Source(f"lessons/{g.lesson:02d}/#vocab", g.kicker)
                out.setdefault(word_key(e.ja), []).append(_whole(e.example, word_key(e.ja), source))
    return out


def _card_examples(cards: Iterable[Card]) -> dict[str, list[Example]]:
    out: dict[str, list[Example]] = {}
    for c in cards:
        for w in c.words:
            source = Source(f"kanji/{ord(c.char):x}/", f"Kanji card {c.char}")
            out.setdefault(word_key(w.ja), []).append(_whole(w.example, word_key(w.ja), source))
    return out


def _reading_examples(readings: Iterable[Reading]) -> dict[str, list[Example]]:
    """Every reading line (paragraph or dialog line) for each word it uses, the word marked, in text order."""
    out: dict[str, list[Example]] = {}
    for r in readings:
        source = Source(f"reading/{r.id}/", f"{'Reading' if r.lesson is not None else 'Scene'}: {r.title.en}")
        for block in (*r.prose, *r.dialog):
            keys = [None if t.word is None else word_key(r.words[t.word].ja) for t in block.tokens]
            for key in dict.fromkeys(k for k in keys if k is not None):
                parts = tuple((t.ja, k == key) for t, k in zip(block.tokens, keys, strict=True))
                out.setdefault(key, []).append(Example(parts, block.tr, source))
    return out


def _shortest(lines: Iterable[Example], n: int) -> tuple[Example, ...]:
    """The n shortest distinct lines, kept in the order given."""
    lines = _distinct(lines)
    chosen = set(sorted(range(len(lines)), key=lambda i: len(furigana.plain(lines[i].ja)))[:n])
    return tuple(x for i, x in enumerate(lines) if i in chosen)


def _distinct(examples: Iterable[Example]) -> tuple[Example, ...]:
    seen: set[str] = set()
    out = []
    for x in examples:
        plain = furigana.plain(x.ja)
        if plain not in seen:
            seen.add(plain)
            out.append(x)
    return tuple(out)


def word_pages(groups: tuple[Group, ...], cards: Iterable[Card], readings: Iterable[Reading]) -> tuple[WordPage, ...]:
    """One page per word, in list order. Its examples: the vocabulary example
    (the sentence its Anki note carries), its kanji cards' examples, then the
    shortest reading-text lines that use it, in text order."""
    vocab, card, read = _vocab_examples(groups), _card_examples(cards), _reading_examples(readings)
    entries: dict[str, Entry] = {}
    in_groups: dict[str, list[Group]] = {}
    for g in groups:
        for e in g.entries:
            entries.setdefault(word_key(e.ja), e)
            in_groups.setdefault(word_key(e.ja), []).append(g)
    pages, owner = [], {}
    for key, e in entries.items():
        s = slug(e.ja)
        if s in owner:
            raise ContentError(f"words {owner[s]!r} and {e.ja!r} would share the page words/{s}/")
        owner[s] = e.ja
        lines = _shortest(read.get(key, ()), READING_LINES)
        pages.append(WordPage(s, e, tuple(in_groups[key]),
                              _distinct((*vocab.get(key, ()), *card.get(key, ()), *lines))))
    return tuple(pages)
