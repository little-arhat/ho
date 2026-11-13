"""Draw the illustration for reading texts (ingest time only; the build never calls a model).

    OPENROUTER_FLUENT=... uv run --group tools illustrate [--force] content/reading/03-depato.toml ...

Same pipeline as perapera: google/gemini-3.1-flash-image draws (~$0.07),
google/gemini-2.5-flash reads the picture back (~$0.001). The pictures must
carry no writing at all: a model asked for a sign invents wrong kana, and a
wrong glyph in a reading book teaches a wrong letterform. So an image ships
only if the read-back finds no text; one retry, then it fails loudly.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import tomllib
import urllib.request
from pathlib import Path

from PIL import Image

DRAW = "google/gemini-3.1-flash-image"
CHECK = "google/gemini-2.5-flash"
ATTEMPTS = 2
SIDE = 960  # px, longest side of the shipped JPEG

STYLE = (
    "Warm, simple flat illustration for a beginner's Japanese reading book, soft colours, "
    "clean shapes, friendly people, set in Japan. Landscape, 4:3. "
    "Absolutely no text anywhere: no letters, no numbers, no signs with writing, "
    "no labels, no speech bubbles, no logos, no watermark."
)
CHECK_PROMPT = (
    "Does this image contain any text, letters, digits or writing of any script, "
    "including on signs, screens, books or clothes? If there is none, answer exactly NONE. "
    "Otherwise transcribe what you see."
)


def _post(key: str, body: dict) -> dict:
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def _draw(key: str, scene: str) -> tuple[bytes, float]:
    reply = _post(key, {"model": DRAW, "modalities": ["image", "text"], "usage": {"include": True},
                        "messages": [{"role": "user", "content": f"{scene}\n\n{STYLE}"}]})
    images = reply["choices"][0]["message"].get("images") or []
    if not images:
        raise RuntimeError("no image in the reply")
    url = images[0]["image_url"]["url"]
    return base64.b64decode(url.split(",", 1)[1]), reply.get("usage", {}).get("cost", 0.0)


def _text_seen(key: str, png: bytes) -> tuple[str, float]:
    data = base64.b64encode(png).decode()
    reply = _post(key, {"model": CHECK, "usage": {"include": True}, "messages": [{"role": "user", "content": [
        {"type": "text", "text": CHECK_PROMPT},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{data}"}}]}]})
    return reply["choices"][0]["message"]["content"].strip(), reply.get("usage", {}).get("cost", 0.0)


def _jpeg(png: bytes) -> bytes:
    img = Image.open(io.BytesIO(png)).convert("RGB")
    img.thumbnail((SIDE, SIDE))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=82, optimize=True, progressive=True)
    return out.getvalue()


def illustrate(key: str, toml: Path) -> float:
    """Write toml's sibling .jpg; return the money spent."""
    scene = tomllib.loads(toml.read_text(encoding="utf-8"))["scene"].strip()
    spent, seen = 0.0, ""
    for _ in range(ATTEMPTS):
        png, cost = _draw(key, scene)
        seen, check_cost = _text_seen(key, png)
        spent += cost + check_cost
        if seen.rstrip(".").upper() == "NONE":
            toml.with_suffix(".jpg").write_bytes(_jpeg(png))
            return spent
    raise RuntimeError(f"{toml.name}: the picture kept containing text ({seen!r}); ${spent:.3f} spent")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Draw illustrations for reading texts.")
    parser.add_argument("texts", nargs="+", type=Path)
    parser.add_argument("--force", action="store_true", help="redraw pictures that already exist")
    args = parser.parse_args(argv)
    key = os.environ.get("OPENROUTER_FLUENT", "")
    if not key:
        print("OPENROUTER_FLUENT is not set", file=sys.stderr)
        return 2
    total, failed = 0.0, 0
    for toml in args.texts:
        if toml.with_suffix(".jpg").exists() and not args.force:
            print(f"skip {toml.name} (has a picture)")
            continue
        try:
            spent = illustrate(key, toml)
            total += spent
            print(f"drew {toml.with_suffix('.jpg')} (${spent:.3f})")
        except (RuntimeError, OSError, KeyError) as e:
            failed += 1
            print(f"FAILED {e}", file=sys.stderr)
    print(f"total ${total:.3f}")
    return 1 if failed else 0
