// Lesson exercises: pick the missing word, or put the words in order. Checked here, nothing saved.
import { LANGS } from "./prefs.js";
import { esc, ruby } from "./ruby.js";

const EXERCISES = JSON.parse(document.getElementById("data").textContent);
const list = document.getElementById("exercise-list");

const translation = (x) => `<div class="ex-tr">${LANGS.map((l) => `<span class="tl tr-${l}" data-l="${l.toUpperCase()}">${esc(x[l])}</span>`).join("")}</div>`;
const plain = (segs) => segs.map((s) => s[0]).join("");

function shuffled(n) {
  const order = [...Array(n).keys()];
  do {
    for (let i = n - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [order[i], order[j]] = [order[j], order[i]]; }
  } while (n > 1 && order.every((v, i) => v === i));
  return order;
}

function choice(x, el) {
  el.innerHTML = `<div class="q" lang="ja">${ruby(x.before)}<span class="gap">＿</span>${ruby(x.after)}</div>${translation(x)}`
    + `<div class="opts" lang="ja">${x.options.map((o, i) => `<button type="button" class="btn opt" data-i="${i}">${ruby(o)}</button>`).join("")}</div>`
    + `<div class="verdict" aria-live="polite"></div>`;
  const gap = el.querySelector(".gap"), verdict = el.querySelector(".verdict");
  el.querySelectorAll(".opt").forEach((b) => b.addEventListener("click", () => {
    const i = +b.dataset.i;
    if (i === x.answer) {
      gap.innerHTML = ruby(x.options[i]); gap.classList.add("ok");
      el.querySelectorAll(".opt").forEach((o) => { o.disabled = true; });
      b.classList.add("ok"); verdict.textContent = "Right.";
    } else {
      b.classList.add("no"); b.disabled = true; verdict.textContent = "Not this one. Try again.";
    }
  }));
}

function reorder(x, el) {
  const answer = x.parts.map(plain).join("");
  const order = shuffled(x.parts.length);
  el.innerHTML = `<div class="built" lang="ja"></div>${translation(x)}`
    + `<div class="opts" lang="ja">${order.map((i) => `<button type="button" class="btn piece" data-i="${i}">${ruby(x.parts[i])}</button>`).join("")}</div>`
    + `<div class="row"><button type="button" class="btn undo">Undo</button><span class="verdict" aria-live="polite"></span></div>`;
  const built = el.querySelector(".built"), verdict = el.querySelector(".verdict");
  const picked = [];
  const paint = () => {
    built.innerHTML = picked.map((i) => `<span class="chunk">${ruby(x.parts[i])}</span>`).join("") || '<span class="hint">Tap the pieces in order</span>';
    el.querySelectorAll(".piece").forEach((b) => { b.disabled = picked.includes(+b.dataset.i); });
    if (picked.length < x.parts.length) { verdict.textContent = ""; built.classList.remove("ok", "no"); return; }
    const right = picked.map((i) => plain(x.parts[i])).join("") === answer;
    built.classList.toggle("ok", right); built.classList.toggle("no", !right);
    verdict.textContent = right ? "Right." : "Not quite. Undo and try again.";
  };
  el.querySelectorAll(".piece").forEach((b) => b.addEventListener("click", () => { picked.push(+b.dataset.i); paint(); }));
  el.querySelector(".undo").addEventListener("click", () => { picked.pop(); paint(); });
  paint();
}

EXERCISES.forEach((x, n) => {
  const el = document.createElement("div");
  el.className = "exercise";
  el.dataset.n = String(n + 1);
  list.append(el);
  (x.kind === "choice" ? choice : reorder)(x, el);
});
