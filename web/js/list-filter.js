// A list page's filter (all, or one group key from data-f), search and romaji
// toggle; see templates/_list_tools.html. Each item carries its search entries
// in data-s, folded by the build the way fold() folds, so only the query is folded here.
import { stored, store } from "./prefs.js";
import { fold } from "./match.js";

const $ = (id) => document.getElementById(id);
const bar = $("ixfilter");
const key = $("ixtools").dataset.store;
let current = stored(`${key}.filter`, "all");
let romaji = stored(`${key}.ro`, false);

function apply() {
  if (!bar.querySelector(`[data-f="${current}"]`)) current = "all";
  bar.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.f === current)));
  $("ixro").setAttribute("aria-pressed", String(romaji));
  document.body.classList.toggle("showro", romaji);
  const q = fold($("ixq").value);
  let shown = 0;
  document.querySelectorAll(".ix-sec li[data-s]").forEach((li) => {
    li.hidden = (current !== "all" && !li.dataset.f.split(" ").includes(current))
      || (q !== "" && !li.dataset.s.includes(q));
    if (!li.hidden) shown++;
  });
  document.querySelectorAll(".ix-sec").forEach((s) => { s.hidden = !s.querySelector("li[data-s]:not([hidden])"); });
  $("ixnone").hidden = shown > 0;
}

bar.addEventListener("click", (e) => {
  const b = e.target.closest("button[data-f]");
  if (!b) return;
  current = b.dataset.f; store(`${key}.filter`, current); apply();
});
$("ixro").addEventListener("click", () => { romaji = !romaji; store(`${key}.ro`, romaji); apply(); });
$("ixq").addEventListener("input", apply);
apply();
