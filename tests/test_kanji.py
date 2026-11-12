from pathlib import Path

import pytest

from ho import kanji
from ho.errors import ContentError
from ho.fields import Text
from ho.refdata import Kanji, load

ROOT = Path(__file__).parent.parent
REF = load(ROOT / "ref/kanji.json")


def card_file(tmp_path, body):
    f = tmp_path / "k.toml"
    f.write_text(body)
    return f


ONE = '''
[[kanji]]
char = "生"
number = 21
level = 5
readings = ["い-きます", "(なま)", "セイ"]
meaning = { en = "life", ru = "жизнь", uk = "життя" }

[[kanji.word]]
ja = "学[がく]生[せい]"
tr = { en = "student", ru = "студент", uk = "студент" }
example = { ja = "わたしは学[がく]生[せい]です。", en = "I am a student.", ru = "Я студент.", uk = "Я студент." }
'''


def test_parse_reading():
    assert kanji.parse_reading("う-まれます", "w") == kanji.Reading("う-まれます", False, False, False)
    assert kanji.parse_reading("(ジツ)", "w") == kanji.Reading("ジツ", True, True, False)
    assert kanji.parse_reading("なん*", "w") == kanji.Reading("なん", False, False, True)
    with pytest.raises(ContentError, match="hiragana"):
        kanji.parse_reading("ニち", "w")


def test_load_card(tmp_path):
    (card,) = kanji.load_file(card_file(tmp_path, ONE))
    assert card.char == "生" and card.number == 21
    assert [r.kana for r in card.readings] == ["い-きます", "なま", "セイ"]
    assert card.words[0].example.tr.en == "I am a student."


def test_word_must_contain_the_kanji(tmp_path):
    body = ONE.replace('ja = "学[がく]生[せい]"', 'ja = "学[がっ]校[こう]"')
    with pytest.raises(ContentError, match="must contain 生"):
        kanji.load_file(card_file(tmp_path, body))


def test_number_and_level_together(tmp_path):
    with pytest.raises(ContentError, match="number and level"):
        kanji.load_file(card_file(tmp_path, ONE.replace("level = 5\n", "")))


def test_check_rejects_reading_kanjidic_lacks(tmp_path):
    cards = kanji.load_file(card_file(tmp_path, ONE.replace('"セイ"', '"ゼイ"')))
    with pytest.raises(ContentError, match="ゼイ is not in KANJIDIC2"):
        kanji.check(cards, REF, [])


def test_check_lets_special_readings_through(tmp_path):
    cards = kanji.load_file(card_file(tmp_path, ONE.replace('"セイ"', '"ゼイ*"')))
    kanji.check(cards, REF, [])


def test_check_requires_cards(tmp_path):
    cards = kanji.load_file(card_file(tmp_path, ONE))
    with pytest.raises(ContentError, match="no kanji card for 学"):
        kanji.check(cards, REF, ["生", "学"])


def test_real_cards_cover_book_and_lessons():
    from ho.lessons import load_lessons
    cards = kanji.load_cards(ROOT / "content/kanji")
    lessons = load_lessons(ROOT / "content/lessons")
    kanji.check(cards, REF, [c.char for c in cards if c.number] + kanji.lesson_kanji(lessons))
    assert [c.number for c in cards[:3]] == [1, 2, 3]


def test_kanji_in_skips_marks():
    assert kanji.kanji_in("時[とき]々[どき]") == ["時"]


def test_stroke_frames():
    assert kanji.stroke_frames(("a", "b", "c")) == (("a",), ("a", "b"), ("a", "b", "c"))


def item(written, reading):
    return kanji.DrillItem(f"{written}", written, reading, Text("x", "х", "х"), "1")


def test_distractors_never_share_spelling_or_reading():
    items = (item("何", "なに"), item("何", "なん"), item("名", "な"), item("日本", "にほん"), item("二本", "にほん"))
    assert kanji.distractors(items, 0, "reading") == [2, 3]  # 何 is なん too; 二本 would show にほん a second time
    assert 4 not in kanji.distractors(items, 3, "written")  # 二本 is also にほん


def test_distractors_prefer_shared_kanji():
    items = (item("学生", "がくせい"), item("天気", "てんき"), item("学校", "がっこう"))
    assert kanji.distractors(items, 0, "written")[0] == 2


def test_refdata_kanji_has_strokes():
    k = REF["日"]
    assert isinstance(k, Kanji) and len(k.strokes) == 4 and "ニチ" in k.on
