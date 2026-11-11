// Rendering helpers shared by pages. Japanese arrives as segments
// [[text], [base, reading], ...] prepared by the build; nothing here parses notation.

export const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

export function ruby(segments) {
  return segments.map((s) => (s.length === 1 ? esc(s[0]) : `<ruby>${esc(s[0])}<rt>${esc(s[1])}</rt></ruby>`)).join("");
}

export function plainText(segments) {
  return segments.map((s) => s[0]).join("");
}

// Translations as a definition list; CSS shows only the selected languages.
export function translations(t) {
  return `<dl class="tr">${["en", "ru", "uk"].filter((l) => t[l]).map((l) => `<dt class="tr-${l}">${l.toUpperCase()}</dt><dd class="tr-${l}">${esc(t[l])}</dd>`).join("")}</dl>`;
}
