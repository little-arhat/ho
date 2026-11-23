from pathlib import Path

import pytest

from ho import phrasebook
from ho.errors import ContentError
from ho.lessons import load_lessons
from ho.reading import load_reading, load_readings, load_scene, load_scenes
from ho.verbs import load_verbs

ROOT = Path(__file__).parent.parent
LESSONS = load_lessons(ROOT / "content/lessons")
PHRASES = phrasebook.by_ja(phrasebook.load(ROOT / "content/phrasebook.toml", load_verbs(ROOT / "content/verbs.toml")))

HEAD = 'lesson = 1\ntitle = { en = "t", ru = "т", uk = "т", es = "t" }\nscene = "s"\n'


TR = 'en = "e"\nru = "р"\nuk = "у"\nes = "s"\n'


def text(tmp_path, paragraphs, new="", name="01-t.toml", dialog=(("私[わたし]", "はい"),)):
    body = (HEAD + "".join(f'[[prose]]\nja = "{p}"\n{TR}' for p in paragraphs)
            + "".join(f'[[dialog]]\nspeaker = "{s}"\nja = "{j}"\n{TR}' for s, j in dialog) + new)
    f = tmp_path / name
    f.write_text(body)
    return f


def test_real_texts_load():
    texts = load_readings(ROOT / "content/reading", LESSONS, PHRASES)
    assert len(texts) >= 12


def test_tokens_link_to_vocabulary(tmp_path):
    r = load_reading(text(tmp_path, ["私[わたし]|は|学[がく]生[せい]|です|。"]), LESSONS, PHRASES)
    assert [t.word for t in r.prose[0].tokens] == [0, None, 1, None, None]
    assert r.words[1].lesson == 1 and r.image is None and r.lessons == (1,)


def test_inflected_surface_names_its_word(tmp_path):
    f = text(tmp_path, ["学[がっ]校[こう]|へ|行[い]きました=行[い]きます"], name="05-t.toml")
    f.write_text(f.read_text().replace("lesson = 1", "lesson = 5"))
    r = load_reading(f, LESSONS, PHRASES)
    assert r.words[1].ja == "行[い]きます"


def test_unknown_word_is_an_error(tmp_path):
    with pytest.raises(ContentError, match="not a word of lessons 1–1"):
        load_reading(text(tmp_path, ["京[きょう]都[と]|へ"]), LESSONS, PHRASES)


def test_later_lesson_word_is_an_error(tmp_path):
    with pytest.raises(ContentError, match="駅"):
        load_reading(text(tmp_path, ["駅[えき]|です"]), LESSONS, PHRASES)


def test_declared_new_word(tmp_path):
    new = '[[new]]\nja = "京[きょう]都[と]"\nen = "Kyoto"\nru = "Киото"\nuk = "Кіото"\nes = "Kioto"\n'
    r = load_reading(text(tmp_path, ["京[きょう]都[と]|です"], new), LESSONS, PHRASES)
    assert r.words[0].lesson is None


def test_unused_new_word_is_an_error(tmp_path):
    new = '[[new]]\nja = "京[きょう]都[と]"\nen = "Kyoto"\nru = "Киото"\nuk = "Кіото"\nes = "Kioto"\n'
    with pytest.raises(ContentError, match="never used"):
        load_reading(text(tmp_path, ["私[わたし]|です"], new), LESSONS, PHRASES)


def test_name_must_match_lesson(tmp_path):
    with pytest.raises(ContentError, match="match the file name"):
        load_reading(text(tmp_path, ["です"], name="02-t.toml"), LESSONS, PHRASES)


def test_dialog_speaker_is_a_tappable_word(tmp_path):
    r = load_reading(text(tmp_path, ["です"], dialog=[("先[せん]生[せい]", "学[がく]生[せい]|です|か|。")]), LESSONS, PHRASES)
    line = r.dialog[0]
    assert r.words[line.speaker.word].ja == "先[せん]生[せい]"
    assert [r.words[t.word].ja for t in line.tokens if t.word is not None] == ["学[がく]生[せい]"]
    assert line.ja == "学[がく]生[せい]ですか。"


def test_speaker_must_be_a_word(tmp_path):
    with pytest.raises(ContentError, match="dialog #1.*'あの'"):
        load_reading(text(tmp_path, ["です"], dialog=[("あの", "はい")]), LESSONS, PHRASES)


def test_both_forms_are_required(tmp_path):
    with pytest.raises(ContentError, match="dialog"):
        load_reading(text(tmp_path, ["です"], dialog=[]), LESSONS, PHRASES)


def test_lessons_are_the_ones_its_words_come_from(tmp_path):
    f = text(tmp_path, ["本[ほん]|を|読[よ]みます"], name="06-t.toml", dialog=[("友[とも]達[だち]", "はい")])
    f.write_text(f.read_text().replace("lesson = 1", "lesson = 6"))
    assert load_reading(f, LESSONS, PHRASES).lessons == (1, 2, 5, 6)  # はい is a lesson 1 word


def test_a_line_names_the_phrases_it_says(tmp_path):
    f = text(tmp_path, ["はい"], dialog=(("私[わたし]", "すみません|、|学[がく]生[せい]|です|か|。"),))
    f.write_text(f.read_text().replace('ja = "すみません', 'uses = ["すみません"]\nja = "すみません'))
    r = load_reading(f, LESSONS, PHRASES)
    assert r.dialog[0].uses == ("すみません",) and r.prose[0].uses == ()


def test_uses_must_be_a_phrase_the_line_says(tmp_path):
    f = text(tmp_path, ["はい"])
    body = f.read_text()
    f.write_text(body.replace('[[prose]]\nja = "はい"', '[[prose]]\nuses = ["ありがとうございます"]\nja = "はい"'))
    with pytest.raises(ContentError, match="does not say it"):
        load_reading(f, LESSONS, PHRASES)
    f.write_text(body.replace('[[prose]]\nja = "はい"', '[[prose]]\nuses = ["はいはい"]\nja = "はい"'))
    with pytest.raises(ContentError, match="not a phrase-book phrase"):
        load_reading(f, LESSONS, PHRASES)


def test_a_scene_has_no_lesson_and_draws_on_every_lesson(tmp_path):
    f = text(tmp_path, ["鋏[はさみ]|で|紙[かみ]|を|切[き]ります|。"], name="shop.toml")
    f.write_text(f.read_text().replace("lesson = 1\n", ""))
    s = load_scene(f, LESSONS, PHRASES)
    assert s.lesson is None and s.id == "shop" and 7 in s.lessons


def test_a_scene_name_is_lowercase_words(tmp_path):
    f = text(tmp_path, ["はい"], name="01-shop.toml")
    f.write_text(f.read_text().replace("lesson = 1\n", ""))
    with pytest.raises(ContentError, match="lowercase"):
        load_scene(f, LESSONS, PHRASES)


def test_real_scenes_load():
    load_scenes(ROOT / "content/scenes", LESSONS, PHRASES)
