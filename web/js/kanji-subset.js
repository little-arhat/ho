// The "From" picker shared by the kanji drills (templates/_kanji_from.html):
// all kanji, the 15-minute book (a number range), one lesson's kanji, or a
// hand-picked set. The choice is remembered per page under `prefix`.
import { stored, store } from "./prefs.js";
import { esc } from "./ruby.js";

export function kanjiSubset(data, prefix, onChange) {
  const $ = (id) => document.getElementById(id);
  const bookNo = Object.fromEntries(data.kanji.filter((k) => k.no).map((k) => [k.c, k.no]));
  const bookMax = Math.max(...Object.values(bookNo));
  const st = {
    which: stored(`${prefix}.which`, "all"),
    from: stored(`${prefix}.from`, 1),
    to: stored(`${prefix}.to`, bookMax),
    picked: new Set(stored(`${prefix}.picked`, [])),
  };
  if (!(st.which in data.sets) && !["all", "custom"].includes(st.which)) st.which = "all";

  // null means every kanji
  function set() {
    if (st.which === "all") return null;
    if (st.which === "custom") return st.picked;
    if (st.which === "book") return new Set(data.sets.book.filter((c) => bookNo[c] >= st.from && bookNo[c] <= st.to));
    return new Set(data.sets[st.which]);
  }

  function paint() {
    $("which").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.k === st.which)));
    $("range-row").hidden = st.which !== "book";
    $("pick-row").hidden = st.which !== "custom";
    $("pick").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(st.picked.has(b.dataset.c))));
  }

  const changed = () => { paint(); onChange(); };

  $("which").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-k]");
    if (!b) return;
    st.which = b.dataset.k; store(`${prefix}.which`, st.which); changed();
  });
  $("pick").innerHTML = data.kanji.map((k) => `<button type="button" data-c="${esc(k.c)}">${k.no ? `<small>${k.no}</small>` : ""}${esc(k.c)}</button>`).join("");
  $("pick").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-c]");
    if (!b) return;
    const c = b.dataset.c;
    if (st.picked.has(c)) st.picked.delete(c); else st.picked.add(c);
    store(`${prefix}.picked`, [...st.picked]); changed();
  });
  $("pick-none").addEventListener("click", () => { st.picked.clear(); store(`${prefix}.picked`, []); changed(); });
  for (const id of ["from", "to"]) {
    $(id).max = bookMax; $(id).value = st[id];
    $(id).addEventListener("change", () => {
      st[id] = Math.min(bookMax, Math.max(1, +$(id).value || 1)); $(id).value = st[id];
      store(`${prefix}.${id}`, st[id]); changed();
    });
  }
  paint();
  return { set, isCustom: () => st.which === "custom" };
}
