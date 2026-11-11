// Site-wide display preferences: which translation languages show, and
// whether furigana shows. Applied as attributes on <html>; CSS does the hiding.
// Stored in localStorage when it is available; the page works without it.

export const LANGS = ["en", "ru", "uk"];
const KEY = "ho.prefs";
const DEFAULT = { langs: ["en", "ru", "uk"], furigana: true };

// Per-browser storage for small conveniences; null/defaults when unavailable.
export function stored(key, fallback) {
  try {
    const v = localStorage.getItem(key);
    return v === null ? fallback : JSON.parse(v);
  } catch (e) { return fallback; }
}

export function store(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* not persisted */ }
}

function read() {
  const v = stored(KEY, null);
  if (v && Array.isArray(v.langs) && v.langs.length && v.langs.every((l) => LANGS.includes(l))) {
    return { langs: v.langs, furigana: v.furigana !== false };
  }
  return { ...DEFAULT, langs: [...DEFAULT.langs] };
}

let current = read();

export function prefs() {
  return { langs: [...current.langs], furigana: current.furigana };
}

function apply() {
  const html = document.documentElement;
  html.dataset.langs = current.langs.join(" ");
  html.dataset.furigana = current.furigana ? "on" : "off";
  document.querySelectorAll("#prefs button").forEach((b) => {
    const on = b.dataset.lang ? current.langs.includes(b.dataset.lang) : current.furigana;
    b.setAttribute("aria-pressed", String(on));
  });
  document.dispatchEvent(new CustomEvent("ho:prefs", { detail: prefs() }));
}

function toggleLang(lang) {
  const has = current.langs.includes(lang);
  if (has && current.langs.length === 1) return;
  const langs = has ? current.langs.filter((l) => l !== lang) : LANGS.filter((l) => l === lang || current.langs.includes(l));
  current = { ...current, langs };
  store(KEY, current);
  apply();
}

function toggleFurigana() {
  current = { ...current, furigana: !current.furigana };
  store(KEY, current);
  apply();
}

function mount() {
  const el = document.getElementById("prefs");
  if (!el) return;
  const group = document.createElement("div");
  group.className = "seg";
  for (const lang of LANGS) {
    const b = document.createElement("button");
    b.type = "button";
    b.dataset.lang = lang;
    b.textContent = lang.toUpperCase();
    b.addEventListener("click", () => toggleLang(lang));
    group.append(b);
  }
  const furi = document.createElement("button");
  furi.type = "button";
  furi.lang = "ja";
  furi.textContent = "ふりがな";
  furi.addEventListener("click", toggleFurigana);
  const g2 = document.createElement("div");
  g2.className = "seg";
  g2.append(furi);
  el.append(group, g2);
}

mount();
apply();
