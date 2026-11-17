import sqlite3
import zipfile
from pathlib import Path

import genanki

from ho import anki
from ho.fields import Line, Text
from ho.words import Entry, Group, Kind

T = Text("e", "р", "у")


def group(id_, kind, lesson, entries):
    return Group(id_, kind, lesson, id_.upper(), "k", Text("Title", "Т", "Т"), tuple(entries))


def test_anki_furigana_puts_a_space_before_each_ruby_base_after_text():
    assert anki.anki_furigana("お金[かね]") == "お 金[かね]"
    assert anki.anki_furigana("会[かい]社[しゃ]員[いん]です") == "会[かい] 社[しゃ] 員[いん]です"
    assert anki.anki_furigana("はい") == "はい"


def test_the_existing_deck_and_note_type_are_kept():
    # These identify the deck the packages import into; changing one makes Anki add copies.
    assert (anki.MODEL_ID, anki.MODEL_NAME, anki.DECK_ID, anki.DECK_NAME) == (
        1726870001001, "Lesson Vocab", 1726870001002, "Vocab")
    assert [f["name"] for f in anki.MODEL.fields] == list(anki.FIELDS)
    assert [t["name"] for t in anki.MODEL.templates] == ["Recognition", "Production"]


def test_note_is_keyed_by_written_and_kana_and_tagged_with_its_lesson():
    e = Entry("食[た]べます", T, Text("dictionary form: 食べる", "с", "с"), Line("朝[あさ]ごはんを食[た]べます。", T))
    n = anki.note(e, 6, lambda text: "abc" if text == "食[た]べます" else "")
    fields = dict(zip(anki.FIELDS, n.fields, strict=True))
    assert n.guid == genanki.guid_for("食べます", "たべます")
    assert n.tags == ("lesson6",)
    assert fields["Kanji"] == "食べます" and fields["Kana"] == "たべます" and fields["Furigana"] == "食[た]べます"
    assert fields["Context"] == "dictionary form: 食べる" and fields["Audio"] == "[sound:abc.m4a]"
    assert fields["Sentence"] == "朝ごはんを食べます。" and fields["SentenceFurigana"] == "朝[あさ]ごはんを 食[た]べます。"
    assert fields["SentenceAudio"] == "" and n.clips == ("abc",)


def test_packages_per_lesson_and_list_then_all_with_each_word_once():
    egg, fish = Entry("卵[たまご]", T, None, None), Entry("魚[さかな]", T, None, None)
    gs = [group("l6", Kind.LESSON, 6, [egg, fish]), group("food", Kind.TOPIC, 6, [egg]),
          group("cards", Kind.ELSEWHERE, None, [Entry("夜[よる]", T, None, None)])]
    ps = anki.packages(gs, lambda t: "")
    assert [(p.file, p.group, len(p.notes)) for p in ps] == [
        ("ho-lesson-06.apkg", "l6", 2), ("ho-food.apkg", "food", 1), (anki.ALL_FILE, None, 2)]
    assert [n.fields[0] for n in ps[-1].notes] == ["卵", "魚"]


def test_package_only_adds_and_is_reproducible(tmp_path: Path):
    (tmp_path / "abc.m4a").write_bytes(b"clip")
    n = anki.note(Entry("食[た]べます", T, None, None), 1, lambda t: "abc")
    a, b = tmp_path / "a.apkg", tmp_path / "b.apkg"
    anki.write_package(a, [n], tmp_path)
    anki.write_package(b, [n], tmp_path)
    assert a.read_bytes() == b.read_bytes()
    with zipfile.ZipFile(a) as z:
        assert z.read("media") == b'{"0": "abc.m4a"}' and z.read("0") == b"clip"
        (tmp_path / "c.anki2").write_bytes(z.read("collection.anki2"))
    with sqlite3.connect(tmp_path / "c.anki2") as db:
        # the oldest mod time: Anki never takes it as an update of a note it already has
        assert db.execute("select count(*), max(mod) from notes").fetchone() == (1, anki.ADD_ONLY_TIME)
