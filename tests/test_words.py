from pathlib import Path

import pytest

from ho import words
from ho.build import load_content
from ho.errors import ContentError
from ho.kanji import fold
from ho.lessons import VOCAB_COLUMNS

ROOT = Path(__file__).parent.parent
HEADER = ",".join(VOCAB_COLUMNS) + "\n"


@pytest.fixture(scope="module")
def content():
    return load_content(ROOT / "content", ROOT / "ref/kanji.json", ROOT / "audio")


def test_topic_follows_its_lesson(content):
    ids = [g.id for g in words.groups(content.lessons, content.topics, content.kanji, content.readings)]
    assert ids.index("food") == ids.index("l6") + 1


def test_card_and_reading_words_are_listed_once_and_not_after_lessons(content):
    gs = words.groups(content.lessons, content.topics, content.kanji, content.readings)
    by_id = {g.id: g for g in gs}
    lesson_keys = {e.ja for g in gs if g.id.startswith("l") for e in g.entries}
    later = [e.ja for g in gs if g.id in ("cards", "reading") for e in g.entries]
    assert len(later) == len(set(later))
    assert not set(later) & lesson_keys
    assert "真[ま]夜[よ]中[なか]" in {e.ja for e in by_id["cards"].entries}
    assert "年[ねん]賀[が]状[じょう]" in {e.ja for e in by_id["reading"].entries}


def test_topic_keeps_words_a_lesson_also_has(content):
    food = {e.ja for g in words.groups(content.lessons, content.topics, (), ()) if g.id == "food" for e in g.entries}
    assert "肉[にく]" in food


def test_search_index_finds_by_writing_kana_romaji_and_meaning(content):
    (eat,) = [e for g in words.groups(content.lessons, (), (), ()) for e in g.entries if e.ja == "食[た]べます"]
    tokens = words.search_index(eat).split(" ")
    for q in ["食べます", "たべます", "tabemasu", "eat", "есть", "їсти"]:
        assert fold(q) in tokens, q


def test_topic_needs_its_word_list(tmp_path):
    (tmp_path / "x.toml").write_text('title = { en = "X", ru = "Х", uk = "Х", es = "X" }\nlesson = 1\n')
    with pytest.raises(ContentError, match="x.csv"):
        words.load_topics(tmp_path, [1])


def test_word_list_needs_its_topic(tmp_path):
    (tmp_path / "x.csv").write_text(HEADER)
    with pytest.raises(ContentError, match="without a .toml"):
        words.load_topics(tmp_path, [1])


def test_topic_lesson_must_exist(tmp_path):
    (tmp_path / "x.toml").write_text('title = { en = "X", ru = "Х", uk = "Х", es = "X" }\nlesson = 9\n')
    (tmp_path / "x.csv").write_text(HEADER)
    with pytest.raises(ContentError, match="lesson 9"):
        words.load_topics(tmp_path, [1])
