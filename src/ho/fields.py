"""Shared content fields: Japanese in furigana notation, and learner-facing
text in English, Russian, Ukrainian and Spanish. Each parser names the file and entry
it was reading when it fails."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ho import furigana
from ho.errors import ContentError

LANGS = ("en", "ru", "uk", "es")


@dataclass(frozen=True)
class Text:
    en: str
    ru: str
    uk: str
    es: str


@dataclass(frozen=True)
class Line:
    ja: str
    tr: Text


def check_keys(row: dict[str, Any], required: set[str], optional: set[str], where: str) -> None:
    missing = required - set(row)
    extra = set(row) - required - optional
    if missing or extra:
        raise ContentError(f"{where}: missing {sorted(missing)}, unknown {sorted(extra)}")


def japanese(text: str, where: str) -> str:
    try:
        furigana.parse(text)
    except ContentError as e:
        raise ContentError(f"{where}: {e}") from e
    return text


# Letters a translation in that language never has (Japanese aside).
_FOREIGN = {
    "ru": re.compile("[іїєґІЇЄҐ]"),
    "uk": re.compile("[ыэъёЫЭЪЁ]"),
    "es": re.compile("[\u0400-\u04ff]"),
}


def check_alphabets(tr: dict[str, str], where: str) -> None:
    """Catch a translation pasted into the wrong language: Ukrainian has no
    ы э ъ ё, Russian has no і ї є ґ, Spanish no Cyrillic at all."""
    for lang, foreign in _FOREIGN.items():
        if m := foreign.search(tr[lang]):
            raise ContentError(f"{where}: {lang} has the letter {m.group(0)!r}: {tr[lang]!r}")


def translations(value: Any, where: str) -> Text:
    if not isinstance(value, dict):
        raise ContentError(f"{where}: expected {{{', '.join(LANGS)}}}")
    check_keys(value, set(LANGS), set(), where)
    if not all(isinstance(value[k], str) and value[k].strip() for k in LANGS):
        raise ContentError(f"{where}: {', '.join(LANGS)} must all be non-empty")
    check_alphabets(value, where)
    return Text(*(japanese(value[k], where) for k in LANGS))


def line(row: dict[str, Any], where: str) -> Line:
    check_keys(row, {"ja", *LANGS}, set(), where)
    return Line(japanese(row["ja"], where), translations({k: row[k] for k in LANGS}, where))


def by_lang(tr: Text) -> dict[str, str]:
    """A translation as page JSON: one key per language."""
    return {k: getattr(tr, k) for k in LANGS}
