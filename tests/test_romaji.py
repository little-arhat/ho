import pytest

from ho.romaji import romanize, speech


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


@pytest.mark.parametrize("text, expected", [
    ("私[わたし]は学[がく]生[せい]です。", "わたしわ がくせいです。"),
    ("駅[えき]へ行[い]きます。", "えきえ いきます。"),
    ("コーヒーを飲[の]みませんか。", "コーヒーを のみませんか。"),
    ("今日[きょう]はいい天[てん]気[き]ですね", "きょうわ いい てんきですね"),
])
def test_speech_is_our_reading_in_phrases(text, expected):
    assert speech(text) == expected


def test_audio_accepts_engine_spelling_and_rejects_misreading():
    from ho.audio import agrees
    assert agrees("私[わたし]は学[がく]生[せい]です。", "ワタシワガクセエデス")
    assert agrees("コーヒーを飲[の]みませんか。", "コオヒイオノミマセンカ")
    assert agrees("１，０００円[えん]です", "センエンデス")  # digits: any sounds
    assert not agrees("何[なに]をしますか", "ナンオシマスカ")
    assert agrees("サーモン · 鮭[さけ] · イクラ", "サアモンサケイクラ")  # punctuation never splits a vowel pair
    assert agrees("ICカードで", "アイシイカアドデ")  # Latin: any sounds


def test_greetings_say_wa():
    assert romanize("こんにちは") == "konnichiwa"
    assert speech("こんばんは") == "こんばんわ"
    assert romanize("母[はは]は") == "haha wa"  # only the particle changes
