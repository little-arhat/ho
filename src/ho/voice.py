"""Record the site's Japanese lines with VOICEVOX (ingest time only; the build never calls it).

    docker run -d --rm --name voicevox -p 127.0.0.1:50021:50021 voicevox/voicevox_engine:cpu-0.26.1
    uv run voice [--prune]

For every line the site speaks that has no clip yet: the engine reads the
kanji text (its dictionary supplies the pitch accent); if its reading does
not say our furigana's sounds, it reads our kana instead (sounds certain,
accent its guess); if even that disagrees, the line is skipped and keeps
the device voice. Clips are mono AAC in audio/. --prune deletes clips no
line uses any more.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from ho import audio, furigana
from ho.build import ROOT, load_content
from ho.romaji import speech
from ho.site import spoken_texts

ENGINE = "http://127.0.0.1:50021"
SPEAKER = int(audio.VOICE.split(":")[1])
OUT = ROOT / "audio"


def _post(path: str, params: dict, body: dict | None = None) -> bytes:
    url = f"{ENGINE}{path}?{urllib.parse.urlencode(params)}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def _query(text: str) -> dict:
    return json.loads(_post("/audio_query", {"text": text, "speaker": SPEAKER}))


def _said(query: dict) -> str:
    return "".join(m["text"] for ap in query["accent_phrases"] for m in ap["moras"])


def plan(text: str) -> tuple[dict | None, str]:
    """The engine query to synthesise for a line, and how it was obtained."""
    q = _query(furigana.plain(text))
    if audio.agrees(text, _said(q)):
        return q, "kanji"
    q = _query(speech(text))
    if audio.agrees(text, _said(q)):
        return q, "kana"
    return None, f"engine says {_said(q)}"


def record(text: str, target: Path) -> str:
    query, how = plan(text)
    if query is None:
        return how
    query.update(outputSamplingRate=24000, outputStereo=False)
    wav = _post("/synthesis", {"speaker": SPEAKER}, query)
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = Path(tmp) / "a.wav", Path(tmp) / "a.m4a"
        src.write_bytes(wav)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(src), "-ac", "1", "-c:a", "aac", "-b:a", "40k",
                        "-movflags", "+faststart", str(dst)], check=True)
        target.write_bytes(dst.read_bytes())
    return how


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record the site's Japanese lines with VOICEVOX.")
    parser.add_argument("--prune", action="store_true", help="delete clips no line uses")
    args = parser.parse_args(argv)
    texts = spoken_texts(load_content(ROOT / "content", ROOT / "ref" / "kanji.json", OUT))
    keys = {audio.key(t): t for t in texts}
    OUT.mkdir(exist_ok=True)
    todo = [(k, t) for k, t in keys.items() if not (OUT / f"{k}.m4a").exists()]
    print(f"{len(keys)} lines, {len(todo)} to record")
    counts: dict[str, int] = {}
    skipped = []
    for i, (k, t) in enumerate(todo, 1):
        how = record(t, OUT / f"{k}.m4a")
        if how in ("kanji", "kana"):
            counts[how] = counts.get(how, 0) + 1
        else:
            skipped.append(f"{furigana.plain(t)}: {how}")
        if i % 100 == 0:
            print(f"  {i}/{len(todo)}", flush=True)
    print(f"recorded: {counts.get('kanji', 0)} read from kanji, {counts.get('kana', 0)} from our kana "
          f"(engine misread the kanji); skipped {len(skipped)}")
    for s in skipped:
        print("  skipped", s)
    if args.prune:
        stale = [p for p in OUT.glob("*.m4a") if p.stem not in keys]
        for p in stale:
            p.unlink()
        print(f"pruned {len(stale)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
