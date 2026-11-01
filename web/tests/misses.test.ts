// How often SAM found each vessel's object, and how a missed stretch is drawn (lib/misses.ts, D-90).
import assert from "node:assert/strict";
import { test } from "node:test";
import { coverageLines, markEnd } from "../lib/misses.ts";
import type { RunEvent } from "../lib/types.ts";

test("coverage reads as pictures found and misses since the first find", () => {
  const c = { concept: "microbial colony", asked: 145, found: 14, first_found_t: 40320, missed_after: 131 };
  assert.deepEqual(coverageLines(c, 86400), ["14 of 145 pictures", "not found in 131 since 11:12"]);
  assert.deepEqual(coverageLines({ ...c, found: 145, missed_after: 0 }, 86400), ["145 of 145 pictures", null]);
  assert.deepEqual(coverageLines({ ...c, found: 0, first_found_t: null, missed_after: 0 }, 86400), [
    "0 of 145 pictures",
    "never found",
  ]);
  assert.deepEqual(coverageLines(undefined, 86400), ["—", null]); // a bundle published before coverage existed
  assert.deepEqual(coverageLines(null, 86400), ["—", null]); // a run from before SAM's answers were kept
});

test("an open miss runs to the end of the run; other open events are a mark", () => {
  const e: RunEvent = { id: "e", vessel_id: "v", t_start: 100, t_end: null, kind: "missed", source: "pipeline", detail: {} };
  assert.equal(markEnd(e, 900), 900);
  assert.equal(markEnd({ ...e, t_end: 300 }, 900), 300);
  assert.equal(markEnd({ ...e, kind: "quality" }, 900), 100);
});
