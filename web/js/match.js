// Answer checking. Accepted answers come from the build.

// Typed meanings and readings: width, case, ё/е, Spanish accents (á/a, ü/u),
// katakana/hiragana and all spaces and punctuation folded away. Must match
// ho.kanji.fold in Python.
const ACCENTS = { á: "a", é: "e", í: "i", ó: "o", ú: "u", ü: "u" };
export const fold = (s) => s.normalize("NFKC").toLowerCase().replace(/ё/g, "е").replace(/[áéíóúü]/g, (c) => ACCENTS[c])
  .replace(/[ァ-ヶ]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0x60))
  .replace(/[^\p{L}\p{N}]+/gu, "");

// List search. The build writes each item's index as folded words joined by
// spaces (ho.kanji.search_tokens); a query is split into words the same way.
// Every query word must match some index word: a Japanese one anywhere in it
// (計 finds 時計), any other at its start (wat finds watch, eat misses great).
const WORD_SEPARATOR = /[\s,;/()[\]]+/u;
const JAPANESE = /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}]/u;

export function searchMatches(tokens, query) {
  return query.split(WORD_SEPARATOR).map(fold).filter((w) => w !== "").every((w) => JAPANESE.test(w)
    ? tokens.some((t) => t.includes(w))
    : tokens.some((t) => t.startsWith(w)));
}

// Romaji answers for the katakana drill: the accepted spellings per token.

export function normalize(s) {
  return s.normalize("NFKC").toLowerCase()
    .replace(/\s+/g, "")
    .replace(/[’‘`´ʼ]/g, "'")
    .replace(/[ー―‐‑–—−]/g, "-");
}

const quote = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

export function matcher(alts) {
  const rx = new RegExp("^" + alts.map((a) => "(?:" + a.map(quote).join("|") + ")").join("") + "$");
  return (s) => rx.test(s);
}

export function accepts(alts, s) {
  return matcher(alts)(s);
}
