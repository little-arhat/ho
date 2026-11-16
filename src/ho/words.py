"""Every word on the site in one list: lesson vocabulary, the book's topic
lists (content/words/<id>.toml + <id>.csv), and the words that kanji cards and
reading texts bring. A topic list is kept whole; the words kanji cards and
reading texts bring are listed only if no earlier group has them."""

from __future__ import annotations

import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ho import furigana
from ho.errors import ContentError
from ho.fields import Text, check_keys, translations
from ho.kanji import Card, fold, meaning_answers, reading_answers
from ho.lessons import Lesson, load_vocab
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


@dataclass(frozen=True)
class Group:
    id: str  # the filter key: l6, a topic id, cards, reading
    label: str  # the filter button
    kicker: str  # what the group is, before its title
    title: Text
    entries: tuple[Entry, ...]


CARDS_TITLE = Text("Words on kanji cards", "Слова с карточек кандзи", "Слова з карток кандзі")
READING_TITLE = Text("New words in reading texts", "Новые слова из текстов для чтения", "Нові слова з текстів для читання")


def _key(ja: str) -> str:
    return ja.replace("～", "").strip()


def _vocab(words: Iterable[VocabWord]) -> tuple[Entry, ...]:
    return tuple(Entry(w.furigana, w.tr, w.note) for w in words)


def groups(lessons: Iterable[Lesson], topics: Iterable[Topic], cards: Iterable[Card],
           readings: Iterable[Reading]) -> tuple[Group, ...]:
    """Lessons in order, each followed by the topic lists printed with it,
    then card words and reading words not in any of those."""
    out: list[Group] = []
    by_lesson: dict[int, list[Topic]] = {}
    for t in topics:
        by_lesson.setdefault(t.lesson, []).append(t)
    for lesson in lessons:
        out.append(Group(f"l{lesson.number}", f"L{lesson.number}", f"Lesson {lesson.number}",
                         lesson.title, _vocab(lesson.vocab)))
        for t in by_lesson.get(lesson.number, []):
            out.append(Group(t.id, t.title.en.upper(), f"Reference words · lesson {t.lesson}", t.title, _vocab(t.words)))
    seen = {_key(e.ja) for g in out for e in g.entries}

    def fresh(entries: Iterable[Entry]) -> tuple[Entry, ...]:
        kept = []
        for e in entries:
            if _key(e.ja) not in seen:
                seen.add(_key(e.ja))
                kept.append(e)
        return tuple(kept)

    card_words = fresh(Entry(w.ja, w.tr, None) for c in cards for w in c.words)
    reading_words = fresh(Entry(w.ja, w.tr, None) for r in readings for w in r.words if w.lesson is None)
    if card_words:
        out.append(Group("cards", "KANJI CARDS", "Elsewhere", CARDS_TITLE, card_words))
    if reading_words:
        out.append(Group("reading", "READING", "Elsewhere", READING_TITLE, reading_words))
    return tuple(out)


def search_index(e: Entry) -> str:
    """What finds a word in the list: as written, in kana or romaji, or by its
    meaning in any language; folded entries joined by spaces."""
    entries = [fold(furigana.plain(e.ja)), *reading_answers(furigana.reading(e.ja)), fold(romanize(e.ja)),
               *meaning_answers(e.tr)]
    return " ".join(dict.fromkeys(x for x in entries if x))
