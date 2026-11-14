// Kanji writing drill: a prompt (meaning and readings, a word in kana, or a
// sentence with the kanji left blank) to write by hand, then the answer with
// its stroke order. "Again later" brings an item back a few prompts on;
// nothing is saved but the settings. Stroke paths are fetched per kanji
// from ../<hex>/strokes.json (KanjiVG, written by the build).
import { stored, store } from "./prefs.js";
import { esc, ruby, translations } from "./ruby.js";
import { kanjiSubset } from "./kanji-subset.js";
import { sayButton } from "./speech.js";

const DATA = JSON.parse(document.getElementById("data").textContent);
const $ = (id) => document.getElementById(id);
const KANJI = /[㐀-鿿豈-﫿]/u;

const st = {
  kind: stored("ho.kw.kind", "mix"),
  pad: stored("ho.kw.pad", true),
  queue: [], item: null, revealed: false, good: 0, again: 0,
};
const subset = kanjiSubset(DATA, "ho.kw", restart);

// One prompt: what to show, and the characters to write.
function prompts() {
  const set = subset.set();
  const inSet = (c) => !set || set.has(c);
  const out = [];
  const want = (k) => st.kind === "mix" || st.kind === k;
  for (const k of DATA.kanji) {
    if (!inSet(k.c)) continue;
    if (want("meaning")) out.push({ kind: "meaning", k });
    if (want("sentence")) k.sents.forEach((s) => out.push({ kind: "sentence", k, s }));
  }
  for (const w of DATA.words) {
    if (!w.k.length || !w.k.every(inSet)) continue;
    if (want("word")) out.push({ kind: "word", w });
    if (want("listen")) out.push({ kind: "listen", w });
  }
  return out;
}

function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}

function restart() {
  st.queue = shuffle(prompts());
  st.good = 0; st.again = 0;
  next();
}

const answerOf = (p) => (p.w ? p.w.w : p.kind === "sentence" ? p.s.s.find((x) => x[2])[0] : p.k.c);

function promptHtml(p) {
  if (p.kind === "meaning") {
    return `<div class="wq-kind">Write the kanji for</div><div class="dq-mean">${translations(p.k)}</div>`
      + `<div class="wq-hint" lang="ja">${esc(p.k.rd.join("・"))}</div>`;
  }
  if (p.kind === "listen") {
    return `<div class="wq-kind">Write what you hear, in kanji</div><div class="wq-listen">${sayButton(p.w.say, p.w.clip)}</div>`;
  }
  if (p.kind === "word") {
    return `<div class="wq-kind">Write in kanji</div><div class="dq-ja" lang="ja">${esc(p.w.r)}</div>${translations(p.w)}`;
  }
  const sentence = p.s.s.map((x) => (x[2] ? `<span class="wblank">${esc(x[1])}</span>` : ruby([x.slice(0, 2)]))).join("");
  return `<div class="wq-kind">Write the underlined part in kanji</div><div class="wq-sent" lang="ja">${sentence}</div>${translations(p.s)}`;
}

function paint() {
  $("kinds").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.k === st.kind)));
  $("padon").checked = st.pad;
  $("pad").hidden = !st.pad;
  $("clear").hidden = !st.pad;
  const left = st.queue.length + (st.item && !st.revealed ? 1 : 0);
  $("pool").textContent = `${left} prompts left this round`;
  $("score").textContent = st.good + st.again ? `${st.good} got · ${st.again} again` : "";
}

function next() {
  clearPad();
  $("guide").innerHTML = "";
  $("answer").innerHTML = "";
  st.revealed = false;
  $("reveal").hidden = false; $("again").hidden = true; $("good").hidden = true;
  if (!st.queue.length) st.queue = shuffle(prompts());
  st.item = st.queue.shift() || null;
  if (!st.item) {
    $("q").textContent = subset.isCustom() ? "Pick some kanji above." : "Nothing to write here yet.";
    $("reveal").hidden = true;
  } else {
    $("q").innerHTML = promptHtml(st.item);
    if (st.item.kind === "listen") $("q").querySelector(".listen")?.click();
  }
  paint();
}

const strokeCache = new Map();
function strokes(c) {
  if (!strokeCache.has(c)) {
    strokeCache.set(c, fetch(`../${c.codePointAt(0).toString(16)}/strokes.json`).then((r) => (r.ok ? r.json() : [])));
  }
  return strokeCache.get(c);
}

