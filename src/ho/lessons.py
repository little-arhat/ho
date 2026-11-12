"""Lessons: one Minna no Nihongo chapter each.

A lesson is `content/lessons/NN.toml` (rules, exercises, teacher's notes)
plus `content/lessons/NN.vocab.csv` (its words). Learner-facing text comes
in English, Russian and Ukrainian; Japanese is in furigana notation.
"""

from __future__ import annotations

import csv
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ho import furigana
from ho.errors import ContentError

LANGS = ("en", "ru", "uk")
BLANK = "＿"


@dataclass(frozen=True)
class Text:
    en: str
    ru: str
    uk: str


@dataclass(frozen=True)
class Line:
    ja: str
    tr: Text


@dataclass(frozen=True)
class Part:
    """One block of a pattern diagram: fixed Japanese, or a slot to fill."""

    ja: str = ""
    slot: str = ""
    label: Text | None = None


@dataclass(frozen=True)
class Table:
    head: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class Rule:
    title: Text
    explain: Text
    pattern: tuple[Part, ...]
    table: Table | None
    examples: tuple[Line, ...]


@dataclass(frozen=True)
class Choice:
    ja: str
    options: tuple[str, ...]
    answer: str
    tr: Text


@dataclass(frozen=True)
class Reorder:
    parts: tuple[str, ...]
    tr: Text


@dataclass(frozen=True)
class Note:
    date: str
    text: str


@dataclass(frozen=True)
class Word:
    kanji: str
    kana: str
    furigana: str
    tr: Text
    note: Text | None
    example: Line | None


@dataclass(frozen=True)
class Lesson:
    number: int
    title: Text
    grammar: str
    rules: tuple[Rule, ...]
    exercises: tuple[Choice | Reorder, ...]
    notes: tuple[Note, ...]
    vocab: tuple[Word, ...]


def _keys(row: dict[str, Any], required: set[str], optional: set[str], where: str) -> None:
    missing = required - set(row)
    extra = set(row) - required - optional
    if missing or extra:
        raise ContentError(f"{where}: missing {sorted(missing)}, unknown {sorted(extra)}")


def _japanese(text: str, where: str) -> str:
    try:
        furigana.parse(text)
    except ContentError as e:
        raise ContentError(f"{where}: {e}") from e
    return text


def _text(value: Any, where: str) -> Text:
    if not isinstance(value, dict):
        raise ContentError(f"{where}: expected {{en, ru, uk}}")
    _keys(value, set(LANGS), set(), where)
    if not all(isinstance(value[k], str) and value[k].strip() for k in LANGS):
        raise ContentError(f"{where}: en, ru and uk must all be non-empty")
    return Text(*(_japanese(value[k], where) for k in LANGS))


def _line(row: dict[str, Any], where: str) -> Line:
    _keys(row, {"ja", "en", "ru", "uk"}, set(), where)
    return Line(_japanese(row["ja"], where), _text({k: row[k] for k in LANGS}, where))


def _part(row: dict[str, Any], where: str) -> Part:
    if "ja" in row:
        _keys(row, {"ja"}, set(), where)
        return Part(ja=_japanese(row["ja"], where))
    _keys(row, {"slot", "en", "ru", "uk"}, set(), where)
    if not re.fullmatch(r"[a-z]+", row["slot"]):
        raise ContentError(f"{where}: slot id must be lowercase letters")
    return Part(slot=row["slot"], label=_text({k: row[k] for k in LANGS}, where))


def _table(row: dict[str, Any], where: str) -> Table:
    _keys(row, {"head", "rows"}, set(), where)
    head = tuple(_japanese(h, where) for h in row["head"])
    rows = tuple(tuple(_japanese(c, where) for c in r) for r in row["rows"])
    if any(len(r) != len(head) for r in rows):
        raise ContentError(f"{where}: every row needs {len(head)} cells")
    return Table(head, rows)


def _rule(row: dict[str, Any], where: str) -> Rule:
    _keys(row, {"title", "explain"}, {"pattern", "table", "example"}, where)
    return Rule(
        title=_text(row["title"], f"{where} title"),
        explain=_text(row["explain"], f"{where} explain"),
        pattern=tuple(_part(p, f"{where} pattern") for p in row.get("pattern", ())),
        table=_table(row["table"], f"{where} table") if "table" in row else None,
        examples=tuple(_line(e, f"{where} example #{i + 1}") for i, e in enumerate(row.get("example", ()))),
    )


