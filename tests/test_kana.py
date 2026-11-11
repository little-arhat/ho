from ho.kana import kata_to_hira, romaji


def test_kata_to_hira():
    assert kata_to_hira("コーヒー") == "こーひー"


def test_romaji():
    assert romaji("がっこう") == "gakkou"
    assert romaji("まっちゃ") == "matcha"
    assert romaji("しゃしん") == "shashin"
    assert romaji("きょう") == "kyou"
    assert romaji("じゃあ") == "jaa"
    assert romaji("コーヒー") == "kohi"
    assert romaji("をください") == "okudasai"
