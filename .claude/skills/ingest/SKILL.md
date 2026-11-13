---
name: ingest
description: Turn new class material in inbox/ (photos or screenshots of Minna no Nihongo pages, teacher's slides and notes, 15-minute kanji book pages, vocab pages) or an Anki deck CSV into site content, validate it, commit and push. Use when the user drops files into inbox/ or says "ingest", "process the inbox", or gives an ank CSV.
---

# Ingest

Input is `inbox/` (gitignored), plus an optional note from the user ("today: で for place").
Each image ends in `processed/` (gitignored) once its content is committed. Images are never committed.

## 1. Look at everything first

Read every image in `inbox/` before editing anything. Sort each one into:

| Kind | Looks like | Goes to |
|---|---|---|
| Teacher's slides / notes | typed or handwritten drills, substitution tables, underlines | `content/lessons/NN.toml` `[[note]]`, plus rules/exercises it teaches |
| MnN lesson page | 文型, 例文, 練習A/B/C, 会話 | `content/lessons/NN.toml` rules, examples, exercises (our own wording) |
| MnN vocab page | 語彙 list, page tab number | `content/lessons/NN.vocab.csv` |
| 15-minute kanji book | numbered card `043 ⑤`, stroke boxes, word table | `content/kanji/book.toml` |

The lesson is the **MnN chapter**, from the page tab, page number or content, never the file name. If a slide's lesson is unclear, it belongs to the most recent lesson unless its grammar says otherwise. Say which lesson you chose and why.

## 2. Write content (formats are enforced by the loaders)

- Japanese is always furigana notation: `会[かい]社[しゃ]`. The ruby base is the kanji run right before `[`.
- Learner-facing text always has `en`, `ru`, `uk`. Draft RU/UK yourself; tell the user they are drafts.
- **Teacher's notes**: verbatim, no names, `date = YYYY-MM-DD` set to today. Keep the layout with full-width spaces.
- **Rules**: state the rule explicitly (what the slides only show by example). Add a `pattern` when there is a slot structure. Add 1–2 `[[exercise]]`s (`choice` with `＿`, or `reorder`) per new point.
- **Kanji book pages**: one `[[kanji]]` per card, with `number`, `level` (the circled N-level), `readings` exactly as printed (hiragana = kun, katakana = on, `-` before okurigana, `(…)` secondary, `…*` special), `meaning` in 3 languages, and every word row as `[[kanji.word]]` with its example sentence translated. Transcribe handwritten additions too, as extra words. If the kanji already has a card in `content/kanji/lessons.toml`, move it (delete it there).
- **Vocab from an Anki CSV**: write the TSV of `uk, note_ru, note_uk, example_ru, example_uk` per row (`-` in note_ru drops a scan-only note), then `uv run ank-import ANK.csv N TSV`.
- New lesson? `content/lessons/NN.toml` needs `number`, `title` (the topic, 3 languages) and `grammar` (a short Japanese list of the points).
- A new kanji anywhere in content that is not jōyō needs `uv run refdata <kanjivg-main.zip> <kanjidic2.xml.gz>` (download from the KanjiVG releases and EDRDG).

## 3. Reading texts (when a lesson's vocab grows)

`content/reading/NN-name.toml`, tokens joined by `|`, `surface=word` for inflected forms; words outside lessons 1–N go under `[[new]]`. Then draw the picture: `OPENROUTER_FLUENT=… uv run --group tools illustrate content/reading/NN-name.toml` (it rejects pictures with any text in them). If the key isn't set, ship without a picture and tell the user.

## 4. Validate, look, ship

1. `uv run pytest -q` and `uv run build`. Fix every content error; never weaken a check to pass.
2. Open the changed pages in Chromium (Playwright, `executable_path=/Applications/Chromium.app/Contents/MacOS/Chromium`), phone and desktop width, and check that they render without JS errors.
3. Commit per lesson / per kind (lesson notes, kanji, vocab), say what came from which photos, push to `master`, wait for the Pages workflow of that commit to succeed.
4. Move the processed images: `mv inbox/<file> processed/`.

## 5. Report

List what changed (by lesson), what you guessed (unclear handwriting, chosen lesson), what is a draft (RU/UK), and anything you skipped and why.
