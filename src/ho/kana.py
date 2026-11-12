"""Kana conversions."""

from __future__ import annotations

_RO = dict(zip(
    "あいうえおかきくけこがぎぐげごさしすせそざじずぜぞたちつてとだぢづでど"
    "なにぬねのはひふへほばびぶべぼぱぴぷぺぽまみむめもやゆよらりるれろわをん",
    "a i u e o ka ki ku ke ko ga gi gu ge go sa shi su se so za ji zu ze zo "
    "ta chi tsu te to da ji zu de do na ni nu ne no ha hi fu he ho ba bi bu be bo "
    "pa pi pu pe po ma mi mu me mo ya yu yo ra ri ru re ro wa o n".split(),
    strict=True,
))
_SMALL_Y = {"ゃ": "a", "ゅ": "u", "ょ": "o"}
# Small vowels after a kana make the sounds loanwords need: チェ che, ティ ti, ファ fa, ウィ wi.
_SMALL_V = {"ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o"}
_MACRON = {"a": "ā", "i": "ī", "u": "ū", "e": "ē", "o": "ō"}


def kata_to_hira(s: str) -> str:
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def _onset(c: str) -> str:
    """The consonant part of a kana, as it combines with a following small vowel."""
    base = "vu" if c == "ゔ" else _RO.get(c, "")
    if base in ("chi", "shi", "ji"):
        return base[:-1]
    if base == "fu":
        return "f"
    if base == "u":
        return "w"
    return base[:-1]


def romaji(kana: str) -> str:
    """Hepburn romaji. ー puts a macron on the vowel before it (コーヒー → kōhī);
    long vowels spelled with kana stay as written (きょう → kyou)."""
    k = kata_to_hira(kana)
    out: list[str] = []
    i = 0
    while i < len(k):
        c = k[i]
        nxt = k[i + 1] if i + 1 < len(k) else ""
        if c == "ー":
            last = out[-1] if out else ""
            if last and last[-1] in _MACRON:
                out[-1] = last[:-1] + _MACRON[last[-1]]
        elif c == "っ":
            r = _RO.get(nxt, "")
            out.append("t" if r.startswith("ch") else r[:1])
        elif nxt in _SMALL_Y:
            base = _RO.get(c, "")
            vowel = _SMALL_Y[nxt]
            out.append(base[:-1] + vowel if base in ("shi", "chi", "ji") else base[:-1] + "y" + vowel)
            i += 1
        elif nxt in _SMALL_V and _onset(c):
            out.append(_onset(c) + _SMALL_V[nxt])
            i += 1
        else:
            out.append(_RO.get(c) or _SMALL_V.get(c) or ("vu" if c == "ゔ" else c))
        i += 1
    return "".join(out)
