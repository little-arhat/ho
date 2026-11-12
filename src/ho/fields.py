"""Shared content fields: Japanese in furigana notation, and learner-facing
text in English, Russian and Ukrainian. Each parser names the file and entry
it was reading when it fails."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ho import furigana
from ho.errors import ContentError

LANGS = ("en", "ru", "uk")


@dataclass(frozen=True)
class Text:
    en: str
    ru: str
    uk: str


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


def translations(value: Any, where: str) -> Text:
    if not isinstance(value, dict):
        raise ContentError(f"{where}: expected {{en, ru, uk}}")
    check_keys(value, set(LANGS), set(), where)
    if not all(isinstance(value[k], str) and value[k].strip() for k in LANGS):
        raise ContentError(f"{where}: en, ru and uk must all be non-empty")
    return Text(*(japanese(value[k], where) for k in LANGS))


def line(row: dict[str, Any], where: str) -> Line:
    check_keys(row, {"ja", "en", "ru", "uk"}, set(), where)
    return Line(japanese(row["ja"], where), translations({k: row[k] for k in LANGS}, where))
