"""Katakana drill: words, and the romaji spellings accepted for each.

A word is split into tokens (one mora, with flags for a preceding ッ and
following ー marks). Each token gets its list of accepted spellings; an answer
is right when it is one spelling per token, in order. The `near_*` variants
also accept a missing long vowel or missing double consonant, so the drill
can say which mark was missed.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from ho.errors import ContentError


def _table(spec: str) -> dict[str, tuple[str, ...]]:
    out = {}
    for pair in spec.split():
        kana, spellings = pair.split(":")
        out[kana] = tuple(spellings.split(","))
    return out


_SINGLE = _table("""
ア:a イ:i ウ:u エ:e オ:o カ:ka キ:ki ク:ku ケ:ke コ:ko ガ:ga ギ:gi グ:gu ゲ:ge ゴ:go
サ:sa シ:shi,si ス:su セ:se ソ:so ザ:za ジ:ji,zi ズ:zu ゼ:ze ゾ:zo タ:ta チ:chi,ti ツ:tsu,tu テ:te ト:to
ダ:da ヂ:ji,di,zi ヅ:zu,du デ:de ド:do ナ:na ニ:ni ヌ:nu ネ:ne ノ:no ハ:ha ヒ:hi フ:fu,hu ヘ:he ホ:ho
バ:ba ビ:bi ブ:bu ベ:be ボ:bo パ:pa ピ:pi プ:pu ペ:pe ポ:po マ:ma ミ:mi ム:mu メ:me モ:mo
ヤ:ya ユ:yu ヨ:yo ラ:ra リ:ri ル:ru レ:re ロ:ro ワ:wa ヲ:wo,o ヴ:vu
ァ:a,xa,la ィ:i,xi,li ゥ:u,xu,lu ェ:e,xe,le ォ:o,xo,lo ャ:ya,xya ュ:yu,xyu ョ:yo,xyo
""")

_COMBO = _table("""
ティ:ti,thi ディ:di,dhi トゥ:tu,twu ドゥ:du,dwu テュ:tyu,thu デュ:dyu,dhu
ファ:fa フィ:fi フェ:fe フォ:fo フュ:fyu ウィ:wi,ui ウェ:we,ue ウォ:wo,uo
ヴァ:va ヴィ:vi ヴェ:ve ヴォ:vo ツァ:tsa ツィ:tsi ツェ:tse ツォ:tso イェ:ye
シェ:she,sye ジェ:je,jye,zye チェ:che,tye,cye
""")
_YOON_ROWS = {"キ": ("ky",), "ギ": ("gy",), "ニ": ("ny",), "ヒ": ("hy",), "ビ": ("by",),
              "ピ": ("py",), "ミ": ("my",), "リ": ("ry",), "シ": ("sh", "sy"),
              "ジ": ("j", "jy", "zy"), "チ": ("ch", "ty", "cy")}
for _kana, _prefixes in _YOON_ROWS.items():
    for _small, _vowel in (("ャ", "a"), ("ュ", "u"), ("ョ", "o")):
        _COMBO[_kana + _small] = tuple(p + _vowel for p in _prefixes)

_MACRON = {"a": "ā", "i": "ī", "u": "ū", "e": "ē", "o": "ō"}
_CIRCUMFLEX = {"a": "â", "i": "î", "u": "û", "e": "ê", "o": "ô"}


@dataclass
class _Token:
    spellings: tuple[str, ...]
    n: bool = False
    gem: bool = False
    long: int = 0


@dataclass(frozen=True)
class Answers:
    exact: list[list[str]]
    near_long: list[list[str]]
    near_gem: list[list[str]]
    near_both: list[list[str]]
    typed: str
    macron: str


@dataclass(frozen=True)
class Word:
    ja: str
    en: str
    ru: str
    uk: str
    answers: Answers = field(compare=False)


def _tokenize(word: str) -> list[_Token]:
    out: list[_Token] = []
    gem = False
    i = 0
    while i < len(word):
        c = word[i]
        if c == "ッ":
            gem = True
            i += 1
            continue
        if c == "ー":
            if out:
                out[-1].long += 1
            i += 1
            continue
        two = word[i : i + 2]
        if len(two) == 2 and two in _COMBO:
            tok = _Token(_COMBO[two])
            i += 2
        elif c == "ン":
            tok = _Token(("n",), n=True)
            i += 1
        elif c in _SINGLE:
            tok = _Token(_SINGLE[c])
            i += 1
        else:
            tok = _Token((c.lower(),))
            i += 1
        tok.gem = gem
        gem = False
        out.append(tok)
    return out


def _double(s: str) -> list[str]:
    if s.startswith("ch"):
        return ["t" + s, "c" + s]
    if s[0] in "aeiou":
        return [s]
    return [s[0] + s]


def _alternatives(tokens: list[_Token], i: int, *, long: bool, gem: bool) -> list[str]:
    t = tokens[i]
    if t.n:
        alts = ["n", "nn", "n'"]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if nxt is not None and not nxt.n and any(s[0] in "bmp" for s in nxt.spellings):
            alts.append("m")
    else:
        alts = list(t.spellings)
    if t.gem:
        doubled = [d for s in alts for d in _double(s)]
        alts = doubled + alts if gem else doubled
    if t.long:
        stretched = []
        for s in alts:
            v = s[-1]
            if v not in _MACRON:
                stretched.append(s)
                continue
            stretched += [s + v * t.long, s + "-" * t.long, s[:-1] + _MACRON[v], s[:-1] + _CIRCUMFLEX[v]]
            if long:
                stretched.append(s)
        alts = stretched
    return alts


def _forms(tokens: list[_Token]) -> tuple[str, str]:
    typed, mac = [], []
    for i, t in enumerate(tokens):
        if t.n:
            nxt = tokens[i + 1] if i + 1 < len(tokens) else None
            base = "n'" if nxt is not None and not nxt.n and nxt.spellings[0][0] in "aeiouy" else "n"
        else:
            base = t.spellings[0]
        if t.gem:
            base = _double(base)[0]
        ty = mc = base
        v = base[-1]
        if t.long and v in _MACRON:
            ty = base + v * t.long
            mc = base[:-1] + _MACRON[v]
        typed.append(ty)
        mac.append(mc)
    return "".join(typed), "".join(mac)


def answers(ja: str) -> Answers:
    t = _tokenize(ja)

    def alts(*, long: bool, gem: bool) -> list[list[str]]:
        return [_alternatives(t, i, long=long, gem=gem) for i in range(len(t))]

    typed, mac = _forms(t)
    return Answers(alts(long=False, gem=False), alts(long=True, gem=False),
                   alts(long=False, gem=True), alts(long=True, gem=True), typed, mac)


def load(path: Path) -> tuple[Word, ...]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    seen: set[str] = set()
    out = []
    for i, row in enumerate(data.get("word", [])):
        where = f"{path}: word #{i + 1}"
        if set(row) != {"ja", "en", "ru", "uk"} or not all(row.values()):
            raise ContentError(f"{where}: needs exactly ja, en, ru, uk, all non-empty")
        if row["ja"] in seen:
            raise ContentError(f"{where}: duplicate {row['ja']!r}")
        if not all("ァ" <= c <= "ヺ" or c == "ー" for c in row["ja"]):
            raise ContentError(f"{where}: {row['ja']!r} is not all katakana")
        seen.add(row["ja"])
        out.append(Word(**row, answers=answers(row["ja"])))
    return tuple(out)
