"""Pages of the site, rendered from loaded content. Pure: no file writes."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jinja2
from markupsafe import Markup, escape

from ho import (
    anki,
    audio,
    furigana,
    kanji,
    katakana,
    lessons,
    phrasebook,
    reading,
    romaji,
    words,
)
from ho.fields import LANGS
from ho.kanji import Card
from ho.katakana import Word
from ho.lessons import Lesson
from ho.phrasebook import Phrasebook
from ho.reading import Reading
from ho.words import Topic


@dataclass(frozen=True)
class Content:
    lessons: tuple[Lesson, ...]
    phrasebook: Phrasebook
    katakana: tuple[Word, ...]
    kanji: tuple[Card, ...]
    strokes: dict[str, tuple[str, ...]]  # KanjiVG stroke paths for every card
    readings: tuple[Reading, ...]
    topics: tuple[Topic, ...]  # the book's reference word lists
    clips: frozenset[str]  # recorded lines (audio.key) found in audio_dir
    audio_dir: Path


@dataclass(frozen=True)
class Section:
    """A top-level section: in the nav and on the home page."""

    page: str
    href: str
    label: str
    jp: str
    blurb: str


SECTIONS = (
    Section("lessons", "lessons/", "Lessons", "課", "Minna no Nihongo, lesson by lesson: rules, vocabulary, exercises."),
    Section("words", "words/", "Words", "単語", "Every word on the site, by lesson and topic; search in any language or romaji."),
    Section("reading", "reading/", "Reading", "読み物", "Short stories and dialogs in the words learned so far; tap a word for its meaning."),
    Section("kanji", "kanji/", "Kanji", "漢字", "Every kanji on the site: readings, stroke order, words; a drill and handwriting practice."),
    Section("phrasebook", "phrasebook/", "Phrase book", "旅の言葉",
            "Phrases to say and to recognise, with casual forms and conjugation."),
    Section("katakana", "katakana/", "Katakana", "カタカナ", "Read loanwords and type them in romaji."),
)


@dataclass(frozen=True)
class Page:
    path: str
    template: str
    title: str
    section: str
    context: dict[str, Any] = field(default_factory=dict)
    data: Any = None


def embed_json(value: Any) -> Markup:
    """JSON safe inside <script type="application/json">: no `<` can open a tag."""
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return Markup(text.replace("<", "\\u003c"))


def ruby(text: str) -> Markup:
    """Furigana notation as escaped HTML with <ruby> markup."""
    return Markup("").join(
        escape(s.text) if s.ruby is None else Markup("<ruby>%s<rt>%s</rt></ruby>") % (s.text, s.ruby)
        for s in furigana.parse(text)
    )


def pages(content: Content) -> tuple[Page, ...]:
    out = [
        Page("index.html", "home.html", "Home", "home"),
        Page("lessons/index.html", "lessons.html", "Lessons", "lessons", {"lessons": content.lessons}),
        Page("phrasebook/index.html", "phrasebook.html", "Phrase book", "phrasebook",
             data=phrasebook.view(content.phrasebook, clip_of(content))),
        Page("katakana/index.html", "katakana.html", "Katakana drill", "katakana",
             data=katakana.view(content.katakana)),
    ]
    numbers = [lesson.number for lesson in content.lessons]
    deck_of = {p.group: p.file for p in anki_packages(content) if p.group}
    for i, lesson in enumerate(content.lessons):
        out.append(Page(
            f"lessons/{lesson.number:02d}/index.html", "lesson.html", f"{lesson.number}. {lesson.title.en}", "lessons",
            {"lesson": lesson,
             "prev": numbers[i - 1] if i > 0 else None,
             "next": numbers[i + 1] if i + 1 < len(numbers) else None,
             "deck": deck_of[f"l{lesson.number}"]},
            data=lessons.exercises_view(lesson)))
    out.extend(_kanji_pages(content))
    out.append(_words_page(content))
    out.extend(_word_pages(content))
    out.extend(_reading_pages(content))
    return tuple(out)


def word_groups(content: Content) -> tuple[words.Group, ...]:
    return words.groups(content.lessons, content.topics, content.kanji, content.readings)


def anki_packages(content: Content) -> tuple[anki.Package, ...]:
    return anki.packages(word_groups(content), clip_of(content))


def _words_page(content: Content) -> Page:
    groups = word_groups(content)
    return Page("words/index.html", "words.html", "Words", "words", {
        "groups": groups,
        "decks": {p.group: p.file for p in anki_packages(content) if p.group},
        "all_deck": anki.ALL_FILE,
        "filters": [("all", "ALL"), *((g.id, g.label) for g in groups)],
        "carded": {c.char for c in content.kanji},
    })


def _word_pages(content: Content) -> list[Page]:
    pages = words.word_pages(word_groups(content), content.kanji, content.readings)
    return [Page(f"words/{p.slug}/index.html", "word.html", f"{furigana.plain(p.entry.ja)} · word", "words", {
        "word": p,
        "prev": pages[i - 1] if i > 0 else None,
        "next": pages[i + 1] if i + 1 < len(pages) else None,
        "carded": {c.char for c in content.kanji},
    }) for i, p in enumerate(pages)]


def _reading_pages(content: Content) -> list[Page]:
    texts = content.readings
    numbers = sorted({r.lesson for r in texts})
    out = [Page("reading/index.html", "readings.html", "Reading", "reading", {
        "by_lesson": [(n, [r for r in texts if r.lesson == n]) for n in numbers],
        "filters": [("all", "ALL"), *((str(n), f"L{n}") for n in sorted({n for r in texts for n in r.lessons}))]})]
    for i, r in enumerate(texts):
        out.append(Page(f"reading/{r.id}/index.html", "reading.html", r.title.en, "reading", {
            "text": r,
            "prev": texts[i - 1] if i > 0 else None,
            "next": texts[i + 1] if i + 1 < len(texts) else None,
        }, data={"words": reading.words_view(r, {c.char for c in content.kanji}, words.slug)}))
    return out


def assets(content: Content) -> dict[str, Path]:
    """Files copied into the site as they are: published path → source."""
    pictures = {f"reading/{r.id}.jpg": r.image for r in content.readings if r.image is not None}
    used = {audio.key(t) for t in spoken_texts(content)} & content.clips
    return pictures | {f"audio/{k}.m4a": content.audio_dir / f"{k}.m4a" for k in sorted(used)}


def spoken_texts(content: Content) -> list[str]:
    """Every Japanese line the site has a listen button for (furigana notation)."""
    out: list[str] = []
    for lesson in content.lessons:
        out += [x.ja for r in lesson.rules for x in r.examples]
        for w in lesson.vocab:
            out.append(w.furigana)
            if w.example:
                out.append(w.example.ja)
    for card in content.kanji:
        out += [x for w in card.words for x in (w.ja, w.example.ja)]
    for r in content.readings:
        out += [x.ja for x in (*r.prose, *r.dialog)]
    out += [e.ja for g in word_groups(content) for e in g.entries]
    for p in content.phrasebook.phrases:
        out += [p.ja, *(a.ja for a in p.answers + p.examples)]
    return list(dict.fromkeys(t for t in out if t))


def clip_of(content: Content):
    """The recorded clip for a line, or "" when there is none (the page uses the device voice)."""
    def clip(text: str) -> str:
        k = audio.key(text)
        return k if k in content.clips else ""
    return clip


def card_path(card: Card) -> str:
    return f"kanji/{ord(card.char):x}/index.html"


def _kanji_pages(content: Content) -> list[Page]:
    by_kanji = kanji.lesson_words(content.lessons)
    first_lesson = {c: ws[0].lesson for c, ws in by_kanji.items()}
    cards = content.kanji
    elsewhere = [c for c in cards if c.number is None and c.char not in first_lesson]
    index = Page("kanji/index.html", "kanji.html", "Kanji", "kanji", {
        "in_lessons": {c: sorted({w.lesson for w in ws}) for c, ws in by_kanji.items()},
        "search": {c.char: kanji.search_index(c, by_kanji.get(c.char, ())) for c in cards},
        "filters": [("all", "ALL"), ("book", "15-MIN BOOK"),
                    *((f"l{lesson.number}", f"L{lesson.number}") for lesson in content.lessons),
                    *([("other", "ELSEWHERE")] if elsewhere else [])],
        "book": [c for c in cards if c.number is not None],
        "by_lesson": [(n, [c for c in cards if c.number is None and first_lesson.get(c.char) == n])
                      for n in sorted({first_lesson[c.char] for c in cards
                                       if c.number is None and c.char in first_lesson})],
        "elsewhere": elsewhere,
    })
    drill = Page("kanji/drill/index.html", "kanji_drill.html", "Kanji drill", "kanji",
                 {"lessons": [lesson.number for lesson in content.lessons]},
                 data=kanji.drill_view(cards, content.lessons, clip_of(content)))
    write = Page("kanji/write/index.html", "kanji_write.html", "Kanji writing", "kanji",
                 {"lessons": [lesson.number for lesson in content.lessons]},
                 data=kanji.write_view(cards, content.lessons, clip_of(content)))
    out = [index, drill, write]
    for i, card in enumerate(cards):
        out.append(Page(card_path(card), "kanji_card.html", f"{card.char} · kanji", "kanji", {
            "card": card,
            "frames": kanji.stroke_frames(content.strokes[card.char]),
            "lesson_words": by_kanji.get(card.char, ()),
            "prev": cards[i - 1] if i > 0 else None,
            "next": cards[i + 1] if i + 1 < len(cards) else None,
        }))
    return out


def _root(path: str) -> str:
    return "../" * path.count("/")


def render_site(content: Content, templates: Path) -> dict[str, str]:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(templates), autoescape=True,
                             undefined=jinja2.StrictUndefined, keep_trailing_newline=True)
    env.globals["LANGS"] = LANGS
    env.filters["ruby"] = ruby
    env.filters["hex"] = lambda c: f"{ord(c):x}"
    env.filters["speech"] = romaji.speech
    env.filters["clip"] = clip_of(content)
    env.filters["kanji"] = lambda text: list(dict.fromkeys(kanji.kanji_in(text)))
    env.filters["reading_romaji"] = kanji.reading_romaji
    env.filters["word_search"] = words.search_index
    env.filters["word_slug"] = words.slug
    env.filters["plain"] = furigana.plain
    env.filters["romanize"] = romaji.romanize
    render: Callable[[Page], str] = lambda p: env.get_template(p.template).render(
        title=p.title, page=p.section, root=_root(p.path), sections=SECTIONS,
        data=embed_json(p.data) if p.data is not None else None, **p.context)
    return {p.path: render(p) for p in pages(content)} | data_files(content)


def data_files(content: Content) -> dict[str, str]:
    """JSON a page fetches on demand: each card's stroke paths, for the writing drill."""
    return {f"kanji/{ord(c.char):x}/strokes.json": json.dumps(content.strokes[c.char], separators=(",", ":"))
            for c in content.kanji}
