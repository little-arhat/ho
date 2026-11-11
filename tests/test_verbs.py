from pathlib import Path

import pytest

from ho.verbs import conjugate, find_verbs, load_verbs

VERBS = load_verbs(Path(__file__).parent.parent / "content/verbs.toml")
BY_DICT = {v.dict: v for v in VERBS}


def forms(dict_form):
    return {f.label.split()[0]: f.ja for f in conjugate(BY_DICT[dict_form])}


def test_lexicon_loads():
    assert len(VERBS) == 98
    assert all(len(conjugate(v)) == 20 for v in VERBS)


@pytest.mark.parametrize(("verb", "label", "expected"), [
    ("行[い]く", "て", "行[い]って"),
    ("行[い]く", "た", "行[い]った"),
    ("書[か]く", "て", "書[か]いて"),
    ("来[く]る", "ます", "来[き]ます"),
    ("来[く]る", "ない", "来[こ]ない"),
    ("食[た]べる", "可能", "食[た]べられる"),
    ("話[はな]す", "て", "話[はな]して"),
    ("予約[よやく]する", "可能", "予約[よやく]できる"),
    ("待[ま]つ", "ます", "待[ま]ちます"),
    ("飲[の]む", "た", "飲[の]んだ"),
    ("急[いそ]ぐ", "て", "急[いそ]いで"),
    ("買[か]う", "ない", "買[か]わない"),
])
def test_conjugate(verb, label, expected):
    assert forms(verb)[label] == expected


def test_meanings():
    rows = {f.label.split()[0]: f.meaning for f in conjugate(BY_DICT["食[た]べる"])}
    assert rows["辞書形"] == "to eat"
    assert rows["受身"] == "be eaten"


def test_find_verbs():
    assert [v.dict for v in find_verbs(["乗[の]り換[か]えはどこですか"], VERBS)] == ["乗[の]る", "乗[の]り換[か]える"]
    assert [v.dict for v in find_verbs(["予約[よやく]したいです"], VERBS)] == ["予約[よやく]する"]
    assert find_verbs(["予約[よやく]は"], VERBS) == ()
    assert find_verbs(["乗[の]"], VERBS) == ()
