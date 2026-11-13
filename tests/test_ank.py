import pytest

from ho.ank import convert, rows
from ho.errors import ContentError


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
    (r,) = rows([ROW], [["пити", "словарная форма: 飲む", "словникова форма: 飲む", "Пью чай.", "П'ю чай."]])
    assert r[:6] == ["飲みます", "のみます", "飲[の]みます", "drink", "пить", "пити"]
    assert r[9:] == ["お茶[ちゃ]を飲[の]みます。", "I drink tea.", "Пью чай.", "П'ю чай."]


def test_dash_drops_note():
    (r,) = rows([ROW], [["пити", "-", "", "Пью чай.", "П'ю чай."]])
    assert r[6:9] == ["", "", ""]


def test_line_count_must_match():
    with pytest.raises(ContentError, match="translation lines"):
        rows([ROW], [])
