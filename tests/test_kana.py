from ho.kana import kata_to_hira, romaji


def test_kata_to_hira():
    assert kata_to_hira("コーヒー") == "こーひー"


def test_romaji():
    assert romaji("がっこう") == "gakkou"
    assert romaji("まっちゃ") == "matcha"
    assert romaji("しゃしん") == "shashin"
    assert romaji("きょう") == "kyou"
    assert romaji("じゃあ") == "jaa"
    assert romaji("コーヒー") == "kōhī"
    assert romaji("ー") == ""
    assert romaji("をください") == "okudasai"


def test_romaji_loanword_sounds():
    assert romaji("チェックイン") == "chekkuin"
    assert romaji("パーティー") == "pātī"
    assert romaji("ファイル") == "fairu"
    assert romaji("ウィーン") == "wīn"
    assert romaji("タトゥー") == "tatū"
    assert romaji("ヴァイオリン") == "vaiorin"
    assert romaji("ディズニー") == "dizunī"
