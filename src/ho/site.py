"""Pages of the site, rendered from loaded content. Pure: no file writes."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jinja2
from markupsafe import Markup, escape

from ho import furigana, katakana, lessons, phrasebook
from ho.katakana import Word
from ho.lessons import Lesson
from ho.phrasebook import Phrasebook


@dataclass(frozen=True)
class Content:
    lessons: tuple[Lesson, ...]
    phrasebook: Phrasebook
    katakana: tuple[Word, ...]


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
            f"lessons/{lesson.number:02d}/index.html", "lesson.html", f"Lesson {lesson.number}", "lessons",
            {"lesson": lesson,
             "prev": numbers[i - 1] if i > 0 else None,
             "next": numbers[i + 1] if i + 1 < len(numbers) else None},
            data=lessons.exercises_view(lesson)))
    return tuple(out)


def _root(path: str) -> str:
    return "../" * path.count("/")


def render_site(content: Content, templates: Path) -> dict[str, str]:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(templates), autoescape=True,
                             undefined=jinja2.StrictUndefined, keep_trailing_newline=True)
    env.filters["ruby"] = ruby
    render: Callable[[Page], str] = lambda p: env.get_template(p.template).render(
        title=p.title, page=p.section, root=_root(p.path), sections=SECTIONS,
        data=embed_json(p.data) if p.data is not None else None, **p.context)
    return {p.path: render(p) for p in pages(content)}
