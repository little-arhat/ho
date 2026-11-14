// Kanji drill. What: single kanji or words. From: all, the 15-minute book
// (optionally a number range), one lesson's kanji, or a hand-picked set; a
// word is in the set when every kanji in it is. Typed answers are compared
// after fold(), the same folding the build applied to the accepted answers.
// Close distractors for words come from the build. Nothing is saved but
// the chosen settings.
import { LANGS, stored, store } from "./prefs.js";
import { fold } from "./match.js";
import { esc, ruby, translations } from "./ruby.js";
import { sayButton } from "./speech.js";

const DATA = JSON.parse(document.getElementById("data").textContent);
const $ = (id) => document.getElementById(id);
const OPTIONS = 4;


// Task id → [label, prompt, answer]; "pick" answers choose 1 of 4, "type" answers are typed.
const MODES = {
  kanji: [
    ["k2m", "KANJI → MEANING"],
    ["k2m-t", "KANJI → TYPE MEANING"],
    ["m2k", "MEANING → KANJI"],
  ],
  words: [
    ["k2r", "KANJI → KANA"],
    ["k2r-t", "KANJI → TYPE READING"],
    ["k2m", "KANJI → MEANING"],
    ["k2m-t", "KANJI → TYPE MEANING"],
    ["m2k", "MEANING → KANJI"],
    ["r2k", "KANA → KANJI"],
  ],
};

const bookNo = Object.fromEntries(DATA.kanji.filter((k) => k.no).map((k) => [k.c, k.no]));
const bookMax = Math.max(...Object.values(bookNo));

const st = {
  what: stored("ho.kd.what", "words"),
  mode: stored("ho.kd.mode2", "k2r"),
  which: stored("ho.kd.which", "all"),
  from: stored("ho.kd.from", 1),
  to: stored("ho.kd.to", bookMax),
  picked: new Set(stored("ho.kd.picked", [])),
  item: null, done: false, missed: false, right: 0, asked: 0,
};
if (!MODES[st.what]) st.what = "words";
if (!(st.which in DATA.sets) && !["all", "custom"].includes(st.which)) st.which = "all";

function kanjiSet() {
  if (st.which === "all") return null;
  if (st.which === "custom") return st.picked;
  if (st.which === "book") return new Set(DATA.sets.book.filter((c) => bookNo[c] >= st.from && bookNo[c] <= st.to));
  return new Set(DATA.sets[st.which]);
}

function pool() {
  const set = kanjiSet();
  if (st.what === "kanji") return DATA.kanji.map((_, i) => i).filter((i) => !set || set.has(DATA.kanji[i].c));
  return DATA.words.map((_, i) => i).filter((i) => !set || DATA.words[i].k.every((c) => set.has(c)));
}

const pick = (xs) => xs[Math.floor(Math.random() * xs.length)];
function sample(xs, n) {
  const a = [...xs];
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a.slice(0, n);
}

const items = () => (st.what === "kanji" ? DATA.kanji : DATA.words);
const written = (it) => (st.what === "kanji" ? it.c : it.w);
const meaning = (it) => translations(it);

// Wrong options: for words, the build's close confusions; otherwise random others from the pool.
function wrongOptions(i, ids, field) {
  const list = items();
  let near = [];
  if (st.what === "words") near = field === "r" ? list[i].dr : list[i].dw;
  const others = sample(ids.filter((j) => j !== i), 30);
  const seen = new Set([field === "m" ? list[i].en : field === "r" ? list[i].r : written(list[i])]);
  const out = [];
  for (const j of [...sample(near, near.length), ...others]) {
    const key = field === "m" ? list[j].en : field === "r" ? list[j].r : written(list[j]);
    if (seen.has(key) || written(list[j]) === written(list[i])) continue;
    seen.add(key); out.push(j);
    if (out.length === OPTIONS - 1) break;
  }
  return out;
}

function paint() {
  $("what").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.k === st.what)));
  $("modes").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.k === st.mode)));
  $("which").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.k === st.which)));
  $("range-row").hidden = st.which !== "book";
  $("pick-row").hidden = st.which !== "custom";
  $("pick").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(st.picked.has(b.dataset.c))));
  const set = kanjiSet();
  const nk = set ? DATA.kanji.filter((k) => set.has(k.c)).length : DATA.kanji.length;
  const nw = DATA.words.filter((w) => !set || w.k.every((c) => set.has(c))).length;
  $("pool").textContent = `${nk} kanji · ${nw} words`;
  $("score").textContent = st.asked ? `${st.right} / ${st.asked} right first time` : "";
}

function renderModes() {
  const modes = MODES[st.what];
  if (!modes.some(([k]) => k === st.mode)) st.mode = modes[0][0];
  $("modes").innerHTML = modes.map(([k, label]) => `<button type="button" data-k="${k}">${label}</button>`).join("");
}

function prompt(it) {
  if (st.mode === "m2k") return `<div class="dq-mean">${meaning(it)}</div>`;
  if (st.mode === "r2k") return `<div class="dq-ja" lang="ja">${esc(it.r)}</div>`;
  return `<div class="dq-ja" lang="ja">${esc(written(it))}</div>`;
}

