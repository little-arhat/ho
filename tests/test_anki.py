import sqlite3
import zipfile
from pathlib import Path

from ho import anki
from ho.fields import Line, Text
from ho.words import Entry, Group, Kind

T = Text("e", "р", "у")


def group(id_, kind, lesson, entries):
    return Group(id_, kind, lesson, id_.upper(), "k", Text("Title", "Т", "Т"), tuple(entries))


def test_anki_furigana_puts_a_space_before_each_ruby_base():
    assert anki.anki_furigana("お金[かね]") == "お 金[かね]"
    assert anki.anki_furigana("会[かい]社[しゃ]員[いん]です") == " 会[かい] 社[しゃ] 員[いん]です"
    assert anki.anki_furigana("はい") == "はい"


def test_decks_for_lessons_and_topics_only():
    e = Entry("食[た]べます", T, None, Line("朝[あさ]食[た]べます。", T))
    gs = [group("l6", Kind.LESSON, 6, [e]), group("food", Kind.TOPIC, 6, [e]), group("cards", Kind.ELSEWHERE, None, [e])]
    ds = anki.decks(gs, lambda text: "abc" if text == "食[た]べます" else "")
    assert [(d.group, d.file, d.name) for d in ds] == [
        ("l6", "ho-lesson-06.apkg", "ho::Lesson 06 · Title"),
        ("food", "ho-food.apkg", "ho::Lesson 06 · Title (reference)"),
    ]
    note = ds[0].notes[0]
    fields = dict(zip(anki.FIELDS, note.fields, strict=True))
    assert fields["Written"] == "食べます" and fields["Romaji"] == "tabemasu"
    assert fields["Audio"] == "[sound:abc.m4a]" and fields["ExampleAudio"] == ""
    assert note.clips == ("abc",)
    # the same word in another list is another note; ids do not depend on order
    assert ds[0].notes[0].guid != ds[1].notes[0].guid
    assert anki.decks(gs[::-1], lambda t: "")[0].id == ds[1].id


def test_package_holds_notes_and_media_and_is_reproducible(tmp_path: Path):
    (tmp_path / "abc.m4a").write_bytes(b"clip")
    e = Entry("食[た]べます", T, None, None)
    (d,) = anki.decks([group("l1", Kind.LESSON, 1, [e])], lambda t: "abc")
    a, b = tmp_path / "a.apkg", tmp_path / "b.apkg"
    anki.write_package(a, [d], tmp_path, 1_700_000_000)
    anki.write_package(b, [d], tmp_path, 1_700_000_000)
    assert a.read_bytes() == b.read_bytes()
    with zipfile.ZipFile(a) as z:
        assert z.read("media") == b'{"0": "abc.m4a"}' and z.read("0") == b"clip"
        (tmp_path / "c.anki2").write_bytes(z.read("collection.anki2"))
    with sqlite3.connect(tmp_path / "c.anki2") as db:
        assert db.execute("select count(*), max(mod) from notes").fetchone() == (1, 1_700_000_000)
