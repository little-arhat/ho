import pytest

from ho.romaji import romanize


@pytest.mark.parametrize("text, expected", [
    ("私[わたし]は学[がく]生[せい]です。", "watashi wa gakusei desu."),
    ("駅[えき]へ行[い]きます。", "eki e ikimasu."),
    ("コーヒーを飲[の]みませんか。", "kōhī o nomimasen ka."),
    ("ちょっと待[ま]ってください。", "chotto matte kudasai."),
    ("学[がく]生[せい]でした", "gakusei deshita"),
    ("高[たか]くないです", "takakunai desu"),
    ("今日[きょう]はいい天[てん]気[き]ですね", "kyou wa ii tenki desu ne"),
    ("すみませんが…", "sumimasen ga…"),
    ("ここで作[さ]業[ぎょう]していい？", "koko de sagyou shite ii?"),
    ("「どうぞお先[さき]に。」", "\"douzo osaki ni.\""),
    ("Wi-Fiはありますか", "Wi-Fi wa arimasu ka"),
    ("〇〇と申[もう]します", "〇〇 to moushimasu"),
    ("", ""),
])
def test_romanize(text, expected):
    assert romanize(text) == expected


def test_sounds_come_from_our_furigana():
    # MeCab reads 何 here as なん; our furigana says なに, and that is what shows.
    assert romanize("何[なに]ですか") == "nani desu ka"


def test_ruby_run_split_only_when_readings_agree():
    assert romanize("一番好[いちばんす]き") == "ichiban suki"
    # A reading MeCab disagrees with keeps the run whole rather than guess a cut.
    assert romanize("一番好[ひとばんす]き") == "hitobansuki"
