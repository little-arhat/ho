// Kanji index filter: all, the 15-minute book's kanji, or those a lesson's vocabulary uses.
import { stored, store } from "./prefs.js";

const bar = document.getElementById("kfilter");
let current = stored("ho.ki.filter", "all");

function apply() {
  if (!bar.querySelector(`[data-f="${current}"]`)) current = "all";
  bar.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.f === current)));
  document.querySelectorAll(".k-grid li").forEach((li) => {
    li.hidden = current !== "all" && !li.dataset.f.split(" ").includes(current);
  });
  document.querySelectorAll(".k-sec").forEach((s) => { s.hidden = !s.querySelector(".k-grid li:not([hidden])"); });
}

bar.addEventListener("click", (e) => {
  const b = e.target.closest("button[data-f]");
  if (!b) return;
  current = b.dataset.f; store("ho.ki.filter", current); apply();
});
apply();
