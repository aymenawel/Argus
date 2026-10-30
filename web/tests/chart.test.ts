// Scales and ticks for the Results page's SVG charts (lib/chart.ts).
import assert from "node:assert/strict";
import { test } from "node:test";
import { conditionGroups, formatPair, groupKey, linearScale, niceTicks } from "../lib/chart.ts";

test("a linear scale maps the domain onto the range, either way round", () => {
  assert.equal(linearScale([0, 10], [0, 100])(5), 50);
  assert.equal(linearScale([0, 10], [200, 0])(10), 0);
  assert.equal(linearScale([3, 3], [0, 100])(3), 0); // an empty domain doesn't divide by zero
});

test("ticks are round steps that cover the range", () => {
  const ticks = niceTicks(0, 47, 5);
  assert.ok(ticks[0] <= 0 && ticks.at(-1)! >= 47, String(ticks));
  const step = ticks[1] - ticks[0];
  assert.ok([1, 2, 5, 10, 20, 50].includes(step), String(step));
  assert.deepEqual(niceTicks(0, 1, 4), [0, 0.5, 1]); // a step of 0.25 rounds up to 0.5
  assert.deepEqual(niceTicks(5, 5, 4), [5]);
});

test("a value and its ± round the uncertainty first, then the value to match", () => {
  assert.equal(formatPair([21.437, 0.6123], "h"), "21.4 ± 0.6 h");
  assert.equal(formatPair([21.437, 0.1523], "h"), "21.44 ± 0.15 h"); // a leading 1 keeps two digits
  assert.equal(formatPair([1234.5, 37], "count"), "1230 ± 40 count");
  assert.equal(formatPair([2.5, 0], "mm"), "2.5 mm");
});

test("treatment conditions are told apart by dash and by dot shape; controls stay solid and round", () => {
  const vessel = (role: "control" | "treatment", value: string) => ({ role, condition: { factor: "salt", value } });
  const groups = conditionGroups([
    vessel("treatment", "50 mM"),
    vessel("control", "0 mM"),
    vessel("treatment", "100 mM"),
    vessel("treatment", "50 mM"),
    vessel("treatment", "150 mM"),
  ]);
  assert.deepEqual(
    [...groups.values()].map((g) => [g.label, g.dash, g.marker]),
    [
      ["Control: 0 mM", undefined, "circle"],
      ["Treatment: 50 mM", undefined, "circle"],
      ["Treatment: 100 mM", "7 4", "square"],
      ["Treatment: 150 mM", "2 4", "diamond"],
    ],
  );
  assert.equal(groups.get(groupKey(vessel("treatment", "100 mM")))?.marker, "square");
});
