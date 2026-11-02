// How often SAM found each vessel's object, and how a missed stretch is drawn (lib/misses.ts, D-90).
import assert from "node:assert/strict";
import { test } from "node:test";
import { coverageLines, markEnd, outlineCaption, outlinedByCode } from "../lib/misses.ts";
import type { DetectionOutline, RunEvent } from "../lib/types.ts";

test("coverage reads as pictures found, how they were found, and misses since the first find", () => {
  const c = { concept: "microbial colony", asked: 145, found: 14, first_found_t: 40320, missed_after: 131 };
  assert.deepEqual(coverageLines(c, 86400), ["14 of 145 pictures", null, "not found in 131 since 11:12"]);
  assert.deepEqual(coverageLines({ ...c, found: 145, missed_after: 0 }, 86400), ["145 of 145 pictures", null, null]);
  assert.deepEqual(coverageLines({ ...c, found: 0, first_found_t: null, missed_after: 0 }, 86400), [
    "0 of 145 pictures",
    null,
    "never found",
  ]);
  assert.deepEqual(coverageLines(undefined, 86400), ["—", null, null]); // a bundle published before coverage existed
  assert.deepEqual(coverageLines(null, 86400), ["—", null, null]); // a run from before SAM's answers were kept
  const split = { ...c, found: 97, missed_after: 3, by_name: 55, pointed: 30, by_code: 12 };
  assert.deepEqual(coverageLines(split, 86400), [
    "97 of 145 pictures",
    "55 by name · 30 by pointing · 12 by code",
    "not found in 3 since 11:12",
  ]);
  const byName = { ...c, by_name: 14, pointed: 0, by_code: 0 }; // all by name: nothing to split (D-93)
  assert.equal(coverageLines(byName, 86400)[1], null);
  const noCode = { ...c, found: 123, by_name: 92, pointed: 31, by_code: 0 }; // a way that found nothing isn't listed
  assert.equal(coverageLines(noCode, 86400)[1], "92 by name · 31 by pointing");
});

test("an outline drawn by code is told apart from SAM's", () => {
  const d: DetectionOutline = { vessel_id: "v", track_key: "k", concept: "c", outline: [], confidence: null };
  assert.equal(outlinedByCode({ ...d, backend: "change-map" }), true);
  assert.equal(outlinedByCode({ ...d, backend: "sam-3.1/pointed" }), false);
  assert.equal(outlinedByCode(d), false); // a bundle published before outlines said who drew them
});

test("the frame's caption counts SAM's objects and the outlines code drew", () => {
  const d: DetectionOutline = { vessel_id: "v", track_key: "k", concept: "c", outline: [], confidence: null };
  const sam = { ...d, backend: "sam-3.1/image" };
  const code = { ...d, backend: "change-map" };
  assert.equal(outlineCaption([sam]), "SAM 3.1 · 1 object");
  assert.equal(outlineCaption([]), "SAM 3.1 · 0 objects");
  assert.equal(outlineCaption([sam, sam, code]), "SAM 3.1 · 2 objects · 1 outlined by code (dashed)");
});

test("an open miss runs to the end of the run; other open events are a mark", () => {
  const e: RunEvent = {
    id: "e",
    vessel_id: "v",
    t_start: 100,
    t_end: null,
    kind: "missed",
    source: "pipeline",
    detail: {},
  };
  assert.equal(markEnd(e, 900), 900);
  assert.equal(markEnd({ ...e, t_end: 300 }, 900), 300);
  assert.equal(markEnd({ ...e, kind: "quality" }, 900), 100);
});