def _exercise(row: dict[str, Any], where: str) -> Choice | Reorder:
    kind = row.get("kind")
    if kind == "choice":
        _keys(row, {"kind", "ja", "options", "answer", "en", "ru", "uk"}, set(), where)
        if row["ja"].count(BLANK) != 1:
            raise ContentError(f"{where}: the sentence needs exactly one {BLANK}")
        if row["answer"] not in row["options"] or len(set(row["options"])) != len(row["options"]):
            raise ContentError(f"{where}: options must be distinct and include the answer")
        return Choice(_japanese(row["ja"], where), tuple(_japanese(o, where) for o in row["options"]),
                      row["answer"], _text({k: row[k] for k in LANGS}, where))
    if kind == "reorder":
        _keys(row, {"kind", "parts", "en", "ru", "uk"}, set(), where)
        if len(row["parts"]) < 3 or len(set(row["parts"])) != len(row["parts"]):
            raise ContentError(f"{where}: needs at least 3 distinct parts")
        return Reorder(tuple(_japanese(p, where) for p in row["parts"]), _text({k: row[k] for k in LANGS}, where))
    raise ContentError(f"{where}: kind must be 'choice' or 'reorder'")


def _note(row: dict[str, Any], where: str) -> Note:
    _keys(row, {"text"}, {"date"}, where)
    date = row.get("date", "")
    if date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(date)):
        raise ContentError(f"{where}: date must be YYYY-MM-DD")
    return Note(str(date), _japanese(row["text"].strip(), where))


VOCAB_COLUMNS = ("kanji", "kana", "furigana", "en", "ru", "uk", "note_en", "note_ru", "note_uk",
                 "example", "example_en", "example_ru", "example_uk")


def _optional_text(row: dict[str, str], prefix: str, where: str) -> Text | None:
    values = {k: row[f"{prefix}_{k}"] for k in LANGS}
    if not any(values.values()):
        return None
    return _text(values, f"{where} {prefix}")


def load_vocab(path: Path) -> tuple[Word, ...]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != VOCAB_COLUMNS:
            raise ContentError(f"{path}: columns must be {','.join(VOCAB_COLUMNS)}")
        out = []
        for line, row in enumerate(reader, start=2):
            where = f"{path}:{line}"
            fg = _japanese(row["furigana"], where)
            written = row["kanji"] or row["kana"]
            if furigana.plain(fg) != written or furigana.reading(fg) != row["kana"]:
                raise ContentError(f"{where}: furigana {fg!r} does not give {written!r} / {row['kana']!r}")
            example = None
            if row["example"]:
                tr = _optional_text(row, "example", where)
                if tr is None:
                    raise ContentError(f"{where}: example needs en, ru and uk translations")
                example = Line(_japanese(row["example"], where), tr)
            elif any(row[f"example_{k}"] for k in LANGS):
                raise ContentError(f"{where}: example translation without an example")
            out.append(Word(row["kanji"], row["kana"], fg,
                            _text({k: row[k] for k in LANGS}, where),
                            _optional_text(row, "note", where), example))
        return tuple(out)


def load_lesson(path: Path) -> Lesson:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    where = str(path)
    _keys(data, {"number", "title", "grammar"}, {"rule", "exercise", "note"}, where)
    if f"{data['number']:02d}.toml" != path.name:
        raise ContentError(f"{where}: number {data['number']} does not match the file name")
    vocab_path = path.with_name(f"{data['number']:02d}.vocab.csv")
    return Lesson(
        number=data["number"],
        title=_text(data["title"], f"{where} title"),
        grammar=_japanese(data["grammar"], f"{where} grammar"),
        rules=tuple(_rule(r, f"{where} rule #{i + 1}") for i, r in enumerate(data.get("rule", ()))),
        exercises=tuple(_exercise(e, f"{where} exercise #{i + 1}") for i, e in enumerate(data.get("exercise", ()))),
        notes=tuple(_note(n, f"{where} note #{i + 1}") for i, n in enumerate(data.get("note", ()))),
        vocab=load_vocab(vocab_path) if vocab_path.exists() else (),
    )


def load_lessons(directory: Path) -> tuple[Lesson, ...]:
    lessons = tuple(load_lesson(p) for p in sorted(directory.glob("[0-9][0-9].toml")))
    numbers = [lesson.number for lesson in lessons]
    if len(set(numbers)) != len(numbers):
        raise ContentError(f"{directory}: duplicate lesson numbers")
    return lessons


def exercises_view(lesson: Lesson) -> list[dict[str, Any]]:
    """Exercises as the page's JSON; Japanese as ruby segments."""
    out: list[dict[str, Any]] = []
    for ex in lesson.exercises:
        tr = {k: getattr(ex.tr, k) for k in LANGS}
        if isinstance(ex, Choice):
            before, after = ex.ja.split(BLANK)
            out.append({"kind": "choice", "before": furigana.segments_json(before),
                        "after": furigana.segments_json(after),
                        "options": [furigana.segments_json(o) for o in ex.options],
                        "answer": ex.options.index(ex.answer), **tr})
        else:
            out.append({"kind": "reorder", "parts": [furigana.segments_json(p) for p in ex.parts], **tr})
    return out
