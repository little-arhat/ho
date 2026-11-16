"""Anki decks of the word lists: one per lesson and per reference list, and
one with all of them as subdecks of "ho".

The note type, deck and note IDs are fixed (derived from names, not
counters), so importing a rebuilt deck updates the notes already in Anki,
keeping their review history, instead of adding copies. A note is keyed by
its group and its furigana: a word moved to another lesson, or given another
reading, becomes a new note.

The core (decks) is pure; write_package is the edge that makes an .apkg.
"""

from __future__ import annotations

import hashlib
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
from ho.romaji import romanize
from ho.words import Entry, Group, Kind

ALL_FILE = "ho-all.apkg"
FIELDS = ("Written", "Furigana", "Romaji", "EN", "RU", "UK", "NoteEN", "NoteRU", "NoteUK",
          "Example", "ExampleEN", "ExampleRU", "ExampleUK", "Audio", "ExampleAudio")


def _id(*names: str) -> int:
    """A stable 62-bit Anki ID for a name."""
    return int(hashlib.sha1("\n".join(("ho", *names)).encode()).hexdigest()[:15], 16) >> 2


def anki_furigana(text: str) -> str:
    """Our furigana notation in Anki's: Anki takes the ruby base back to the
    previous space, so each base gets a space before it (お金[かね] → お 金[かね]);
    the {{furigana:}} filter hides those spaces."""
    return "".join(s.text if s.ruby is None else f" {s.text}[{s.ruby}]" for s in furigana.parse(text))


@dataclass(frozen=True)
class Note:
    guid: str
    fields: tuple[str, ...]  # in FIELDS order
    clips: tuple[str, ...]  # audio keys the note plays
    tags: tuple[str, ...]


@dataclass(frozen=True)
class Deck:
    id: int
    name: str
    file: str  # the .apkg holding this deck alone
    group: str  # the words.Group it comes from
    notes: tuple[Note, ...]


def _note(group: Group, e: Entry, tag: str, clip: Callable[[str], str]) -> Note:
    word_clip = clip(e.ja)
    example_clip = clip(e.example.ja) if e.example else ""
    note = e.note
    ex = e.example
    fields = (
        furigana.plain(e.ja), anki_furigana(e.ja), romanize(e.ja), e.tr.en, e.tr.ru, e.tr.uk,
        note.en if note else "", note.ru if note else "", note.uk if note else "",
        anki_furigana(ex.ja) if ex else "", ex.tr.en if ex else "", ex.tr.ru if ex else "", ex.tr.uk if ex else "",
        f"[sound:{word_clip}.m4a]" if word_clip else "", f"[sound:{example_clip}.m4a]" if example_clip else "",
    )
    return Note(genanki.guid_for("ho", group.id, e.ja), fields,
                tuple(c for c in (word_clip, example_clip) if c), ("ho", tag))


def decks(groups: Iterable[Group], clip: Callable[[str], str]) -> tuple[Deck, ...]:
    """A deck for each lesson and reference list; other groups have none."""
    out = []
    for g in groups:
        if g.kind is Kind.ELSEWHERE or g.lesson is None:
            continue
        if g.kind is Kind.LESSON:
            name, file, tag = f"Lesson {g.lesson:02d} · {g.title.en}", f"ho-lesson-{g.lesson:02d}.apkg", f"lesson-{g.lesson:02d}"
        else:
            name, file, tag = f"Lesson {g.lesson:02d} · {g.title.en} (reference)", f"ho-{g.id}.apkg", g.id
        out.append(Deck(_id("deck", g.id), f"ho::{name}", file, g.id,
                        tuple(_note(g, e, tag, clip) for e in g.entries)))
    return tuple(out)


