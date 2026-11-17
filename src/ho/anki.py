"""Anki packages of the word lists, made for the author's existing Anki deck
"Vocab": the same note type ("Lesson Vocab"), deck and note IDs as the tool
that built it, so a package imports into that deck and a word already there
is recognised as the same note, not added twice. A note is keyed by the word
as written and its kana (genanki.guid_for(written, kana)).

Packages only add words. Each note is stamped with the oldest modification
time, and Anki updates an existing note on import only from a newer one
(its default, "Update existing notes: if newer"), so the notes already in the
collection keep their own audio, sentences and edits. The cost: a correction
here never reaches a note that is already in Anki.

There is one package per lesson and per reference list, and one with all of
them. The core (packages) is pure; write_package is the edge that makes an .apkg.
"""

from __future__ import annotations

import itertools
import json
import sqlite3
import tempfile
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import genanki

from ho import furigana
from ho.words import Entry, Group, Kind

# The existing deck's note type and deck: these must not change.
MODEL_ID = 1726870001001
MODEL_NAME = "Lesson Vocab"
DECK_ID = 1726870001002
DECK_NAME = "Vocab"
FIELDS = ("Kanji", "Furigana", "Kana", "English", "Russian", "Context", "Pos", "Audio",
          "Sentence", "SentenceFurigana", "SentenceKana", "SentenceEnglish", "SentenceAudio")
ADD_ONLY_TIME = 1  # seconds since the epoch: older than any note in a collection, so never an update

ALL_FILE = "ho-all.apkg"


def anki_furigana(text: str) -> str:
    """Our furigana notation in Anki's: Anki takes the ruby base back to the
    previous space, so each base after other text gets a space before it
    (お金[かね] → お 金[かね]); the {{furigana:}} filter hides those spaces."""
    return "".join(s.text if s.ruby is None else f" {s.text}[{s.ruby}]"
                   for s in furigana.parse(text)).lstrip(" ")


@dataclass(frozen=True)
class Note:
    guid: str
    fields: tuple[str, ...]  # in FIELDS order
    clips: tuple[str, ...]  # audio keys the note plays
    tags: tuple[str, ...]


@dataclass(frozen=True)
class Package:
    file: str
    group: str | None  # the words.Group it holds; None for the one with all
    notes: tuple[Note, ...]


def _sound(clip: str) -> str:
    return f"[sound:{clip}.m4a]" if clip else ""


def note(e: Entry, lesson: int, clip: Callable[[str], str]) -> Note:
    written, kana = furigana.plain(e.ja), furigana.reading(e.ja)
    ex = e.example
    word_clip, example_clip = clip(e.ja), clip(ex.ja) if ex else ""
    fields = (
        written, anki_furigana(e.ja), kana, e.tr.en, e.tr.ru, e.note.en if e.note else "", "", _sound(word_clip),
        furigana.plain(ex.ja) if ex else "", anki_furigana(ex.ja) if ex else "",
        furigana.reading(ex.ja) if ex else "", ex.tr.en if ex else "", _sound(example_clip),
    )
    return Note(genanki.guid_for(written, kana), fields, tuple(c for c in (word_clip, example_clip) if c),
                (f"lesson{lesson}",))


def _unique(notes: Iterable[Note]) -> tuple[Note, ...]:
    """One note per word: a word in two lists (卵 in lesson 6 and the food list) is one note, the first."""
    first: dict[str, Note] = {}
    for n in notes:
        first.setdefault(n.guid, n)
    return tuple(first.values())


def packages(groups: Iterable[Group], clip: Callable[[str], str]) -> tuple[Package, ...]:
    """A package for each lesson and reference list (other groups have none), then one with them all."""
    out = []
    for g in groups:
        if g.kind is Kind.ELSEWHERE or g.lesson is None:
            continue
        file = f"ho-lesson-{g.lesson:02d}.apkg" if g.kind is Kind.LESSON else f"ho-{g.id}.apkg"
        out.append(Package(file, g.id, _unique(note(e, g.lesson, clip) for e in g.entries)))
    return (*out, Package(ALL_FILE, None, _unique(n for p in out for n in p.notes)))


