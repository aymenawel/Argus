// The words a reader with no lab training sees (lib/plain.ts, D-95): the worker's argus/plain.py, on the page.
import assert from "node:assert/strict";
import { test } from "node:test";
import { formatDuration } from "../lib/chart.ts";
import { chipTitle, curveWords, metricWords, roleWord, unitLabel, withoutLabel } from "../lib/plain.ts";

test("a measurement is named in everyday words", () => {
  assert.equal(metricWords("delta_e"), "colour change");
  assert.equal(metricWords("germinated_count"), "sprouted seeds");
  assert.equal(metricWords("some_new_metric"), "some new metric");
});

test("units read as people write them", () => {
  assert.equal(unitLabel("dE00"), "ΔE");
  assert.equal(unitLabel("mm2"), "mm²");
  assert.equal(unitLabel("dE00/h"), "ΔE per hour");
  assert.equal(unitLabel("mm"), "mm");
});

test("a treatment is a test sample", () => {
  assert.equal(roleWord("treatment"), "test");
  assert.equal(roleWord("control"), "control");
});

test("a curve is named by its shape", () => {
  assert.equal(curveWords("logistic"), "S-shaped");
  assert.equal(curveWords("first_order"), "fast, then slowing");
});

test("a time under an hour reads in minutes", () => {
  assert.equal(formatDuration([0.0628, 0.0005]), "3.77 ± 0.03 min");
  assert.equal(formatDuration([21.4, 0.6]), "21.4 ± 0.6 h");
});

test("a note field does not start with its own name", () => {
  assert.equal(withoutLabel("observation: The glass is clear.", "observation"), "The glass is clear.");
  assert.equal(withoutLabel("Interpretation: this fits.", "interpretation"), "This fits.");
  assert.equal(withoutLabel("Observations agree.", "observation"), "Observations agree.");
});

test("an event chip says what happened", () => {
  assert.equal(chipTitle("Time of the intervention event"), "Time a hand or object was at the samples");
  assert.equal(chipTitle("Time of the rule event"), "Time a set threshold was crossed");
  assert.equal(chipTitle("Run time now"), "Run time now");
});
