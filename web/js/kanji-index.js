// Kanji index: filter (all, the 15-minute book's kanji, or those a lesson's
// vocabulary uses), search, and romaji under the readings. Each tile carries
// its search entries (data-s, folded by the build the way fold() folds).
import { stored, store } from "./prefs.js";
import { fold } from "./match.js";

const $ = (id) => document.getElementById(id);
const bar = $("kfilter");
let current = stored("ho.ki.filter", "all");
let romaji = stored("ho.ki.ro", false);

function apply() {
  if (!bar.querySelector(`[data-f="${current}"]`)) current = "all";
  bar.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.f === current)));
  $("kro").setAttribute("aria-pressed", String(romaji));
  document.body.classList.toggle("showro", romaji);
  const q = fold($("kq").value);
  let shown = 0;
  document.querySelectorAll(".k-grid li").forEach((li) => {
    li.hidden = (current !== "all" && !li.dataset.f.split(" ").includes(current))
      || (q !== "" && !li.dataset.s.includes(q));
    if (!li.hidden) shown++;
  });
  document.querySelectorAll(".k-sec").forEach((s) => { s.hidden = !s.querySelector(".k-grid li:not([hidden])"); });
  $("knone").hidden = shown > 0;
}

bar.addEventListener("click", (e) => {
  const b = e.target.closest("button[data-f]");
  if (!b) return;
  current = b.dataset.f; store("ho.ki.filter", current); apply();
});
$("kro").addEventListener("click", () => { romaji = !romaji; store("ho.ki.ro", romaji); apply(); });
$("kq").addEventListener("input", apply);
apply();
