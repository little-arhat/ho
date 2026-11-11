import pytest

from ho.errors import ContentError
from ho.furigana import Segment, parse, plain, reading, segments_json


def test_parse_kanji_run():
    assert parse("お願[ねが]いします") == (
        Segment("お", None),
        Segment("願", "ねが"),
        Segment("いします", None),
    )


def test_multi_run():
    text = "日本語[にほんご]は少[すこ]し"
    assert plain(text) == "日本語は少し"
    assert reading(text) == "にほんごはすこし"


def test_digits_not_base():
    assert parse("10時[じ]") == (Segment("10", None), Segment("時", "じ"))


def test_consecutive_bases():
    assert parse("会[かい]社[しゃ]") == (Segment("会", "かい"), Segment("社", "しゃ"))


def test_katakana_reading_and_long_mark():
    assert parse("珈琲[コーヒー]") == (Segment("珈琲", "コーヒー"),)


def test_no_ruby():
    assert parse("すみません") == (Segment("すみません", None),)
    assert parse("") == ()


@pytest.mark.parametrize("bad", ["お[お]", "願[]", "願[ネガa]", "願[ねが", "ねが]", "[ねが]"])
def test_errors(bad):
    with pytest.raises(ContentError):
        parse(bad)


def test_segments_json():
    assert segments_json("お茶[ちゃ]") == [["お"], ["茶", "ちゃ"]]
