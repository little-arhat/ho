"""Pages of the site, rendered from loaded content. Pure: no file writes."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jinja2
from markupsafe import Markup, escape

from ho import furigana, kanji, katakana, lessons, phrasebook, reading
from ho.kanji import Card
from ho.katakana import Word
from ho.lessons import Lesson
from ho.phrasebook import Phrasebook
from ho.reading import Reading


@dataclass(frozen=True)
class Content:
    lessons: tuple[Lesson, ...]
    phrasebook: Phrasebook
    katakana: tuple[Word, ...]
    kanji: tuple[Card, ...]
    strokes: dict[str, tuple[str, ...]]  # KanjiVG stroke paths for every card
    readings: tuple[Reading, ...]


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
    Section("reading", "reading/", "Reading", "読み物", "Short stories in the words learned so far; tap a word for its meaning."),
    Section("kanji", "kanji/", "Kanji", "漢字", "Every kanji in the lessons: readings, stroke order, words; a drill."),
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
             data=phrasebook.view(content.phrasebook)),
        Page("katakana/index.html", "katakana.html", "Katakana drill", "katakana",
             data=katakana.view(content.katakana)),
    ]
    numbers = [lesson.number for lesson in content.lessons]
    for i, lesson in enumerate(content.lessons):
        out.append(Page(
            f"lessons/{lesson.number:02d}/index.html", "lesson.html", f"{lesson.number}. {lesson.title.en}", "lessons",
            {"lesson": lesson,
             "prev": numbers[i - 1] if i > 0 else None,
             "next": numbers[i + 1] if i + 1 < len(numbers) else None},
            data=lessons.exercises_view(lesson)))
    out.extend(_kanji_pages(content))
    out.extend(_reading_pages(content))
    return tuple(out)


def _reading_pages(content: Content) -> list[Page]:
    texts = content.readings
    out = [Page("reading/index.html", "readings.html", "Reading", "reading", {
        "by_lesson": [(n, [r for r in texts if r.lesson == n]) for n in sorted({r.lesson for r in texts})]})]
    for i, r in enumerate(texts):
        out.append(Page(f"reading/{r.id}/index.html", "reading.html", r.title.en, "reading", {
            "text": r,
            "prev": texts[i - 1] if i > 0 else None,
            "next": texts[i + 1] if i + 1 < len(texts) else None,
        }, data={"words": reading.words_view(r)}))
    return out


def assets(content: Content) -> dict[str, Path]:
    """Files copied into the site as they are: published path → source."""
    return {f"reading/{r.id}.jpg": r.image for r in content.readings if r.image is not None}


def card_path(card: Card) -> str:
    return f"kanji/{ord(card.char):x}/index.html"


def _kanji_pages(content: Content) -> list[Page]:
    words = kanji.lesson_words(content.lessons)
    first_lesson = {c: ws[0].lesson for c, ws in words.items()}
    cards = content.kanji
    index = Page("kanji/index.html", "kanji.html", "Kanji", "kanji", {
        "book": [c for c in cards if c.number is not None],
        "by_lesson": [(n, [c for c in cards if c.number is None and first_lesson.get(c.char) == n])
                      for n in sorted({first_lesson[c.char] for c in cards if c.number is None})],
    })
    drill = Page("kanji/drill/index.html", "kanji_drill.html", "Kanji drill", "kanji",
                 {"lessons": [lesson.number for lesson in content.lessons]},
                 data=kanji.drill_view(kanji.drill_items(cards, content.lessons)))
    out = [index, drill]
    for i, card in enumerate(cards):
        out.append(Page(card_path(card), "kanji_card.html", f"{card.char} · kanji", "kanji", {
            "card": card,
            "frames": kanji.stroke_frames(content.strokes[card.char]),
            "lesson_words": words.get(card.char, ()),
            "prev": cards[i - 1] if i > 0 else None,
            "next": cards[i + 1] if i + 1 < len(cards) else None,
        }))
    return out


def _root(path: str) -> str:
    return "../" * path.count("/")


def render_site(content: Content, templates: Path) -> dict[str, str]:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(templates), autoescape=True,
                             undefined=jinja2.StrictUndefined, keep_trailing_newline=True)
    env.filters["ruby"] = ruby
    env.filters["hex"] = lambda c: f"{ord(c):x}"
    render: Callable[[Page], str] = lambda p: env.get_template(p.template).render(
        title=p.title, page=p.section, root=_root(p.path), sections=SECTIONS,
        data=embed_json(p.data) if p.data is not None else None, **p.context)
    return {p.path: render(p) for p in pages(content)}
