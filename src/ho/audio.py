"""Recorded audio for Japanese lines: naming and checking. Pure.

A clip is `audio/<key>.m4a`, named by what it says (voice, text and our
reading), so an edited line simply has no clip until `uv run voice` makes
one, and the page falls back to the device's voice meanwhile.

The voice engine reads the kanji text itself, which gives it the pitch
accent from its dictionary. Its reading is accepted only if it says the same
sounds as our furigana: compare() folds both to one phonetic spelling,
because the engine writes long vowels as they sound (がくせい → ガクセエ,
コーヒー → コオヒイ) and particles as spoken (を → オ). Our text gives no
reading for digits or Latin letters, so such a run matches any sounds there.
"""

from __future__ import annotations

import hashlib
import re

from ho import furigana
from ho.kana import romaji
from ho.romaji import speech

VOICE = "voicevox:30"  # No.7 (アナウンス): VOICEVOX's announcer-style voice
CREDIT = "VOICEVOX:No.7"


def key(text: str) -> str:
    """The clip name for a furigana line."""
    raw = f"{VOICE}\n{furigana.plain(text)}\n{speech(text)}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


_LONG = (("ā", "aa"), ("ī", "ii"), ("ū", "uu"), ("ē", "ee"), ("ō", "oo"), ("ou", "oo"), ("ei", "ee"))


def sounds(kana: str) -> str:
    """Kana as a comparable sound string: romaji with long vowels spelt one way."""
    out = romaji(kana)
    for a, b in _LONG:
        out = out.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", out)


_NO_READING = re.compile(r"[0-9０-９A-Za-zＡ-Ｚａ-ｚ]+")  # numbers and Latin: our text gives no reading


def pattern(text: str) -> re.Pattern[str]:
    """What the engine must say for our line: its sounds, and any sounds where
    our text has a number or Latin letters (IC, Wi-Fi)."""
    spoken = re.sub(r"[\W_]", "", speech(text))
    parts = _NO_READING.split(spoken)
    return re.compile(".+".join(re.escape(sounds(p)) for p in parts))


def agrees(text: str, engine_kana: str) -> bool:
    """Whether the engine's reading says the sounds of our furigana."""
    return pattern(text).fullmatch(sounds(engine_kana)) is not None
