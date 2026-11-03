// The Argus line (D-98): one or two sentences built by code from stored readings and the verdict, never by a model.
import assert from "node:assert/strict";
import { test } from "node:test";
import { argusLine, checkCounts } from "../lib/summary.ts";

const DYE = [
  { label: "A", role: "treatment", condition: "cold", first: 0.04, latest: [3.12, 0.05] },
  { label: "B", role: "control", condition: "room", first: 0.05, latest: [4.55, 0.06] },
  { label: "C", role: "treatment", condition: "warm", first: 0.03, latest: [25.12, 0.06] },
] as const;

const line = (overrides: Partial<Parameters<typeof argusLine>[0]> = {}) =>
  argusLine({
    samples: DYE.map((s) => ({ ...s, latest: [...s.latest] as [number, number] })),
    metric: "delta_e",
    unit: "dE00",
    verdict: null,
    checkTime: null,
    ...overrides,
  });

test("the sample that changed most leads, against the control", () => {
  assert.equal(
    line().lead,
    "Sample C (test, warm) changed the most: 25.12 ± 0.06 ΔE, against 4.55 ± 0.06 ΔE for the control (B).",
  );
});

test("the verdict's sentence and level follow", () => {
  const verdict = { level: "TOO_EARLY" as const, sentence: "The plan was written after this run's data was recorded." };
  const said = line({ verdict });
  assert.equal(said.detail, verdict.sentence);
  assert.equal(said.level, "TOO_EARLY");
});

test("without a verdict, the plan's check time says when Argus will judge", () => {
  assert.equal(line({ checkTime: "2:00" }).detail, "Argus judges your idea from 2:00.");
  assert.equal(line().detail, null);
});

test("a run with no control makes no comparison", () => {
  const alone = DYE.filter((s) => s.role !== "control").map((s) => ({
    ...s,
    latest: [...s.latest] as [number, number],
  }));
  assert.equal(line({ samples: alone }).lead, "Sample C (test, warm) changed the most: 25.12 ± 0.06 ΔE.");
});

test("nothing measured yet", () => {
  const empty = DYE.map((s) => ({ ...s, first: null, latest: null }));
  assert.equal(line({ samples: empty }).lead, "Argus is watching. Nothing measured yet.");
});

test("a count reads as the thing counted", () => {
  const seeds = [
    {
      label: "pg1-2",
      role: "treatment" as const,
      condition: "pearl millet",
      first: 0,
      latest: [9, 0] as [number, number],
    },
    { label: "sc1-1", role: "control" as const, condition: "rye", first: 0, latest: [8, 0] as [number, number] },
  ];
  assert.equal(
    line({ samples: seeds, metric: "germinated_count", unit: "count" }).lead,
    "Sample pg1-2 (test, pearl millet) changed the most: 9 sprouted seeds, against 8 sprouted seeds for the control (sc1-1).",
  );
});

test("the checks are counted in words, zero groups left out", () => {
  assert.equal(checkCounts([{ ok: true }, { ok: null }, { ok: false }]), "1 passed · 1 not settled · 1 failed");
  assert.equal(checkCounts([{ ok: true }, { ok: true }]), "2 passed");
  assert.equal(checkCounts([]), "No checks yet");
});