const frame = (paths, i) => `<li><svg viewBox="0 0 109 109" aria-hidden="true"><path class="grid" d="M54.5 0V109M0 54.5H109"/>`
  + paths.slice(0, i + 1).map((d, j) => `<path class="${j === i ? "now" : "done"}" d="${d}"/>`).join("")
  + `</svg><span>${i + 1}</span></li>`;

async function reveal() {
  if (!st.item || st.revealed) return;
  st.revealed = true;
  const p = st.item;
  const target = answerOf(p);
  const chars = [...new Set([...target].filter((c) => KANJI.test(c)))];
  const head = p.w ? ruby(p.w.ja) + (p.kind === "listen" ? translations(p.w) : "") : p.kind === "sentence" ? ruby([p.s.s.find((x) => x[2]).slice(0, 2)]) : esc(target);
  $("answer").innerHTML = `<div class="wa-big" lang="ja">${head}</div>`
    + chars.map((c) => `<div class="wa-char"><a lang="ja" href="../${c.codePointAt(0).toString(16)}/">${esc(c)}</a><ol class="strokes" data-c="${esc(c)}"></ol></div>`).join("");
  $("reveal").hidden = true; $("again").hidden = false; $("good").hidden = false;
  paint();
  for (const c of chars) {
    const paths = await strokes(c);
    const list = $("answer").querySelector(`ol[data-c="${c}"]`);
    if (list) list.innerHTML = paths.map((_, i) => frame(paths, i)).join("");
    if (chars.length === 1 && st.pad) $("guide").innerHTML = paths.map((d) => `<path d="${d}"/>`).join("");
  }
  $("good").focus();
}

function grade(good) {
  if (!st.revealed) return;
  if (good) st.good++;
  else {
    st.again++;
    st.queue.splice(Math.min(st.queue.length, 3 + Math.floor(Math.random() * 3)), 0, st.item);
  }
  next();
}

// Writing box: draw with finger, pen or mouse.
const canvas = $("canvas");
const ctx = canvas.getContext("2d");
let drawing = false;

// Resizing a canvas wipes it, and phones fire resize while scrolling (the
// toolbar), so only a real change of the box resizes, and the ink is kept.
function sizePad() {
  const r = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const w = Math.round(r.width * dpr), h = Math.round(r.height * dpr);
  if (!w || (w === canvas.width && h === canvas.height)) return;
  const ink = canvas.width ? Object.assign(document.createElement("canvas"), { width: canvas.width, height: canvas.height }) : null;
  ink?.getContext("2d").drawImage(canvas, 0, 0);
  canvas.width = w; canvas.height = h;
  if (ink) ctx.drawImage(ink, 0, 0, w, h);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.lineCap = "round"; ctx.lineJoin = "round";
  ctx.lineWidth = Math.max(4, r.width / 40);
  ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue("--fg").trim() || "#000";
}

function clearPad() { ctx.clearRect(0, 0, canvas.width, canvas.height); }

const at = (e) => { const r = canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
canvas.addEventListener("pointerdown", (e) => {
  drawing = true; canvas.setPointerCapture(e.pointerId);
  const [x, y] = at(e); ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + 0.01, y); ctx.stroke();
});
canvas.addEventListener("pointermove", (e) => { if (!drawing) return; const [x, y] = at(e); ctx.lineTo(x, y); ctx.stroke(); });
for (const ev of ["pointerup", "pointercancel"]) canvas.addEventListener(ev, () => { drawing = false; });

$("kinds").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-k]");
  if (!b) return;
  st.kind = b.dataset.k; store("ho.kw.kind", st.kind); restart();
});
$("padon").addEventListener("change", () => { st.pad = $("padon").checked; store("ho.kw.pad", st.pad); paint(); if (st.pad) sizePad(); });
$("clear").addEventListener("click", clearPad);
$("reveal").addEventListener("click", reveal);
$("good").addEventListener("click", () => grade(true));
$("again").addEventListener("click", () => grade(false));
window.addEventListener("resize", () => { if (st.pad) sizePad(); });
document.addEventListener("keydown", (e) => {
  if (e.target.closest("input")) return;
  if (e.key === " " || e.key === "Enter") { e.preventDefault(); if (!st.revealed) reveal(); else grade(true); }
  if (e.key === "a" && st.revealed) grade(false);
});
paint();
sizePad();
restart();
