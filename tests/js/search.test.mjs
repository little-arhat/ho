import { test } from "node:test";
import assert from "node:assert/strict";
import { searchMatches } from "../../web/js/match.js";

// Index tokens as the build writes them (ho.kanji.search_tokens): one folded word each.
const watch = ["時計", "とけい", "tokei", "watch", "clock", "часы", "годинник", "reloj"];
const great = ["great", "seat", "heat", "weather", "theater"];

test("a Latin or Cyrillic query matches the start of a word", () => {
  assert.equal(searchMatches(watch, "watch"), true);
  assert.equal(searchMatches(watch, "wat"), true);
  assert.equal(searchMatches(watch, "Час"), true);
  assert.equal(searchMatches(watch, "tok"), true);
});

test("a Latin query does not match inside a word", () => {
  assert.equal(searchMatches(great, "eat"), false);
  assert.equal(searchMatches(watch, "atch"), false);
  assert.equal(searchMatches(watch, "kei"), false);
});

test("a Japanese query matches anywhere in a word", () => {
  assert.equal(searchMatches(watch, "計"), true);
  assert.equal(searchMatches(watch, "けい"), true);
  assert.equal(searchMatches(watch, "ケイ"), true);
});

test("every word of a query must match some token", () => {
  assert.equal(searchMatches(watch, "watch clock"), true);
  assert.equal(searchMatches(watch, "alarm clock"), false);
});

test("an empty query matches everything", () => {
  assert.equal(searchMatches(great, "  "), true);
});
