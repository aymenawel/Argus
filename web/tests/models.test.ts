// Model ids in the words a person reads (lib/models.ts).
import assert from "node:assert/strict";
import { test } from "node:test";
import { modelName } from "../lib/models.ts";

test("Meta's model ids read as their names", () => {
  assert.equal(modelName("muse-spark-1.3"), "Muse Spark 1.3");
  assert.equal(modelName("muse-wonder-1.0"), "Muse Wonder 1.0");
  assert.equal(modelName("meta-models/muse-spark-open-1026"), "Muse Spark Open");
  assert.equal(modelName("meta-models/muse-spark-open"), "Muse Spark Open");
  assert.equal(modelName("sam-3.1"), "SAM 3.1");
  assert.equal(modelName(null), "");
});
