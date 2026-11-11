"""Pages of the site, rendered from loaded content. Pure: no file writes."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import jinja2
from markupsafe import Markup

from ho import phrasebook
from ho.katakana import Word
from ho.phrasebook import Phrasebook

TEMPLATES = Path(__file__).resolve().parents[2] / "templates"


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


PAGES = (
    Page("home", "index.html", "home.html", "Home", "Home", "ホーム", ""),
    Page("phrasebook", "phrasebook/index.html", "phrasebook.html", "Phrase book", "Phrase book",
         "旅の言葉", "Phrases to say and to recognise, with casual forms and conjugation."),
    Page("katakana", "katakana/index.html", "katakana.html", "Katakana drill", "Katakana",
         "カタカナ", "Read loanwords and type them in romaji."),
)


def embed_json(value: Any) -> Markup:
    """JSON safe to place inside <script type="application/json">."""
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return Markup(text.replace("</", "<\\/"))


def _root(path: str) -> str:
    return "../" * path.count("/")


def _data(page: str, content: Content) -> Markup | None:
    if page == "phrasebook":
        return embed_json(phrasebook.view(content.phrasebook))
    if page == "katakana":
        return embed_json([{"ja": w.ja, "en": w.en, "ru": w.ru, "uk": w.uk, **asdict(w.answers)}
                           for w in content.katakana])
    return None


def render_site(content: Content) -> dict[str, str]:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES), autoescape=True,
                             undefined=jinja2.StrictUndefined, keep_trailing_newline=True)
    nav = [{"page": p.page, "href": p.path.removesuffix("index.html") or "./", "label": p.label,
            "jp": p.jp, "blurb": p.blurb} for p in PAGES]
    out = {}
    for p in PAGES:
        root = _root(p.path)
        out[p.path] = env.get_template(p.template).render(
            page=p.page, title=p.title, root=root, nav=nav, data=_data(p.page, content))
    return out
