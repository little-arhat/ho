---
name: ingest
description: Turn new class material in inbox/ (photos or screenshots of Minna no Nihongo pages, teacher's slides and notes, 15-minute kanji book pages, vocab pages) or an Anki deck CSV into site content, validate it, commit and push. Use when the user drops files into inbox/ or says "ingest", "process the inbox", or gives an ank CSV.
---

# Ingest

Input is `inbox/` (gitignored), plus an optional note from the user ("today: で for place").
Images are never committed. Leave them in `inbox/` after processing: the user cleans it up.

## 1. Look at everything first

Read every image in `inbox/` before editing anything. Sort each one into:

| Kind | Looks like | Goes to |
|---|---|---|
| Teacher's slides / notes | typed or handwritten drills, substitution tables, underlines | `content/lessons/NN.toml` `[[note]]`, plus rules/exercises it teaches |
| MnN lesson page | 文型, 例文, 練習A/B/C, 会話 | `content/lessons/NN.toml` rules, examples, exercises (our own wording) |
| MnN vocab page | 語彙 list, page tab number | `content/lessons/NN.vocab.csv` |
| MnN reference words | "Reference Words & Information", a themed picture list | `content/words/<id>.toml` (title, lesson) + `<id>.csv` (vocab columns) |
| 15-minute kanji book | numbered card `043 ⑤`, stroke boxes, word table | `content/kanji/book.toml` |

The lesson is the **MnN chapter**, from the page tab, page number or content, never the file name. If a slide's lesson is unclear, it belongs to the most recent lesson unless its grammar says otherwise. Say which lesson you chose and why.

## 2. Write content (formats are enforced by the loaders)

- Japanese is always furigana notation: `会[かい]社[しゃ]`. The ruby base is the kanji run right before `[`.
- Learner-facing text always has `en`, `ru`, `uk`, `es`. Draft RU/UK/ES yourself; tell the user they are drafts.
- **Teacher's notes**: verbatim, no names, `date = YYYY-MM-DD` set to today. Keep the layout with full-width spaces.
- **Rules**: state the rule explicitly (what the slides only show by example). Add a `pattern` when there is a slot structure, a `table` for paradigms and verb pairs (cells are Japanese; head cells may be symbols like `Ⓐ → Ⓑ`). Add 1–2 `[[exercise]]`s (`choice` with `＿`, or `reorder`) per new point.
- **Cover the whole lesson, not just the slides.** Before shipping a lesson, list what MnN teaches in it (文型, 例文, and the vocab's verbs and set phrases) and check each has a rule: a verb pair that works like one already covered still gets its own rule, table and drills (L7: あげます/もらいます was there, but 貸します/借ります and 教えます/習います were only named in passing until the user noticed). Keep `grammar` (the lesson's one-line list) in step with the rules.
- **Kanji book pages**: one `[[kanji]]` per card, with `number`, `level` (the circled N-level), `readings` exactly as printed (hiragana = kun, katakana = on, `-` before okurigana, `(…)` secondary, `…*` special), `meaning` in 4 languages, and every word row as `[[kanji.word]]` with its example sentence translated. Transcribe handwritten additions too, as extra words. If the kanji already has a card in `content/kanji/lessons.toml`, move it (delete it there).
- **Vocab from an Anki CSV**: write the TSV of `uk, es, note_ru, note_uk, note_es, example_ru, example_uk, example_es` per row (`-` in note_ru drops a scan-only note), then `uv run ank-import ANK.csv N TSV`.
- **Vocab examples**: give a new word an `example` sentence (with translations) whenever you can. It is the first sentence on the word's page (`words/<word>/`) and the sentence on its Anki card; a word without one shows only kanji-card and reading-text lines.
- **Word identity** is the furigana with its reading, ignoring `～`/`~` and an expression's final `。`/`？` (`lessons.word_key`). The same word in two lists (パソコン in L2 and L7, 肉 in L6 and the food list) shares one word page; homographs need different readings (人[じん], 人[ひと]). The build fails if two words would share a page (`words/時計-とけい/`): fix the content, not the check.
- New lesson? `content/lessons/NN.toml` needs `number`, `title` (the topic, 4 languages) and `grammar` (a short Japanese list of the points).
- A new kanji anywhere in content that is not jōyō needs `uv run refdata <kanjivg-main.zip> <kanjidic2.xml.gz>` (download from the KanjiVG releases and EDRDG).

## 3. Reading texts (three per new lesson)

`content/reading/NN-name.toml`: the same scene twice, as `[[prose]]` paragraphs and as `[[dialog]]` lines (each with a `speaker`, which must be a word: a name under `[[new]]`, or 先生, 店員…). Write three per lesson, on the lesson's topic and grammar, each a little longer than the previous lesson's (L7 texts run 6 paragraphs and 9–12 dialog lines). Reuse the recurring cast (マリア, 田中, ワン, カリナ, 山田 先生, 木村, 由紀, アンナ), declared under `[[new]]` in each text that uses them.

Tokens joined by `|`, `surface=word` for inflected forms (`借[か]りました=借[か]ります`); words outside lessons 1–N go under `[[new]]`. Use only grammar of lessons 1–N too: the loader checks words, not grammar, so check it yourself (e.g. no を before L6, no ～ませんか before its lesson). Link tokens accurately: a linked line also shows on that word's page, with the word marked. The lesson tags are derived from the words.

**Link the phrase book.** When a line says a phrase-book phrase, add `uses = ["<the phrase's ja, exactly>"]` to that block; the loader checks the phrase exists and that the line says its `ja` (〇〇 matches any words; casual forms do not count). Link situational phrases (いらっしゃいませ, これをください, 何番線ですか); leave the everyday ones (すみません, お願いします, ありがとうございます, はい、そうです) unlinked, or their cards list half the site. `uv run python _probes/phrase_hits.py content/reading` lists candidates if the probe is there.

Then draw the picture: `uv run --env-file .env --group tools illustrate content/reading/NN-name.toml` (the key is `OPENROUTER_FLUENT` in `.env`; never print it). It rejects pictures with any text in them. If the key is missing, ship without a picture and tell the user.

## 3a. Scenes (phrase-book level, not tied to a lesson)

`content/scenes/<name>.toml` (lowercase name, no `lesson`): the same story + dialog format, in natural Japanese for a place, drawing on every lesson's words; everything else under `[[new]]` with 4 languages (the recurring cast too). Lines name the phrase-book phrases they say with `uses`; a scene is how a phrase-book section shows its phrases in context, so write one when a section has none, and add the phrases a scene needs to the phrase book when they are missing (the clinic scene brought the Health topic). Pitfalls the loader catches: a speaker is one token (女[おんな]の人[ひと], not three); jukujikun take whole-word furigana (今日[きょう], 大人[おとな], 風邪[かぜ]); a phrase fixed to a number (5階, 7時) needs exactly that number in the line. Write prices in digits (２８００|円[えん]). Keep signs, lettering and post boxes out of the picture prompt: `illustrate` rejects any text in the picture.

## 3b. Record the new lines (VOICEVOX)

Every new Japanese line (vocab, examples, rules, reading texts) needs a clip, or it plays in the device voice:

    open -a Docker                      # wait until `docker info` works
    docker run -d --rm --name voicevox -p 127.0.0.1:50021:50021 voicevox/voicevox_engine:cpu-0.26.1
    curl -s 127.0.0.1:50021/version     # wait until it answers
    uv run voice --prune                # records what is missing, deletes clips no line uses
    docker stop voicevox

`voice` skips a line when the engine's reading differs from our kana. 24 known skips stay on the device voice (〇〇 placeholders, 失礼いたします, the 母の日 sentence, the ages list); report any new skip and fix its kana or wording if it is ours. Commit `audio/` with the content.

## 4. Validate, look, ship

1. `uv run pytest -q` and `uv run build`. Fix every content error; never weaken a check to pass.
2. Open the changed pages in Chromium (Playwright, `executable_path=/Applications/Chromium.app/Contents/MacOS/Chromium`), phone (390 px) and desktop width, and check that they render without JS errors or horizontal scroll. Serve `_site` over HTTP (`http.server` with `directory="_site"`): from `file://` the module scripts do not run, so search, popups and drills look dead. Check a new word's page (`words/<word>/`) and a reading popup's "word page" link too.
3. Commit per lesson / per kind (lesson notes, kanji, vocab, reading, audio), say what came from which photos, `git push origin master` (the branch has no upstream), and wait for the Pages workflow of that commit: `gh` is not installed, so poll `https://api.github.com/repos/little-arhat/ho/actions/runs?head_sha=<sha>` until it is completed, then check its jobs (`_probes/ci.sh` does this, if present).

## 5. Report

List what changed (by lesson), what you guessed (unclear handwriting, chosen lesson), what is a draft (RU/UK/ES), which lines have no recorded clip, and anything you skipped and why.

Search (kanji list, words list) and word pages need no work: they are built from the content.