# The look of the author's own vocab deck: white on black, a textbook font
# for Japanese. The fonts are not shipped (the textbook font may not be
# redistributed): Anki finds them in a collection that already holds them as
# media (_NotoSansJP-Medium.otf, _HGSKyokashotai.ttf) and falls back to
# system fonts otherwise.
_CSS = """
@font-face { font-family: 'notosans'; src: url('_NotoSansJP-Medium.otf') format('opentype'); }
@font-face { font-family: 'textbook'; src: url('_HGSKyokashotai.ttf'); }

.card {
  font-family: 'notosans', 'Hiragino Sans', sans-serif;
  font-size: 22px;
  text-align: center;
  color: white;
  background-color: black;
}
div { padding-top: 5px; padding-bottom: 5px; }

.japanese { font-family: 'textbook', 'Hiragino Mincho ProN', serif; }
.word { font-size: 60px; }
.sentence { font-size: 36px; }
.pos { font-size: 14px; color: #999; }
.english { font-size: 28px; }
.russian { font-size: 24px; color: #6cb6ff; }
.context { font-size: 16px; color: #aaa; }
.sentence-english { font-size: 18px; color: #bbb; }
"""

_MEANING = """
<div class="english">{{English}}</div>
<div class="russian">{{Russian}}</div>
{{#Context}}<div class="context">{{Context}}</div>{{/Context}}
"""

_WORD_ANSWER = """
<div class="japanese word">{{furigana:Furigana}}</div>
<div class="pos">{{Pos}}</div>
<div class="english">{{English}}</div>
<div class="russian">{{Russian}}</div>
{{#Context}}<div class="context">{{Context}}</div>{{/Context}}
{{#SentenceFurigana}}
<div class="japanese sentence">{{furigana:SentenceFurigana}}</div>
<div class="sentence-english">{{SentenceEnglish}}</div>
{{/SentenceFurigana}}
"""

MODEL = genanki.Model(
    MODEL_ID,
    MODEL_NAME,
    fields=[{"name": f} for f in FIELDS],
    templates=[
        {"name": "Recognition",
         "qfmt": """
<div class="japanese word">{{Kanji}}</div>
<div class="pos">{{Pos}}</div>
{{#Sentence}}<div class="japanese sentence">{{Sentence}}</div>{{/Sentence}}
""",
         "afmt": "{{Audio}}{{SentenceAudio}}" + _WORD_ANSWER},
        {"name": "Production", "qfmt": _MEANING, "afmt": "{{Audio}}{{SentenceAudio}}" + _WORD_ANSWER},
    ],
    css=_CSS,
)


_ZIP_TIME = (1980, 1, 1, 0, 0, 0)  # zip entries carry no build time: the same input gives the same bytes


def _zip_add(z: zipfile.ZipFile, name: str, data: bytes, compress: int) -> None:
    info = zipfile.ZipInfo(name, _ZIP_TIME)
    info.compress_type = compress
    z.writestr(info, data)


def write_package(path: Path, notes: Iterable[Note], audio_dir: Path) -> None:
    """An .apkg of the notes in the deck, with every clip they play."""
    deck = genanki.Deck(DECK_ID, DECK_NAME)
    clips: set[str] = set()
    for n in notes:
        deck.add_note(genanki.Note(model=MODEL, fields=list(n.fields), guid=n.guid, tags=list(n.tags)))
        clips.update(n.clips)
    media = sorted(clips)
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "collection.anki2"
        conn = sqlite3.connect(db)
        # IDs from a counter far from Anki's own millisecond-time IDs; mod time ADD_ONLY_TIME (see above)
        genanki.Package(deck).write_to_db(conn.cursor(), ADD_ONLY_TIME, itertools.count(DECK_ID * 1000))
        conn.commit()
        conn.close()
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w") as z:
            _zip_add(z, "collection.anki2", db.read_bytes(), zipfile.ZIP_DEFLATED)
            _zip_add(z, "media", json.dumps({str(i): f"{c}.m4a" for i, c in enumerate(media)}).encode(),
                     zipfile.ZIP_DEFLATED)
            for i, c in enumerate(media):
                _zip_add(z, str(i), (audio_dir / f"{c}.m4a").read_bytes(), zipfile.ZIP_STORED)
