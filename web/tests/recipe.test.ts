// A drafted recipe in words, and the edits the "What will you do?" dialog makes to it (lib/recipe.ts).
import assert from "node:assert/strict";
import { test } from "node:test";
import { detailOf } from "../lib/api.ts";
import { addMeasurement, quantityUnit, recipeInWords, renameConcept, stepInWords, withMethod } from "../lib/recipe.ts";
import type { RecipeSpec, Tool } from "../lib/types.ts";

const TOOLBOX: Tool[] = [
  { method: "area", family: "size", unit: "mm2", words: "the area" },
  { method: "skeleton_length", family: "size", unit: "mm", words: "the length" },
  { method: "touching_count", family: "count", unit: "count", words: "how many touch" },
];

const GERMINATION: RecipeSpec = {
  id: "own",
  version: 1,
  title: "Germination speed in petri dishes",
  default_mode: "continuous",
  analysis_step_s: 1800,
  curve: "logistic",
  rivals: ["position in the frame"],
  default_views: [],
  watcher: { signals: ["ssim", "colour"], light_normalization: "normal", day_night: false },
  concepts: [{ name: "seed" }, { name: "root" }],
  measurements: [
    { id: "root_length", family: "size", method: "skeleton_length", from: "root", unit: "mm" },
    {
      id: "germinated",
      family: "count",
      method: "touching_count",
      from: "seed",
      unit: "count",
      touching: "root",
      min_length_mm: 2,
    },
  ],
  events: [],
  main_measurement: "germinated",
};

test("a germination draft reads as what Argus looks for, measures and how often", () => {
  assert.deepEqual(recipeInWords(GERMINATION), {
    lookFor: "seed, root",
    measure: "root length (mm), seeds with a root (count)",
    every: "every 30 min",
  });
});

test("a fast step reads in seconds", () => {
  assert.equal(recipeInWords({ ...GERMINATION, analysis_step_s: 0.5 }).every, "every 0.5 s");
  assert.equal(stepInWords(7200), "2 h");
  assert.equal(stepInWords(90), "1.5 min");
});

test("renaming a concept renames what reads from it and what it touches", () => {
  const renamed = renameConcept(GERMINATION, "root", "radicle");
  assert.deepEqual(
    renamed.concepts.map((c) => c.name),
    ["seed", "radicle"],
  );
  assert.equal(renamed.measurements[0].from, "radicle");
  assert.equal(renamed.measurements[1].touching, "radicle");
});

test("choosing a method takes its family and unit from the toolbox", () => {
  const area = withMethod(GERMINATION.measurements[1], TOOLBOX[0], GERMINATION);
  assert.deepEqual([area.method, area.family, area.unit], ["area", "size", "mm2"]);
  assert.equal(area.touching, null);
  assert.equal(area.min_length_mm, null);
  const touching = withMethod(GERMINATION.measurements[0], TOOLBOX[2], GERMINATION);
  assert.equal(touching.touching, "seed"); // another concept than the one it reads from
  assert.equal(touching.min_length_mm, 2);
});

test("an added measurement gets a name of its own", () => {
  const once = addMeasurement(GERMINATION, TOOLBOX[0], "seed");
  const twice = addMeasurement(once, TOOLBOX[0], "seed");
  assert.deepEqual(
    twice.measurements.slice(2).map((m) => m.id),
    ["seed_area", "seed_area_2"],
  );
});

test("a refusal's reasons read as sentences", () => {
  assert.equal(
    detailOf({ detail: ["concepts: too long", "curve: unknown"] }, "x"),
    "concepts: too long; curve: unknown",
  );
  assert.equal(detailOf({ detail: [{ msg: "field required" }] }, "x"), "field required");
});

test("a grown count reads as the objects that grew, and keeps its own minimum", () => {
  const grown: RecipeSpec = {
    ...GERMINATION,
    measurements: [
      { id: "germinated", family: "count", method: "grown_count", from: "seed", unit: "count", min_length_mm: 2 },
    ],
  };
  assert.equal(recipeInWords(grown).measure, "seeds that grew 2 mm (count)");
  const tool: Tool = { method: "grown_count", family: "count", unit: "count", words: "grew" };
  const switched = withMethod(GERMINATION.measurements[0], tool, GERMINATION);
  assert.equal(switched.touching, null);
  assert.equal(switched.min_length_mm, 2);
});

test("the smallest effect is in the unit of what the plan compares", () => {
  assert.equal(quantityUnit(null, "count"), "count");
  assert.equal(quantityUnit("level", "mm"), "mm");
  assert.equal(quantityUnit("half_time", "count"), "h");
  assert.equal(quantityUnit("rate", "count"), "count/h");
});
