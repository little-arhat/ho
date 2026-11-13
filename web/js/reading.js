// Reading texts: tap a word to see its reading, meaning and the lesson it comes from.
import { esc, ruby, translations } from "./ruby.js";

const { words } = JSON.parse(document.getElementById("data").textContent);
const pop = document.getElementById("pop");
let open = null;

function show(b) {
  const w = words[+b.dataset.w];
  pop.innerHTML = `<div class="pop-ja" lang="ja">${ruby(w.ja)}</div>${translations(w)}`
    + `<div class="pop-src">${w.lesson === null ? "new word" : `lesson ${esc(w.lesson)}`}</div>`;
  pop.hidden = false;
  const r = b.getBoundingClientRect(), host = pop.offsetParent.getBoundingClientRect();
  const left = Math.max(0, Math.min(r.left - host.left, host.width - pop.offsetWidth));
  pop.style.left = `${left}px`;
  pop.style.top = `${r.bottom - host.top + 6}px`;
  open?.classList.remove("on");
  b.classList.add("on");
  open = b;
}

function hide() { pop.hidden = true; open?.classList.remove("on"); open = null; }

document.getElementById("rt").addEventListener("click", (e) => {
  const b = e.target.closest(".rt-w");
  if (!b) return;
  if (b === open) hide(); else show(b);
});
document.addEventListener("click", (e) => { if (open && !e.target.closest(".rt-w, #pop")) hide(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") hide(); });
