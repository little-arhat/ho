// Answer checking. Accepted answers come from the build.

// Typed meanings and readings: width, case, ё/е, katakana/hiragana and all
// spaces and punctuation folded away. Must match ho.kanji.fold in Python.
export const fold = (s) => s.normalize("NFKC").toLowerCase().replace(/ё/g, "е")
  .replace(/[ァ-ヶ]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0x60))
  .replace(/[^\p{L}\p{N}]+/gu, "");

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
