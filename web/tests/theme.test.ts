// The clean-lab look is the default (D-98): a viewer who never chose gets light, whatever their system prefers.
import assert from "node:assert/strict";
import { test } from "node:test";
import { readTheme, THEME_SCRIPT } from "../lib/theme.ts";

test("with nothing chosen the theme is light", () => {
  assert.equal(readTheme(), "light");
});

test("the head script marks only a chosen dark or system theme", () => {
  assert.match(THEME_SCRIPT, /"dark"/);
  assert.match(THEME_SCRIPT, /"system"/);
  assert.doesNotMatch(THEME_SCRIPT, /"light"/);
});
