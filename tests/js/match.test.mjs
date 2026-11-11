import { test } from "node:test";
import assert from "node:assert/strict";
import { accepts, normalize } from "../../web/js/match.js";

const coffee = [["koo", "ko-", "kō", "kô"], ["hii", "hi-", "hī", "hî"]];

test("accepts a long-vowel spelling after normalizing", () => {
  assert.equal(accepts(coffee, normalize("Kōhī")), true);
});

test("rejects a missing long vowel", () => {
  assert.equal(accepts(coffee, "kohi"), false);
});

test("normalizes dashes and spaces", () => {
  assert.equal(normalize("ko—hi— "), "ko-hi-");
});
