from pathlib import Path

import pytest

from ho import phrasebook
from ho.errors import ContentError
from ho.verbs import load_verbs

CONTENT = Path(__file__).parent.parent / "content"
VERBS = load_verbs(CONTENT / "verbs.toml")
PB = phrasebook.load(CONTENT / "phrasebook.toml", VERBS)
VIEW = phrasebook.view(PB, lambda text: "")


def find(ja):
    i = next(i for i, p in enumerate(PB.phrases) if p.ja == ja)
    return VIEW["phrases"][i]


def test_counts():
    assert len(PB.topics) == 11
    assert len(PB.phrases) == 545


def test_unknown_topic(tmp_path):
    f = tmp_path / "pb.toml"
    f.write_text('[[topic]]\nid="a"\njp="あ"\nen="A"\ncolor="#000000"\ncolor_dark="#ffffff"\n'
                 '[[phrase]]\ntopic="b"\nsection="s"\nkind="say"\nja="はい"\nen="yes"\nru="да"\nuk="так"\n')
    with pytest.raises(ContentError, match="phrase #1 'はい'.*unknown topic 'b'"):
        phrasebook.load(f, VERBS)


def test_bad_furigana_names_entry(tmp_path):
    f = tmp_path / "pb.toml"
    f.write_text('[[topic]]\nid="a"\njp="あ"\nen="A"\ncolor="#000000"\ncolor_dark="#ffffff"\n'
                 '[[phrase]]\ntopic="a"\nsection="s"\nkind="say"\nja="お[お]"\nen="o"\nru="о"\nuk="о"\n')
    with pytest.raises(ContentError, match="phrase #1"):
        phrasebook.load(f, VERBS)


def test_search_fields():
    p = find("お手洗[てあら]いはどこですか")
    assert "туалет" in p["search"].lower()
    assert "お手洗いはどこですか" in p["search"]
    assert "おてあらいはどこですか" in p["search"]
    assert p["ro"] == "otearai wa doko desu ka"
    assert p["ja"][:2] == [["お"], ["手洗", "てあら"]]


def test_verb_from_answer_is_attached():
    p = find("お手伝[てつだ]いしましょうか")
    names = [VIEW["verbs"][i]["lookup"] for i in p["verbs"]]
    assert "助かる" in names


def test_verb_view():
    v = next(v for v in VIEW["verbs"] if v["lookup"] == "予約する")
    assert v["wiktionary"] == "予約"
    assert len(v["forms"]) == 20
    assert v["forms"][1]["romaji"] == "yoyakushimasu"


def test_bad_colour(tmp_path):
    f = tmp_path / "pb.toml"
    f.write_text('[[topic]]\nid="a"\njp="あ"\nen="A"\ncolor="red;x"\ncolor_dark="#fff000"\n[[phrase]]\n'
                 'topic="a"\nsection="s"\nkind="tip"\nnote="n"\n')
    with pytest.raises(ContentError, match="colours"):
        phrasebook.load(f, VERBS)


def test_misspelled_table(tmp_path):
    f = tmp_path / "pb.toml"
    f.write_text('[[topic]]\nid="a"\njp="あ"\nen="A"\ncolor="#000000"\ncolor_dark="#ffffff"\n[[phrases]]\n'
                 'topic="a"\nsection="s"\nkind="tip"\nnote="n"\n')
    with pytest.raises(ContentError, match="expected"):
        phrasebook.load(f, VERBS)
