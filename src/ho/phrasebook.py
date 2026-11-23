"""Phrase book: topics of phrases you say, phrases you hear, and tips."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from ho import furigana
from ho.errors import ContentError
from ho.fields import LANGS, check_alphabets
from ho.kana import romaji
from ho.kanji import fold
from ho.romaji import romanize, speech
from ho.verbs import KIND_LABEL, Verb, conjugate, find_verbs

Kind = Literal["say", "hear", "tip"]
_COLOR = re.compile(r"#[0-9a-fA-F]{6}")


@dataclass(frozen=True)
class Topic:
    id: str
    jp: str
    en: str
    color: str
    color_dark: str


@dataclass(frozen=True)
class Line:
    """A Japanese line with its translations: an answer or an example."""

    ja: str
    en: str
    ru: str
    uk: str
    es: str


@dataclass(frozen=True)
class Phrase:
    topic: str
    section: str
    kind: Kind
    ja: str = ""
    casual: str = ""
    en: str = ""
    ru: str = ""
    uk: str = ""
    es: str = ""
    note: str = ""
    level: str = ""
    answers: tuple[Line, ...] = ()
    examples: tuple[Line, ...] = ()

    def japanese(self) -> tuple[str, ...]:
        """Every Japanese line on the card, the note excluded."""
        lines = (self.ja, self.casual, *(a.ja for a in self.answers + self.examples))
        return tuple(t for t in lines if t)


@dataclass(frozen=True)
class Phrasebook:
    topics: tuple[Topic, ...]
    phrases: tuple[Phrase, ...]
    verbs: tuple[Verb, ...]


def _langs(x: Line | Phrase) -> dict[str, str]:
    return {k: getattr(x, k) for k in LANGS}


def _line(row: dict[str, Any], where: str) -> Line:
    try:
        line = Line(**row)
    except TypeError as e:
        raise ContentError(f"{where}: {e}") from e
    if not all((line.ja, *_langs(line).values())):
        raise ContentError(f"{where}: ja, {', '.join(LANGS)} are all required")
    check_alphabets(_langs(line), where)
    return line


def _topic(row: dict[str, Any], where: str) -> Topic:
    try:
        t = Topic(**row)
    except TypeError as e:
        raise ContentError(f"{where}: {e}") from e
    if not (t.id and t.jp and t.en):
        raise ContentError(f"{where}: id, jp and en are required")
    if not (_COLOR.fullmatch(t.color) and _COLOR.fullmatch(t.color_dark)):
        raise ContentError(f"{where}: colours must be #rrggbb")
    return t


def _phrase(row: dict[str, Any], topics: set[str], where: str) -> Phrase:
    fields = dict(row)
    answers = tuple(_line(a, f"{where} answer") for a in fields.pop("answers", ()))
    examples = tuple(_line(a, f"{where} example") for a in fields.pop("examples", ()))
    try:
        p = Phrase(**fields, answers=answers, examples=examples)
    except TypeError as e:
        raise ContentError(f"{where}: {e}") from e
    if p.topic not in topics:
        raise ContentError(f"{where}: unknown topic {p.topic!r}")
    check_alphabets(_langs(p), where)
    if p.kind not in ("say", "hear", "tip"):
        raise ContentError(f"{where}: unknown kind {p.kind!r}")
    if p.kind == "tip" and not p.note:
        raise ContentError(f"{where}: a tip needs a note")
    if p.kind != "tip" and not all((p.ja, *_langs(p).values())):
        raise ContentError(f"{where}: ja, {', '.join(LANGS)} are all required")
    for text in (*p.japanese(), p.note):
        try:
            furigana.parse(text)
        except ContentError as e:
            raise ContentError(f"{where}: {e}") from e
    return p


def anchor(p: Phrase) -> str:
    """A phrase card's address on the phrase-book page (`?phrase=`): its topic,
    section, kind and words (the same words can be a card you say and one you hear)."""
    return re.sub(r"\W+", "-", f"{p.topic} {p.section} {p.kind} {furigana.plain(p.ja)}").strip("-").lower()


def by_ja(pb: Phrasebook) -> dict[str, tuple[Phrase, ...]]:
    """Phrases you say or hear, by their Japanese (the same phrase may be filed under two topics)."""
    out: dict[str, list[Phrase]] = {}
    for p in pb.phrases:
        if p.kind != "tip":
            out.setdefault(p.ja, []).append(p)
    return {ja: tuple(ps) for ja, ps in out.items()}


def appears_in(p: Phrase, text: str) -> bool:
    """Whether a line (furigana notation) says the phrase's Japanese, 〇〇
    standing for any words, with spacing, punctuation and kana script ignored.

    Casual forms do not count: many are a word or two (〇〇で, あの…) that
    would be found in almost any line, so a match would prove nothing."""
    pieces = [re.escape(fold(x)) for x in furigana.plain(p.ja).split("〇〇")]
    return re.search(".+?".join(pieces), fold(furigana.plain(text))) is not None


def load(path: Path, verbs: tuple[Verb, ...]) -> Phrasebook:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if set(data) != {"topic", "phrase"}:
        raise ContentError(f"{path}: expected [[topic]] and [[phrase]] tables, found {sorted(data)}")
    topics = tuple(_topic(row, f"{path}: topic #{i + 1}") for i, row in enumerate(data["topic"]))
    ids = {t.id for t in topics}
    if len(ids) != len(topics):
        raise ContentError(f"{path}: duplicate topic ids")
    phrases = tuple(
        _phrase(row, ids, f"{path}: phrase #{i + 1} {row.get('ja') or row.get('note', '')[:20]!r}")
        for i, row in enumerate(data["phrase"])
    )
    anchors = [anchor(p) for p in phrases if p.kind != "tip"]
    twice = sorted({a for a in anchors if anchors.count(a) > 1})
    if twice:
        raise ContentError(f"{path}: the same card twice: {', '.join(twice)}")
    return Phrasebook(topics, phrases, verbs)


def _verb_view(v: Verb) -> dict[str, Any]:
    term = v.dict.removesuffix("する") if v.kind == "suru" else v.dict
    return {
        "dict": furigana.segments_json(v.dict),
        "romaji": romaji(furigana.reading(v.dict)),
        "kind": KIND_LABEL[v.kind],
        "gloss": v.gloss.base,
        "lookup": furigana.plain(v.dict),
        "wiktionary": furigana.plain(term),
        "forms": [
            {"label": f.label, "ja": furigana.segments_json(f.ja),
             "romaji": romaji(furigana.reading(f.ja)), "meaning": f.meaning}
            for f in conjugate(v)
        ],
    }


def _line_view(line: Line, clip: Callable[[str], str]) -> dict[str, Any]:
    return {"ja": furigana.segments_json(line.ja), "ro": romanize(line.ja), "say": speech(line.ja), "clip": clip(line.ja),
            **_langs(line)}


def _words(texts: tuple[str, ...]) -> list[list[str]]:
    seen: dict[str, str] = {}
    for text in texts:
        for seg in furigana.parse(text):
            if seg.ruby is not None:
                seen.setdefault(seg.text, seg.ruby)
    return [[base, ruby] for base, ruby in seen.items()]


def view(pb: Phrasebook, clip: Callable[[str], str],
         texts: Callable[[Phrase], list[dict[str, str]]]) -> dict[str, Any]:
    """The phrase book as the page's JSON: parsed ruby, search text, verb tables,
    and for each phrase its anchor and the texts that use it ({title, href})."""
    verb_index: dict[str, int] = {}
    verbs: list[dict[str, Any]] = []
    phrases = []
    for p in pb.phrases:
        jp = p.japanese()
        ids = []
        for v in find_verbs(jp, pb.verbs):
            if v.dict not in verb_index:
                verb_index[v.dict] = len(verbs)
                verbs.append(_verb_view(v))
            ids.append(verb_index[v.dict])
        lines = p.answers + p.examples
        search = [*(furigana.plain(t) for t in jp), *(furigana.reading(t) for t in jp),
                  *_langs(p).values(), furigana.plain(p.note),
                  *(x for a in lines for x in _langs(a).values())]
        phrases.append({
            "topic": p.topic,
            "section": p.section,
            "anchor": anchor(p) if p.kind != "tip" else "",
            "texts": texts(p) if p.kind != "tip" else [],
            "kind": p.kind,
            "ja": furigana.segments_json(p.ja),
            "ro": romanize(p.ja),
            "say": speech(p.ja),
            "clip": clip(p.ja),
            "casual": furigana.segments_json(p.casual),
            "casual_ro": romanize(p.casual),
            **_langs(p),
            "note": furigana.segments_json(p.note),
            "level": p.level,
            "answers": [_line_view(a, clip) for a in p.answers],
            "examples": [_line_view(a, clip) for a in p.examples],
            "words": _words(jp),
            "verbs": ids,
            "search": " ".join(s for s in search if s),
        })
    topics = [asdict(t) for t in pb.topics]
    return {"topics": topics, "phrases": phrases, "verbs": verbs}
