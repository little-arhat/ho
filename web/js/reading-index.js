// The reading list's lesson filter: all texts, or those that use one lesson's words.
import { stored, store } from "./prefs.js";

const KEY = "ho.rd.filter";
const bar = document.getElementById("rdfilter");
let current = stored(KEY, "all");

function apply() {
  if (!bar.querySelector(`[data-f="${current}"]`)) current = "all";
  bar.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.f === current)));
  document.querySelectorAll(".rd-list li[data-f]").forEach((li) => {
    li.hidden = current !== "all" && !li.dataset.f.split(" ").includes(current);
  });
  document.querySelectorAll(".rd-sec").forEach((s) => { s.hidden = !s.querySelector("li[data-f]:not([hidden])"); });
}

bar.addEventListener("click", (e) => {
  const b = e.target.closest("button[data-f]");
  if (!b) return;
  current = b.dataset.f;
  store(KEY, current);
  apply();
});
apply();
