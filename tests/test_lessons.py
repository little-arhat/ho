from pathlib import Path

import pytest

from ho.errors import ContentError
from ho.lessons import VOCAB_COLUMNS, exercises_view, load_lesson, load_lessons, load_vocab

LESSONS = Path(__file__).parent.parent / "content/lessons"
HEAD = 'number = 9\ntitle_ja = "テスト"\ntitle = { en = "t", ru = "т", uk = "т" }\n'


def write(tmp_path, body, name="09.toml"):
    f = tmp_path / name
    f.write_text(HEAD + body)
    return f


def test_real_lessons_load():
    lessons = load_lessons(LESSONS)
    assert lessons and lessons[0].number == 1
    assert all(lesson.rules and lesson.vocab for lesson in lessons)


def test_choice_view(tmp_path):
    f = write(tmp_path, '''
[[exercise]]
kind = "choice"
ja = "私[わたし]＿学[がく]生[せい]です。"
options = ["は", "の"]
answer = "の"
en = "e"
ru = "р"
uk = "у"
''')
    (x,) = exercises_view(load_lesson(f))
    assert x["before"] == [["私", "わたし"]]
    assert x["answer"] == 1


@pytest.mark.parametrize(("body", "message"), [
    ('[[exercise]]\nkind="choice"\nja="はい"\noptions=["a","b"]\nanswer="a"\nen="e"\nru="р"\nuk="у"\n', "exactly one"),
    ('[[exercise]]\nkind="choice"\nja="＿です"\noptions=["a","b"]\nanswer="c"\nen="e"\nru="р"\nuk="у"\n', "include the answer"),
    ('[[exercise]]\nkind="reorder"\nparts=["a","b"]\nen="e"\nru="р"\nuk="у"\n', "at least 3"),
    ('[[rule]]\ntitle={en="e",ru="р",uk=""}\nexplain={en="e",ru="р",uk="у"}\n', "non-empty"),
    ('[[rule]]\ntitle={en="e",ru="р",uk="у"}\nexplain={en="e",ru="р",uk="у"}\nexmple=[]\n', "unknown"),
    ('[[note]]\ndate="11/11"\ntext="x"\n', "YYYY-MM-DD"),
])
def test_rejects(tmp_path, body, message):
    with pytest.raises(ContentError, match=message):
        load_lesson(write(tmp_path, body))


def test_number_must_match_file(tmp_path):
    with pytest.raises(ContentError, match="file name"):
        load_lesson(write(tmp_path, "", name="08.toml"))


def test_vocab_furigana_must_match(tmp_path):
    f = tmp_path / "v.csv"
    f.write_text(",".join(VOCAB_COLUMNS) + "\n私,わたくし,私[わたし],I,я,я,,,,,,,\n")
    with pytest.raises(ContentError, match="does not give"):
        load_vocab(f)


def test_vocab_example_needs_translations(tmp_path):
    f = tmp_path / "v.csv"
    f.write_text(",".join(VOCAB_COLUMNS) + "\n私,わたし,私[わたし],I,я,я,,,,私[わたし]です。,I am.,,\n")
    with pytest.raises(ContentError, match="example"):
        load_vocab(f)
