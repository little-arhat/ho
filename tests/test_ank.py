import pytest

from ho.ank import convert, rows
from ho.errors import ContentError
from ho.lessons import VOCAB_COLUMNS


def test_convert_moves_base_to_kanji_run():
    assert convert("お 茶[ちゃ]を 飲[の]みます。") == "お茶[ちゃ]を飲[の]みます。"
    assert convert("会[かい]社[しゃ]") == "会[かい]社[しゃ]"


def test_convert_rejects_base_without_kanji():
    with pytest.raises(ContentError):
        convert("おちゃ[ちゃ]")


ROW = {"kanji": "飲みます", "kana": "のみます", "furigana": "飲[の]みます", "translation": "drink",
       "russian": "пить", "context": "dictionary form: 飲む", "audio": "", "example": "お 茶[ちゃ]を 飲[の]みます。",
       "example_translation": "I drink tea.", "example_audio": ""}


def test_rows_merge_translations():
    (r,) = rows([ROW], [["пити", "beber", "словарная форма: 飲む", "словникова форма: 飲む", "forma de diccionario: 飲む",
                         "Пью чай.", "П'ю чай.", "Bebo té."]])
    assert r[:7] == ["飲みます", "のみます", "飲[の]みます", "drink", "пить", "пити", "beber"]
    assert r[7:11] == ["dictionary form: 飲む", "словарная форма: 飲む", "словникова форма: 飲む", "forma de diccionario: 飲む"]
    assert r[11:] == ["お茶[ちゃ]を飲[の]みます。", "I drink tea.", "Пью чай.", "П'ю чай.", "Bebo té."]
    assert len(r) == len(VOCAB_COLUMNS)


def test_dash_drops_note():
    (r,) = rows([ROW], [["пити", "beber", "-", "", "", "Пью чай.", "П'ю чай.", "Bebo té."]])
    assert r[7:11] == ["", "", "", ""]


def test_line_count_must_match():
    with pytest.raises(ContentError, match="translation lines"):
        rows([ROW], [])
