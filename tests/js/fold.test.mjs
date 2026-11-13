import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fold } from "../../web/js/match.js";

const cases = JSON.parse(readFileSync(new URL("../fold_cases.json", import.meta.url), "utf8"));

test("fold matches the shared cases (same as ho.kanji.fold)", () => {
  for (const [input, expected] of cases) assert.equal(fold(input), expected, input);
});
