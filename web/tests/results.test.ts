// What the Results page says in its own words: a verdict's explanation and a suggested run length (lib/results.ts).
import assert from "node:assert/strict";
import { test } from "node:test";
import { explanationToShow, runLength } from "../lib/results.ts";
import type { Verdict } from "../lib/types.ts";

const LATE = "The plan was locked after this run's data began, so it can't be judged against it.";

function verdict(explanation: string, checks: string[]): Verdict {
  return {
    checks: checks.map((text, i) => ({ id: `c${i}`, ok: false, text, refs: [] })),
    body: { explanation },
  } as unknown as Verdict;
}

test("an explanation that only repeats a check is shown once, in the checks", () => {
  assert.equal(explanationToShow(verdict(LATE, [LATE])), null);
  assert.equal(explanationToShow(verdict("The warm glass changed more.", [LATE])), "The warm glass changed more.");
  assert.equal(explanationToShow(verdict("", [LATE])), null);
});

test("a run length under an hour reads in minutes", () => {
  assert.equal(runLength(2 / 60), "2 min"); // a dye run judged at 2 minutes, not "0.0 h"
  assert.equal(runLength(4.5), "4.5 h");
  assert.equal(runLength(36), "36 h");
});
