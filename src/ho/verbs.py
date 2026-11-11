"""Verb lexicon and conjugation.

A verb is its dictionary form in furigana notation plus its class; every
other form is derived from those two. Forms stay in furigana notation, so
the reading of each is checked by the same parser as everything else.
"""

from __future__ import annotations

import tomllib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from ho import furigana
from ho.errors import ContentError

Kind = Literal["godan", "ichidan", "iku", "kuru", "suru"]
KINDS: tuple[Kind, ...] = ("godan", "ichidan", "iku", "kuru", "suru")
KIND_LABEL: dict[Kind, str] = {
    "godan": "godan · u-verb",
    "iku": "godan · u-verb, irregular て-form",
    "ichidan": "ichidan · ru-verb",
    "kuru": "irregular",
    "suru": "する verb",
}

# Godan endings by vowel row: a i u e o.
_ROWS = {
    "う": "わいうえお", "く": "かきくけこ", "ぐ": "がぎぐげご", "す": "さしすせそ",
    "つ": "たちつてと", "ぬ": "なにぬねの", "ぶ": "ばびぶべぼ", "む": "まみむめも",
    "る": "らりるれろ",
}


@dataclass(frozen=True)
class Gloss:
    base: str
    past: str
    participle: str


@dataclass(frozen=True)
class Verb:
    dict: str
    kind: Kind
    match: tuple[str, ...]
    gloss: Gloss


@dataclass(frozen=True)
class Form:
    label: str
    ja: str
    meaning: str


@dataclass(frozen=True)
class _Stems:
    dictionary: str
    i: str
    a: str
    te: str
    ta: str
    potential: str
    volitional: str
    ba: str
    passive: str
    causative: str


def _stems(v: Verb) -> _Stems:
    d = v.dict
    if v.kind == "kuru":
        b = d.removesuffix("来[く]る")
        return _Stems(d, b + "来[き]", b + "来[こ]", b + "来[き]て", b + "来[き]た",
                      b + "来[こ]られる", b + "来[こ]よう", b + "来[く]れば", b + "来[こ]られる",
                      b + "来[こ]させる")
    if v.kind == "suru":
        b = d.removesuffix("する")
        return _Stems(d, b + "し", b + "し", b + "して", b + "した", b + "できる",
                      b + "しよう", b + "すれば", b + "される", b + "させる")
    if v.kind == "ichidan":
        s = d[:-1]
        return _Stems(d, s, s, s + "て", s + "た", s + "られる", s + "よう", s + "れば",
                      s + "られる", s + "させる")
    end, pre = d[-1], d[:-1]
    row = _ROWS[end]
    if v.kind == "iku" or end in "うつる":
        te, ta = pre + "って", pre + "った"
    elif end == "く":
        te, ta = pre + "いて", pre + "いた"
    elif end == "ぐ":
        te, ta = pre + "いで", pre + "いだ"
    elif end == "す":
        te, ta = pre + "して", pre + "した"
    else:
        te, ta = pre + "んで", pre + "んだ"
    return _Stems(d, pre + row[1], pre + row[0], te, ta, pre + row[3] + "る",
                  pre + row[4] + "う", pre + row[3] + "ば", pre + row[0] + "れる",
                  pre + row[0] + "せる")


