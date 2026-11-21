from pathlib import Path

import pytest

from ho import furigana, words
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


def test_slug_is_the_word_as_written_plus_its_kana():
    assert words.slug("時[と]計[けい]") == "時計-とけい"
    assert words.slug("パソコン") == "パソコン"
    assert words.slug("すてきですね。") == "すてきですね"
    assert words.slug("～でございます") == "でございます"
    assert words.slug("人[じん]") != words.slug("人[ひと]")


@pytest.fixture(scope="module")
def pages(content):
    gs = words.groups(content.lessons, content.topics, content.kanji, content.readings)
    return {p.slug: p for p in words.word_pages(gs, content.kanji, content.readings)}


def test_a_word_in_several_lists_has_one_page(pages):
    assert [g.id for g in pages["パソコン"].groups] == ["l2", "l7"]
    assert [g.id for g in pages["肉-にく"].groups] == ["l6", "food"]


def test_a_word_page_shows_its_vocab_example_first(content, pages):
    word = next(w for lesson in content.lessons for w in lesson.vocab if w.example)
    page = pages[words.slug(word.furigana)]
    assert page.examples[0].ja == word.example.ja
    assert page.examples[0].source.href.startswith("lessons/")


def test_a_word_page_shows_its_kanji_card_example(content, pages):
    card = next(c for c in content.kanji if c.char == "計")
    w = card.words[0]
    page = pages[words.slug(w.ja)]
    assert any(x.ja == w.example.ja and x.source.href == "kanji/8a08/" for x in page.examples)


def test_a_verbatim_use_of_a_kanji_word_is_marked(pages):
    (card,) = [x for x in pages["時計-とけい"].examples if x.source.href == "kanji/6642/"]
    assert card.parts == (("これはだれの", False), ("時[と]計[けい]", True), ("ですか。", False))


def test_marking_skips_kana_words_and_inflected_uses():
    assert words._marked("もうしわけありません。", "もう") == (("もうしわけありません。", False),)
    assert words._marked("パンを食[た]べました。", "食[た]べます") == (("パンを食[た]べました。", False),)
    assert words._marked("人[ひと]と人[ひと]", "人[ひと]") == (("人[ひと]", True), ("と", False), ("人[ひと]", True))


def test_a_word_page_shows_a_few_reading_lines_with_the_word_marked(pages):
    lines = [x for x in pages["鋏-はさみ"].examples if x.source.href.startswith("reading/")]
    assert 1 <= len(lines) <= words.READING_LINES
    for x in lines:
        assert [ja for ja, mine in x.parts if mine] and all(furigana.plain(ja) == "鋏" for ja, mine in x.parts if mine)
    common = [x for x in pages["私-わたし"].examples if x.source.href.startswith("reading/")]
    assert len(common) == words.READING_LINES


def test_examples_are_not_repeated(pages):
    for p in pages.values():
        plain = [furigana.plain(x.ja) for x in p.examples]
        assert len(plain) == len(set(plain)), p.slug
