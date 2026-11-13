// Phrase book view. Data (parsed ruby, search text, verb tables) comes from the build.
import { stored, store } from "./prefs.js";
import { esc, plainText, ruby, translations } from "./ruby.js";
import { sayButton } from "./speech.js";

const DATA = JSON.parse(document.getElementById("data").textContent);
const TOPIC = Object.fromEntries(DATA.topics.map((t) => [t.id, t]));
const $ = (id) => document.getElementById(id);

// Search folds: case, ё/е, katakana/hiragana; romaji ignores long vowels and は=wa.
const kataToHira = (s) => s.replace(/[ァ-ヶ]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0x60));
const fold = (s) => kataToHira(s.toLowerCase().replace(/ё/g, "е"));
const foldRomaji = (s) => s.toLowerCase()
  .replace(/[āâ]/g, "a").replace(/[īî]/g, "i").replace(/[ūû]/g, "u").replace(/[ēê]/g, "e").replace(/[ōô]/g, "o")
  .replace(/ou|oo|uu|aa|ii|ee/g, (m) => m[0])
  .replace(/ha/g, "wa").replace(/[^a-z ]/g, "");
// Indexed with and without word spaces, so "watashiwa" and "watashi wa" both match.
const romajiIndex = (lines) => {
  const s = foldRomaji(lines.filter(Boolean).join(" "));
  return s + " " + s.replace(/ /g, "");
};
const ROMAJI_TERM = /^[a-zāīūēōâîûêô]+$/;

const phrases = DATA.phrases.map((p, id) => ({
  ...p,
  id,
  idx: fold(p.search),
  idxR: romajiIndex([p.ro, p.casual_ro, ...p.answers.map((a) => a.ro), ...p.examples.map((a) => a.ro)]),
}));

const st = { topic: stored("ho.pb.topic", "all"), kind: "all", cas: stored("ho.pb.cas", false), ro: stored("ho.pb.ro", false), q: "" };
if (st.topic !== "all" && !TOPIC[st.topic]) st.topic = "all";

const colorStyle = (t) => `--c-l:${t.color};--c-d:${t.color_dark}`;

// Topic chips
const chips = $("topics");
function chip(id, label, jp, t) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "chip" + (t ? " tc" : "");
  b.dataset.t = id;
  if (t) b.style.cssText = colorStyle(t);
  b.innerHTML = (t ? "<i></i>" : "") + `<b lang="ja">${esc(jp)}</b>${esc(label)}`;
  b.addEventListener("click", () => {
    st.topic = id; store("ho.pb.topic", id);
    st.q = ""; $("q").value = "";
    render(); window.scrollTo({ top: 0 });
  });
  chips.append(b);
}
chip("all", "All", "全部", null);
DATA.topics.forEach((t) => chip(t.id, t.en, t.jp, t));

function segmented(el, items, onClick) {
  for (const [k, label] of items) {
    const b = document.createElement("button");
    b.type = "button"; b.dataset.k = k; b.textContent = label;
    b.addEventListener("click", () => { onClick(k); render(); });
    el.append(b);
  }
}
segmented($("kinds"), [["all", "ALL"], ["say", "SAY"], ["hear", "HEAR"], ["tip", "TIPS"]], (k) => { st.kind = k; });
segmented($("opts"), [["cas", "CASUAL"], ["ro", "RŌMAJI"]], (k) => { st[k] = !st[k]; store(`ho.pb.${k}`, st[k]); });

function paintControls() {
  $("kinds").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(st.kind === b.dataset.k)));
  $("opts").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(st[b.dataset.k])));
  const cur = st.q.trim() ? "all" : st.topic;
  chips.querySelectorAll(".chip").forEach((b) => b.setAttribute("aria-pressed", String(cur === b.dataset.t)));
  $("out").classList.toggle("showcas", st.cas);
  $("out").classList.toggle("showro", st.ro);
}

const CHEVRON = '<svg class="chev" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>';

const ro = (s) => (s ? `<div class="rol">${esc(s)}</div>` : "");

function lines(list) {
  return `<div class="ans">${list.map((a) => `<div><div class="jps" lang="ja">${ruby(a.ja)}${sayButton(a.say)}</div>${ro(a.ro)}${translations(a)}</div>`).join("")}</div>`;
}

function verbTable(v) {
  const rows = v.forms.map((f) => `<tr><th>${esc(f.label)}</th><td><span class="cj" lang="ja">${ruby(f.ja)}</span><span class="ro">${esc(f.romaji)}</span></td><td>${esc(f.meaning)}</td></tr>`).join("");
  return `<details class="conj"><summary><span class="cj" lang="ja">${ruby(v.dict)}</span> <span class="ro">${esc(v.romaji)}</span> · to ${esc(v.gloss)} <small>${esc(v.kind)}</small></summary>`
    + `<div class="tw"><table>${rows}</table></div>`
    + `<div class="clinks"><a href="https://en.wiktionary.org/wiki/${encodeURIComponent(v.wiktionary)}#Japanese" target="_blank" rel="noopener">Wiktionary</a>`
    + `<a href="https://www.japandict.com/?s=${encodeURIComponent(v.lookup)}" target="_blank" rel="noopener">JapanDict</a></div></details>`;
}