_ROWS_SPEC: tuple[tuple[str, Callable[[_Stems], str], Callable[[Gloss], str]], ...] = (
    ("辞書形 dictionary", lambda s: s.dictionary, lambda g: "to " + g.base),
    ("ます polite", lambda s: s.i + "ます", lambda g: g.base + " (polite)"),
    ("ない negative", lambda s: s.a + "ない", lambda g: "don't " + g.base),
    ("ません polite negative", lambda s: s.i + "ません", lambda g: "don't " + g.base + " (polite)"),
    ("た past", lambda s: s.ta, lambda g: g.past),
    ("ました polite past", lambda s: s.i + "ました", lambda g: g.past + " (polite)"),
    ("なかった past negative", lambda s: s.a + "なかった", lambda g: "didn't " + g.base),
    ("ませんでした polite past neg.", lambda s: s.i + "ませんでした",
     lambda g: "didn't " + g.base + " (polite)"),
    ("て te-form", lambda s: s.te, lambda g: g.base + " and… (linking form)"),
    ("てください request", lambda s: s.te + "ください", lambda g: "please " + g.base),
    ("たいです want to", lambda s: s.i + "たいです", lambda g: "want to " + g.base),
    ("可能 potential", lambda s: s.potential, lambda g: "can " + g.base),
    ("可能・ません can't", lambda s: s.potential[:-1] + "ません",
     lambda g: "can't " + g.base + " (polite)"),
    ("ましょう let's", lambda s: s.i + "ましょう", lambda g: "let's " + g.base + " (polite)"),
    ("意向 let's (casual)", lambda s: s.volitional, lambda g: "let's " + g.base + " (casual)"),
    ("ば conditional", lambda s: s.ba, lambda g: "if (I) " + g.base),
    ("たら conditional", lambda s: s.ta + "ら", lambda g: "if / when (I) " + g.base),
    ("てもいいですか permission", lambda s: s.te + "もいいですか", lambda g: "may I " + g.base + "?"),
    ("受身 passive", lambda s: s.passive,
     lambda g: "passive form" if g.participle == "—" else "be " + g.participle),
    ("使役 causative", lambda s: s.causative, lambda g: "make / let someone " + g.base),
)


def conjugate(v: Verb) -> tuple[Form, ...]:
    s = _stems(v)
    return tuple(Form(label, ja(s), meaning(v.gloss)) for label, ja, meaning in _ROWS_SPEC)


_TAIL = {"suru": "する", "kuru": "来[く]る", "ichidan": "る"}
_FIELDS = {"dict", "kind", "match", "gloss"}


def _verb(row: dict[str, Any], where: str) -> Verb:
    if set(row) != _FIELDS:
        raise ContentError(f"{where}: needs exactly {sorted(_FIELDS)}, found {sorted(row)}")
    try:
        v = Verb(row["dict"], row["kind"], tuple(row["match"]), Gloss(**row["gloss"]))
    except TypeError as e:
        raise ContentError(f"{where}: {e}") from e
    if v.kind not in KINDS:
        raise ContentError(f"{where}: unknown kind {v.kind!r}")
    tail = _TAIL.get(v.kind)
    wrong_tail = tail is not None and not v.dict.endswith(tail)
    wrong_ending = v.kind in ("godan", "iku") and v.dict[-1:] not in _ROWS
    if wrong_tail or wrong_ending:
        raise ContentError(f"{where}: {v.dict!r} does not end like a {v.kind} verb")
    try:
        furigana.parse(v.dict)
    except ContentError as e:
        raise ContentError(f"{where}: {e}") from e
    if not v.match or any(key.count("|") != 1 for key in v.match):
        raise ContentError(f"{where}: match keys must be '漢字|よみ', found {list(v.match)}")
    return v


def load_verbs(path: Path) -> tuple[Verb, ...]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if set(data) != {"verb"}:
        raise ContentError(f"{path}: expected only [[verb]] tables, found {sorted(data)}")
    out: list[Verb] = []
    dicts: set[str] = set()
    keys: dict[str, str] = {}
    for i, row in enumerate(data["verb"]):
        where = f"{path}: verb #{i + 1} {row.get('dict', '')!r}"
        v = _verb(row, where)
        if v.dict in dicts:
            raise ContentError(f"{where}: duplicate verb")
        dicts.add(v.dict)
        for key in v.match:
            if key in keys:
                raise ContentError(f"{where}: match key {key!r} already belongs to {keys[key]!r}")
            keys[key] = v.dict
        out.append(v)
    return tuple(out)


def find_verbs(texts: Iterable[str], verbs: Iterable[Verb]) -> tuple[Verb, ...]:
    """Verbs inflected in the texts: a matching ruby followed by kana."""
    by_key = {key: v for v in verbs for key in v.match}
    found: dict[str, Verb] = {}
    for text in texts:
        segs = furigana.parse(text)
        for seg, nxt in zip(segs, (*segs[1:], None), strict=True):
            if seg.ruby is None:
                continue
            v = by_key.get(f"{seg.text}|{seg.ruby}")
            after = nxt.text[0] if nxt is not None and nxt.ruby is None else ""
            if v is None or not ("ぁ" <= after <= "ゖ"):
                continue
            if v.kind == "suru" and after not in "しすさで":
                continue
            found.setdefault(v.dict, v)
    return tuple(found.values())
