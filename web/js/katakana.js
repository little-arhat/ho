// Katakana drill: read a loanword, type it in romaji. Accepted spellings come from the build.
import { esc } from "./ruby.js";
import { matcher, normalize } from "./match.js";
import { prefs } from "./prefs.js";

const DECK = JSON.parse(document.getElementById("data").textContent).map((w) => ({
  ...w,
  ok: matcher(w.exact),
  nearLong: matcher(w.near_long),
  nearGem: matcher(w.near_gem),
  nearBoth: matcher(w.near_both),
}));

const $ = (id) => document.getElementById(id);
const face = $("face"), kana = $("kana"), slot = $("slot"), input = $("answer"), note = $("note");
const band = $("band"), stat = $("stat"), num = $("num");
const prevKana = $("prevKana"), prevSub = $("prevSub"), nextKana = $("nextKana"), nextSub = $("nextSub");
const revealBtn = $("reveal"), soundBtn = $("sound"), restartBtn = $("restart");
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

let queue = [], pos = 0, misses = 0, revealed = false, firstTry = 0, answered = 0, prevWord = null, finished = false;
const requeued = new Set();

const meaning = (w) => prefs().langs.map((l) => w[l]).join(" / ");

function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}

/* sound */
let ac = null, soundOn = true;
function unlockAudio() {
  if (!ac) { try { ac = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { ac = null; } }
  if (ac && ac.state === "suspended") ac.resume();
}
function tone(freq, at, dur, type, gain) {
  if (!ac || !soundOn) return;
  const t = ac.currentTime + at, o = ac.createOscillator(), g = ac.createGain();
  o.type = type; o.frequency.setValueAtTime(freq, t);
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(gain, t + 0.012);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.connect(g); g.connect(ac.destination);
  o.start(t); o.stop(t + dur + 0.03);
}
const chime = () => { tone(1046.5, 0, 0.18, "sine", 0.22); tone(1318.5, 0.09, 0.28, "sine", 0.2); };
const buzz = () => { tone(150, 0, 0.24, "square", 0.06); tone(112, 0, 0.24, "square", 0.05); if (soundOn && navigator.vibrate) navigator.vibrate(70); };

/* ui */
function setNote(html, cls) { note.className = "kt-note" + (cls ? " " + cls : ""); note.innerHTML = html; }

function fitKana() {
  const len = [...kana.textContent].length || 1;
  const avail = face.clientWidth - 36;
  kana.style.fontSize = Math.max(28, Math.min(76, Math.floor(avail / (len * 1.07)))) + "px";
}

function updateStat() {
  stat.textContent = answered ? `First try ${firstTry} of ${answered}` : "Press return to check";
}

function renderStops() {
  if (prevWord) { prevKana.textContent = prevWord.ja; prevSub.textContent = `${prevWord.macron}, ${meaning(prevWord)}`; }
  else { prevKana.textContent = "始発"; prevSub.textContent = "start"; }
  nextKana.textContent = finished ? "" : "？";
  nextSub.textContent = finished ? "" : `${Math.max(0, queue.length - pos - 1)} to go`;
  num.textContent = String(Math.min(pos + 1, queue.length));
}

function showWord(animate) {
  misses = 0; revealed = false;
  setNote("");
  const w = queue[pos];
  const swap = () => { kana.textContent = w.ja; fitKana(); };
  if (animate && !reduced && kana.animate) {
    const out = kana.animate([{ transform: "translateX(0)", opacity: 1 }, { transform: "translateX(-32px)", opacity: 0 }], { duration: 140, easing: "ease-in" });
    out.onfinish = () => {
      swap();
      kana.animate([{ transform: "translateX(32px)", opacity: 0 }, { transform: "translateX(0)", opacity: 1 }], { duration: 220, easing: "ease-out" });
    };
  } else swap();
  renderStops();
}

function flash(cls, ms) {
  band.classList.remove("hit", "miss");
  void band.offsetWidth;
  band.classList.add(cls);
  setTimeout(() => band.classList.remove(cls), ms);
}

function check() {
  if (finished) return;
  const raw = input.value;
  const v = normalize(raw);
  if (!v) return;
  unlockAudio();
  if (/[぀-ヿ一-鿿]/.test(raw)) {
    input.value = "";
    setNote("Switch to the English keyboard and type in romaji.", "miss");
    return;
  }
  const w = queue[pos];
  if (w.ok(v)) correct(w); else wrong(v, w);
}

function correct(w) {
  answered++;
  if (misses === 0 && !revealed) firstTry++;
  else if (!requeued.has(w.ja)) { requeued.add(w.ja); queue.splice(Math.min(pos + 6, queue.length), 0, w); }
  chime();
  flash("hit", 260);
  prevWord = w;
  input.value = "";
  pos++;
  updateStat();
  if (pos >= queue.length) finish(); else showWord(true);
}

function wrong(v, w) {
  misses++;
  input.value = "";
  const shown = `“${esc(v)}”`;
  let msg;
  if (w.nearLong(v)) msg = `${shown} is close. ー makes the vowel long: double it or use a macron.`;
  else if (w.nearGem(v)) msg = `${shown} is close. ッ doubles the next consonant.`;
  else if (w.nearBoth(v)) msg = `${shown} is close. Check the ー long vowel and the ッ double consonant.`;
  else msg = `${shown} isn't it. Try again.`;
  if (misses >= 3 && !revealed) msg += " Stuck? Tap Show answer.";
  setNote(msg, "miss");
  buzz();
  flash("miss", 450);
  slot.classList.add("miss");
  setTimeout(() => slot.classList.remove("miss"), 450);
  face.classList.remove("shake"); void face.offsetWidth; face.classList.add("shake");
}

function reveal() {
  if (finished) return;
  const w = queue[pos];
  revealed = true;
  let html = `Type <b>${esc(w.typed)}</b>`;
  if (w.macron !== w.typed) html += ` or <b>${esc(w.macron)}</b>`;
  html += `. It means ${esc(meaning(w))}.`;
  setNote(html, "reveal");
  input.focus();
}

function finish() {
  finished = true;
  face.classList.add("done");
  revealBtn.disabled = true;
  kana.textContent = "終点"; fitKana();
  setNote(`End of the line. First try ${firstTry} of ${answered}.`);
  renderStops();
  num.textContent = String(queue.length);
  input.blur();
}

function start() {
  queue = shuffle([...DECK]);
  requeued.clear();
  pos = 0; firstTry = 0; answered = 0; prevWord = null; finished = false;
  face.classList.remove("done");
  revealBtn.disabled = false;
  updateStat();
  showWord(false);
}

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.isComposing) { e.preventDefault(); check(); }
});
// Keep the on-screen keyboard open when tapping buttons.
[revealBtn, soundBtn].forEach((b) => b.addEventListener("mousedown", (e) => e.preventDefault()));
revealBtn.addEventListener("click", reveal);
soundBtn.addEventListener("click", () => {
  soundOn = !soundOn;
  soundBtn.setAttribute("aria-pressed", String(soundOn));
  if (soundOn) { unlockAudio(); chime(); }
  if (!finished) input.focus();
});
restartBtn.addEventListener("click", () => { start(); input.focus(); });
face.addEventListener("click", (e) => { if (!finished && e.target !== input) input.focus(); });
window.addEventListener("resize", fitKana);
document.addEventListener("ho:prefs", () => { if (prevWord) renderStops(); });

start();
input.focus();
