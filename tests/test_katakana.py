import re
from pathlib import Path

import pytest

from ho.errors import ContentError
from ho.katakana import answers, load

WORDS = load(Path(__file__).parent.parent / "content/katakana.toml")


def accepts(alts, s):
    return re.fullmatch("".join("(?:" + "|".join(map(re.escape, a)) + ")" for a in alts), s) is not None


def test_load():
    assert len(WORDS) == 198
    assert all(w.en and w.ru and w.uk for w in WORDS)


@pytest.mark.parametrize("s", ["koohii", "ko-hi-", "kōhī", "kôhî"])
def test_long_vowels(s):
    assert accepts(answers("コーヒー").exact, s)


def test_missing_long_vowel_is_near():
    a = answers("コーヒー")
    assert not accepts(a.exact, "kohi")
    assert accepts(a.near_long, "kohi")


def test_double_consonant():
    a = answers("スパゲッティ")
    assert accepts(a.exact, "supagetti")
    assert accepts(a.exact, "supagetthi")
    assert not accepts(a.exact, "supageti")
    assert accepts(a.near_gem, "supageti")


@pytest.mark.parametrize("s", ["wain", "wainn", "wain'"])
def test_n(s):
    assert accepts(answers("ワイン").exact, s)


def test_n_before_p_may_be_m():
    a = answers("コンピューター")
    assert accepts(a.exact, "konpyuutaa")
    assert accepts(a.exact, "kompyuutaa")


def test_tch():
    a = answers("マッチ")
    assert accepts(a.exact, "matchi")
    assert accepts(a.exact, "macchi")


def test_forms():
    a = answers("コーヒー")
    assert (a.typed, a.macron) == ("koohii", "kōhī")
    assert answers("パンヤ").typed == "pan'ya"


@pytest.mark.parametrize("bad", ["ヰスキー", "アッ", "ーア", "ッン", "ッア", "ンー", "ッッカ"])
def test_rejects_undrillable(bad):
    with pytest.raises(ContentError):
        answers(bad)


def test_unknown_table_rejected(tmp_path):
    f = tmp_path / "k.toml"
    f.write_text('[[words]]\nja="パン"\nen="bread"\nru="хлеб"\nuk="хліб"\n')
    with pytest.raises(ContentError, match="only \\[\\[word\\]\\]"):
        load(f)