// The expanded part of a card is built on first open.
function more(p) {
  let h = "";
  if (p.casual.length) h += `<div class="blk"><h4>${p.kind === "say" ? "Casual (friends)" : "Casual version you may hear"}</h4><div class="jps" lang="ja">${ruby(p.casual)}</div>${ro(p.casual_ro)}</div>`;
  if (p.answers.length) h += `<div class="blk"><h4>You can answer</h4>${lines(p.answers)}</div>`;
  if (p.examples.length) h += `<div class="blk"><h4>Examples</h4>${lines(p.examples)}</div>`;
  if (p.note.length) h += `<div class="blk"><h4>Note</h4><div class="note">${ruby(p.note)}</div></div>`;
  if (p.words.length) h += `<div class="blk"><h4>Dictionary · JapanDict</h4><div class="dict">${p.words.map(([k, r]) => `<a href="https://www.japandict.com/?s=${encodeURIComponent(k)}" target="_blank" rel="noopener" lang="ja">${esc(k)}<small>${esc(r)}</small></a>`).join("")}</div></div>`;
  if (p.verbs.length) h += `<div class="blk"><h4>Verbs · conjugation</h4>${p.verbs.map((i) => verbTable(DATA.verbs[i])).join("")}</div>`;
  h += `<div class="actions"><button class="btn" type="button" data-act="show">Show full screen</button><button class="btn" type="button" data-act="copy">Copy Japanese</button></div>`;
  return h;
}

function card(p) {
  const t = TOPIC[p.topic];
  if (p.kind === "tip") return `<div class="card tip tc" style="${colorStyle(t)}"><div class="kind tip">知る · tip</div><div class="tiptext">${ruby(p.note)}</div></div>`;
  const label = p.kind === "say" ? "言う · you say" : "聞く · you hear";
  return `<div class="card ${p.kind} tc" style="${colorStyle(t)}" tabindex="0" data-id="${p.id}">${CHEVRON}`
    + `<div class="kind ${p.kind}">${label}${p.level ? `<span class="lv">${esc(p.level)}</span>` : ""}</div>`
    + `<div class="jpl" lang="ja">${ruby(p.ja)}${sayButton(p.say)}</div>${ro(p.ro)}`
    + (p.casual.length ? `<div class="cas-inline" lang="ja">${ruby(p.casual)}</div><div class="rol cas-ro">${esc(p.casual_ro)}</div>` : "")
    + translations(p) + `<div class="more"></div></div>`;
}

function matches(p, terms) {
  return terms.every((t) => p.idx.includes(t) || (ROMAJI_TERM.test(t) && p.idxR.includes(foldRomaji(t))));
}

function render() {
  paintControls();
  const terms = st.q.trim() ? fold(st.q.trim()).split(/\s+/) : [];
  const list = phrases.filter((p) => (terms.length || st.topic === "all" || p.topic === st.topic)
    && (st.kind === "all" || p.kind === st.kind) && matches(p, terms));
  $("count").textContent = list.filter((p) => p.kind !== "tip").length + (terms.length ? " found in all topics" : " phrases");
  if (!list.length) {
    $("out").innerHTML = `<div class="empty">Nothing matches “${esc(st.q)}”. Try another word, or switch the filter to ALL.</div>`;
    return;
  }
  let h = "", lastT = null, lastS = null;
  for (const p of list) {
    if (p.topic !== lastT) {
      if (lastT !== null) h += "</div></section>";
      const t = TOPIC[p.topic];
      h += `<section class="topic tc" style="${colorStyle(t)}"><div class="board"><span class="jp" lang="ja">${esc(t.jp)}</span><span class="en">${esc(t.en)}</span></div>`;
      lastT = p.topic; lastS = null;
    }
    if (p.section !== lastS) {
      if (lastS !== null) h += "</div>";
      h += `<h3 class="sec">${esc(p.section)}</h3><div class="list">`;
      lastS = p.section;
    }
    h += card(p);
  }
  $("out").innerHTML = h + "</div></section>";
}

function toggle(c) {
  const m = c.querySelector(".more");
  if (!m.childElementCount) m.innerHTML = more(phrases[+c.dataset.id]);
  c.classList.toggle("open");
}

$("out").addEventListener("click", (e) => {
  const b = e.target.closest("[data-act]");
  if (b) {
    e.stopPropagation();
    const p = phrases[+b.closest(".card").dataset.id];
    if (b.dataset.act === "copy") {
      const txt = plainText(p.ja);
      const done = () => { b.textContent = "Copied"; setTimeout(() => { b.textContent = "Copy Japanese"; }, 1200); };
      if (navigator.clipboard) navigator.clipboard.writeText(txt).then(done, () => { b.textContent = txt; });
      else b.textContent = txt;
    } else {
      $("showbig").innerHTML = ruby(p.ja);
      $("showsub").textContent = p.en;
      $("show").hidden = false;
    }
    return;
  }
  if (e.target.closest("a") || e.target.closest("details")) return;
  const c = e.target.closest(".card[data-id]");
  if (c) toggle(c);
});
$("out").addEventListener("keydown", (e) => {
  if ((e.key === "Enter" || e.key === " ") && e.target.matches(".card[data-id]")) { e.preventDefault(); toggle(e.target); }
});
$("showclose").addEventListener("click", () => { $("show").hidden = true; });
$("show").addEventListener("click", (e) => { if (e.target.id === "show") $("show").hidden = true; });
let timer;
$("q").addEventListener("input", (e) => { clearTimeout(timer); timer = setTimeout(() => { st.q = e.target.value; render(); }, 120); });
render();
