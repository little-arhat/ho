// Romaji answer checking. The accepted spellings per token come from the build.

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