function ask() {
  const ids = pool();
  paint();
  $("fb").innerHTML = "";
  if (!ids.length) {
    $("q").textContent = st.which === "custom" ? "Pick some kanji above." : "Nothing here yet.";
    $("opts").innerHTML = ""; $("typed").hidden = true; $("next").hidden = true;
    return;
  }
  let i = pick(ids);
  if (ids.length > 1) while (i === st.item) i = pick(ids);
  st.item = i; st.done = false; st.missed = false;
  const it = items()[i];
  $("q").innerHTML = prompt(it);
  $("next").hidden = true;
  const typed = st.mode.endsWith("-t");
  $("typed").hidden = !typed;
  $("opts").innerHTML = "";
  if (typed) {
    $("answer").value = "";
    $("answer").placeholder = st.mode === "k2r-t" ? "reading: かな or romaji" : "meaning in EN, RU or UK";
    $("answer").lang = st.mode === "k2r-t" ? "ja" : "";
    $("answer").focus();
    return;
  }
  const field = st.mode === "k2r" ? "r" : st.mode === "k2m" ? "m" : "w";
  const opts = sample([i, ...wrongOptions(i, ids, field)], OPTIONS);
  const label = (j) => {
    const x = items()[j];
    if (field === "r") return `<span lang="ja">${esc(x.r)}</span>`;
    if (field === "m") return LANGS.map((l) => `<span class="tl tr-${l}">${esc(x[l])}</span>`).join("");
    return `<span lang="ja">${esc(written(x))}</span>`;
  };
  $("opts").className = "dopts" + (field === "m" ? " wide" : "");
  $("opts").innerHTML = opts.map((j) => `<button type="button" class="btn opt" data-j="${j}">${label(j)}</button>`).join("");
}

function reveal() {
  const it = items()[st.item];
  const head = st.what === "kanji"
    ? `<div class="dfb-ja" lang="ja">${esc(it.c)} <small>${esc(it.rd.join("、"))}</small></div>`
    : `<div class="dfb-ja" lang="ja">${ruby(it.ja)}${sayButton(it.say, it.clip)}</div>`;
  const src = st.what === "kanji"
    ? (it.no ? `15-minute book № ${it.no}` : "")
    : (it.src === "book" ? "15-minute book" : `Lesson ${esc(it.src)}`);
  $("fb").innerHTML = head + meaning(it) + (src ? `<div class="dfb-src">${src}</div>` : "");
  $("next").hidden = false;
}

function finish(firstTime) {
  st.done = true; st.asked++;
  if (firstTime) st.right++;
  reveal(); paint(); $("next").focus();
}

function answerPick(b) {
  if (st.done) return;
  if (+b.dataset.j === st.item) {
    b.classList.add("ok");
    $("opts").querySelectorAll(".opt").forEach((o) => { o.disabled = true; });
    finish(!st.missed);
  } else {
    st.missed = true; b.classList.add("no"); b.disabled = true;
  }
}

function answerTyped(e) {
  e.preventDefault();
  if (st.done) { ask(); return; }
  const it = items()[st.item];
  const given = fold($("answer").value);
  if (!given) return;
  const ok = (st.mode === "k2r-t" ? it.ar : it.am).includes(given);
  $("answer").classList.toggle("no", !ok);
  if (ok) finish(!st.missed);
  else { st.missed = true; $("fb").innerHTML = `<div class="dfb-src">Not quite. Try again, or Show.</div>`; }
}

function choose(el, key, after) {
  el.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-k]");
    if (!b) return;
    st[key] = b.dataset.k; store(`ho.kd.${key === "mode" ? "mode2" : key}`, st[key]);
    after?.();
    st.right = 0; st.asked = 0; st.item = null;
    ask();
  });
}

$("pick").innerHTML = DATA.kanji.map((k) => `<button type="button" data-c="${esc(k.c)}">${k.no ? `<small>${k.no}</small>` : ""}${esc(k.c)}</button>`).join("");
$("pick").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-c]");
  if (!b) return;
  const c = b.dataset.c;
  if (st.picked.has(c)) st.picked.delete(c); else st.picked.add(c);
  store("ho.kd.picked", [...st.picked]);
  st.item = null; ask();
});
$("pick-none").addEventListener("click", () => { st.picked.clear(); store("ho.kd.picked", []); ask(); });
for (const id of ["from", "to"]) {
  $(id).max = bookMax; $(id).value = st[id];
  $(id).addEventListener("change", () => {
    st[id] = Math.min(bookMax, Math.max(1, +$(id).value || 1)); $(id).value = st[id];
    store(`ho.kd.${id}`, st[id]); st.item = null; ask();
  });
}
choose($("what"), "what", renderModes);
choose($("modes"), "mode");
choose($("which"), "which");
$("opts").addEventListener("click", (e) => { const b = e.target.closest(".opt"); if (b) answerPick(b); });
$("typed").addEventListener("submit", answerTyped);
$("reveal").addEventListener("click", () => { if (!st.done) { st.missed = true; finish(false); } });
$("next").addEventListener("click", ask);
renderModes();
ask();
