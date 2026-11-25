// Reading texts: tap a word to see its reading, meaning and the lesson it comes from;
// switch between the story and the dialog (the choice is remembered).
import { esc, ruby, translations } from "./ruby.js";
import { stored, store } from "./prefs.js";

const { words } = JSON.parse(document.getElementById("data").textContent);
const pop = document.getElementById("pop");
let open = null;

function show(b) {
  const w = words[+b.dataset.w];
  pop.innerHTML = `<div class="pop-ja keep-ruby" lang="ja">${ruby(w.ja)}</div>${translations(w)}`
    + (w.k.length ? `<div class="pop-k" lang="ja">${w.k.map((c) => `<a href="../../kanji/${c.codePointAt(0).toString(16)}/">${esc(c)}</a>`).join("")}</div>` : "")
    + `<div class="pop-src">${w.lesson === null ? "new word" : `lesson ${esc(w.lesson)}`}`
    + ` · <a href="../../words/${encodeURIComponent(w.slug)}/">word page →</a></div>`;
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

const FORM_KEY = "ho.rt.form";
const forms = document.getElementById("forms");

function showForm(form) {
  if (!forms.querySelector(`[data-form="${form}"]`)) form = "prose";
  forms.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.form === form)));
  document.querySelectorAll("#rt > section[data-form]").forEach((s) => { s.hidden = s.dataset.form !== form; });
  hide();
}

forms.addEventListener("click", (e) => {
  const b = e.target.closest("button[data-form]");
  if (!b) return;
  store(FORM_KEY, b.dataset.form);
  showForm(b.dataset.form);
});
showForm(stored(FORM_KEY, "prose"));
