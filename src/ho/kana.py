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


def kata_to_hira(s: str) -> str:
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def romaji(kana: str) -> str:
    """Hepburn romaji; ー is dropped, so long vowels are not marked."""
    k = kata_to_hira(kana).replace("ー", "")
    out: list[str] = []
    i = 0
    while i < len(k):
        c = k[i]
        nxt = k[i + 1] if i + 1 < len(k) else ""
        if c == "っ":
            r = _RO.get(nxt, "")
            out.append("t" if r.startswith("ch") else r[:1])
        elif nxt in _SMALL_Y:
            base = _RO.get(c, "")
            vowel = _SMALL_Y[nxt]
            out.append(base[:-1] + vowel if base in ("shi", "chi", "ji") else base[:-1] + "y" + vowel)
            i += 1
        else:
            out.append(_RO.get(c, c))
        i += 1
    return "".join(out)
