// Kanji drill, both ways: read a word written in kanji (pick its kana), or
// write a word heard as kana (pick its kanji). Distractors are chosen by the
// build; here we only draw from them. Nothing is saved but the chosen mode.
import { stored, store } from "./prefs.js";
import { esc, ruby, translations } from "./ruby.js";

const { items } = JSON.parse(document.getElementById("data").textContent);
const $ = (id) => document.getElementById(id);
const OPTIONS = 4;

const st = { mode: stored("ho.kd.mode", "read"), src: stored("ho.kd.src", "all"), item: null, done: false, right: 0, asked: 0 };
if (!["read", "write"].includes(st.mode)) st.mode = "read";

const pool = () => items.map((_, i) => i).filter((i) => st.src === "all" || items[i].src === st.src);
const pick = (xs) => xs[Math.floor(Math.random() * xs.length)];

function sample(xs, n) {
  const a = [...xs];
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a.slice(0, n);
}

function paint() {
  $("modes").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.k === st.mode)));
  $("srcs").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.k === st.src)));
  $("score").textContent = st.asked ? `${st.right} / ${st.asked} right` : "";
}

function ask() {
  const ids = pool();
  if (!ids.length) { $("q").textContent = "No words here yet."; $("opts").innerHTML = ""; return; }
  let i = pick(ids);
  if (ids.length > 1) while (i === st.item) i = pick(ids);
  st.item = i; st.done = false;
  const it = items[i];
  const field = st.mode === "read" ? "r" : "w";
  const wrong = sample(st.mode === "read" ? it.dr : it.dw, OPTIONS - 1);
  const opts = sample([i, ...wrong], OPTIONS);
  $("q").innerHTML = st.mode === "read"
    ? `<div class="dq-ja" lang="ja">${esc(it.w)}</div>`
    : `<div class="dq-ja" lang="ja">${esc(it.r)}</div>${translations(it)}`;
  $("opts").innerHTML = opts.map((j) => `<button type="button" class="btn opt" lang="ja" data-j="${j}">${esc(items[j][field])}</button>`).join("");
  $("fb").innerHTML = "";
  $("next").hidden = true;
  paint();
}

function answer(b) {
  if (st.done) return;
  const it = items[st.item];
  const ok = +b.dataset.j === st.item;
  if (ok) {
    st.done = true;
    if (!$("opts").querySelector(".no")) st.right++;
    st.asked++;
    b.classList.add("ok");
    $("opts").querySelectorAll(".opt").forEach((o) => { o.disabled = true; });
    $("fb").innerHTML = `<div class="dfb-ja" lang="ja">${ruby(it.ja)}</div>${translations(it)}`
      + `<div class="dfb-src">${it.src === "book" ? "15-minute book" : `Lesson ${esc(it.src)}`}</div>`;
    $("next").hidden = false;
    $("next").focus();
    paint();
  } else {
    b.classList.add("no"); b.disabled = true;
  }
}

function controls(el, key, storeKey) {
  el.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
    st[key] = b.dataset.k; store(storeKey, st[key]);
    st.right = 0; st.asked = 0; st.item = null;
    ask();
  }));
}

controls($("modes"), "mode", "ho.kd.mode");
controls($("srcs"), "src", "ho.kd.src");
$("opts").addEventListener("click", (e) => { const b = e.target.closest(".opt"); if (b) answer(b); });
$("next").addEventListener("click", ask);
if (st.src !== "all" && !items.some((it) => it.src === st.src)) st.src = "all";
ask();
