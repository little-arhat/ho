"""Pages of the site, rendered from loaded content. Pure: no file writes."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jinja2
from markupsafe import Markup

from ho import katakana, phrasebook
from ho.katakana import Word
from ho.phrasebook import Phrasebook


@dataclass(frozen=True)
class Content:
    phrasebook: Phrasebook
    katakana: tuple[Word, ...]


@dataclass(frozen=True)
class Page:
    page: str
    path: str
    template: str
    title: str
    label: str
    jp: str
    blurb: str
    data: Callable[[Content], Any] | None = None


PAGES = (
    Page("home", "index.html", "home.html", "Home", "Home", "ホーム", ""),
    Page("phrasebook", "phrasebook/index.html", "phrasebook.html", "Phrase book", "Phrase book",
         "旅の言葉", "Phrases to say and to recognise, with casual forms and conjugation.",
         lambda c: phrasebook.view(c.phrasebook)),
    Page("katakana", "katakana/index.html", "katakana.html", "Katakana drill", "Katakana",
         "カタカナ", "Read loanwords and type them in romaji.",
         lambda c: katakana.view(c.katakana)),
)


def embed_json(value: Any) -> Markup:
    """JSON safe inside <script type="application/json">: no `<` can open a tag."""
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return Markup(text.replace("<", "\\u003c"))


def _root(path: str) -> str:
    return "../" * path.count("/")


def render_site(content: Content, templates: Path) -> dict[str, str]:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(templates), autoescape=True,
                             undefined=jinja2.StrictUndefined, keep_trailing_newline=True)
    nav = [{"page": p.page, "href": p.path.removesuffix("index.html") or "./", "label": p.label,
            "jp": p.jp, "blurb": p.blurb} for p in PAGES]
    return {
        p.path: env.get_template(p.template).render(
            page=p.page, title=p.title, root=_root(p.path), nav=nav,
            data=embed_json(p.data(content)) if p.data else None)
        for p in PAGES
    }