# The look of the author's own vocab deck: white on black, a textbook font
# for Japanese. The fonts are not shipped (the textbook font may not be
# redistributed): Anki finds them in a collection that already holds them as
# media (_NotoSansJP-Medium.otf, _HGSKyokashotai.ttf) and falls back to
# system fonts otherwise.
_CSS = """
@font-face { font-family: 'notosans'; src: url('_NotoSansJP-Medium.otf') format('opentype'); }
@font-face { font-family: 'textbook'; src: url('_HGSKyokashotai.ttf'); }

.card {
  font-family: 'notosans', system-ui, -apple-system, 'Helvetica Neue', 'Hiragino Sans', sans-serif;
  font-size: 22px;
  text-align: center;
  color: white;
  background-color: black;
}
div { padding-top: 5px; padding-bottom: 5px; }

.japanese { font-family: 'textbook', 'Hiragino Mincho ProN', serif; }
.word { font-size: 60px; }
.sentence { font-size: 36px; }
.romaji { font-size: 14px; color: #999; }
.english { font-size: 28px; }
.russian { font-size: 24px; color: #6cb6ff; }
.ukrainian { font-size: 24px; color: #f2c94c; }
.context { font-size: 16px; color: #aaa; }
.sentence-english { font-size: 18px; color: #bbb; }
"""

_MEANING = """
<div class="english">{{EN}}</div>
<div class="russian">{{RU}}</div>
<div class="ukrainian">{{UK}}</div>
{{#NoteEN}}<div class="context">{{NoteEN}}<br>{{NoteRU}}<br>{{NoteUK}}</div>{{/NoteEN}}
"""

_ANSWER = """
<div class="japanese word">{{furigana:Furigana}}</div>
<div class="romaji">{{Romaji}}</div>
""" + _MEANING + """
{{#Example}}
<div class="japanese sentence">{{furigana:Example}}</div>
<div class="sentence-english">{{ExampleEN}}<br>{{ExampleRU}}<br>{{ExampleUK}}</div>
{{/Example}}
"""

MODEL = genanki.Model(
    _id("model", "word"), "ho word",
    fields=[{"name": f} for f in FIELDS],
    templates=[
        {"name": "Recognition",
         "qfmt": """
<div class="japanese word">{{Written}}</div>
{{#Example}}<div class="japanese sentence">{{kanji:Example}}</div>{{/Example}}
""",
         "afmt": "{{Audio}}{{ExampleAudio}}" + _ANSWER},
        {"name": "Production", "qfmt": _MEANING, "afmt": "{{Audio}}{{ExampleAudio}}" + _ANSWER},
    ],
    css=_CSS,
)


_ZIP_TIME = (1980, 1, 1, 0, 0, 0)  # zip entries carry no build time: the same input gives the same bytes


def _zip_add(z: zipfile.ZipFile, name: str, data: bytes, compress: int) -> None:
    info = zipfile.ZipInfo(name, _ZIP_TIME)
    info.compress_type = compress
    z.writestr(info, data)


def write_package(path: Path, deck_list: Iterable[Deck], audio_dir: Path, timestamp: int) -> None:
    """An .apkg with the decks and every clip their notes play.

    `timestamp` (seconds) becomes the notes' modification time. Anki updates
    an existing note on import only when the incoming one is newer, so it
    must grow when the content does: the build passes the commit time.
    """
    anki_decks, clips = [], set()
    for d in deck_list:
        deck = genanki.Deck(d.id, d.name)
        for n in d.notes:
            deck.add_note(genanki.Note(model=MODEL, fields=list(n.fields), guid=n.guid, tags=list(n.tags)))
            clips.update(n.clips)
        anki_decks.append(deck)
    media = sorted(clips)
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "collection.anki2"
        conn = sqlite3.connect(db)
        genanki.Package(anki_decks).write_to_db(conn.cursor(), timestamp, itertools.count(timestamp * 1000))
        conn.commit()
        conn.close()
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w") as z:
            _zip_add(z, "collection.anki2", db.read_bytes(), zipfile.ZIP_DEFLATED)
            _zip_add(z, "media", json.dumps({str(i): f"{c}.m4a" for i, c in enumerate(media)}).encode(),
                     zipfile.ZIP_DEFLATED)
            for i, c in enumerate(media):
                _zip_add(z, str(i), (audio_dir / f"{c}.m4a").read_bytes(), zipfile.ZIP_STORED)
