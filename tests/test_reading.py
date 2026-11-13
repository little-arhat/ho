from pathlib import Path

import pytest

from ho.errors import ContentError
from ho.lessons import load_lessons
from ho.reading import load_reading, load_readings

ROOT = Path(__file__).parent.parent
LESSONS = load_lessons(ROOT / "content/lessons")

HEAD = 'lesson = 1\ntitle = { en = "t", ru = "т", uk = "т" }\nscene = "s"\n'


def text(tmp_path, paragraphs, new="", name="01-t.toml"):
    body = HEAD + "".join(f'[[paragraph]]\nja = "{p}"\nen = "e"\nru = "р"\nuk = "у"\n' for p in paragraphs) + new
    f = tmp_path / name
    f.write_text(body)
    return f


def test_real_texts_load():
    texts = load_readings(ROOT / "content/reading", LESSONS)
    assert len(texts) >= 12


def test_tokens_link_to_vocabulary(tmp_path):
    r = load_reading(text(tmp_path, ["私[わたし]|は|学[がく]生[せい]|です|。"]), LESSONS)
    assert [t.word for t in r.paragraphs[0].tokens] == [0, None, 1, None, None]
    assert r.words[1].lesson == 1 and r.image is None


def test_inflected_surface_names_its_word(tmp_path):
    f = text(tmp_path, ["学[がっ]校[こう]|へ|行[い]きました=行[い]きます"], name="05-t.toml")
    f.write_text(f.read_text().replace("lesson = 1", "lesson = 5"))
    r = load_reading(f, LESSONS)
    assert r.words[1].ja == "行[い]きます"


def test_unknown_word_is_an_error(tmp_path):
    with pytest.raises(ContentError, match="not a word of lessons 1–1"):
        load_reading(text(tmp_path, ["京[きょう]都[と]|へ"]), LESSONS)


def test_later_lesson_word_is_an_error(tmp_path):
    with pytest.raises(ContentError, match="駅"):
        load_reading(text(tmp_path, ["駅[えき]|です"]), LESSONS)


def test_declared_new_word(tmp_path):
    new = '[[new]]\nja = "京[きょう]都[と]"\nen = "Kyoto"\nru = "Киото"\nuk = "Кіото"\n'
    r = load_reading(text(tmp_path, ["京[きょう]都[と]|です"], new), LESSONS)
    assert r.words[0].lesson is None


def test_unused_new_word_is_an_error(tmp_path):
    new = '[[new]]\nja = "京[きょう]都[と]"\nen = "Kyoto"\nru = "Киото"\nuk = "Кіото"\n'
    with pytest.raises(ContentError, match="never used"):
        load_reading(text(tmp_path, ["私[わたし]|です"], new), LESSONS)


def test_name_must_match_lesson(tmp_path):
    with pytest.raises(ContentError, match="match the file name"):
        load_reading(text(tmp_path, ["です"], name="02-t.toml"), LESSONS)
