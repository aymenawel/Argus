// The setup wizard's rules (lib/setup.ts): what each step needs before it can be left, and new vessel labels.
import assert from "node:assert/strict";
import { test } from "node:test";
import { inReadingOrder, nextLabel, stepProblems, type WizardState, type WizardVessel } from "../lib/setup.ts";
import type { Preview } from "../lib/types.ts";

const ROI: [number, number][] = [
  [0, 0],
  [10, 0],
  [10, 10],
];

function stateWith(vessels: Partial<WizardVessel>[], extra: Partial<WizardState> = {}): WizardState {
  return {
    source: { kind: "webcam", camera_index: 0, paths: [] },
    vessels: vessels.map((v, i) => ({ label: `V${i}`, role: null, condition: null, roi: ROI, ...v })),
    preview: null,
    plan: null,
    ...extra,
  };
}

const PREVIEW: Preview = {
  frame_jpeg_b64: "",
  calibration: { card: "standard", px_per_mm: 3.05, rel_uncertainty: 0.004 },
  quality: { blur: 120, flags: [] },
  vessels: [],
};

test("the source step needs a camera or a video", () => {
  assert.deepEqual(stepProblems("source", stateWith([], { source: null })), ["Choose a camera or a video."]);
  assert.deepEqual(
    stepProblems("source", stateWith([], { source: { kind: "video", camera_index: null, paths: [] } })),
    ["Choose a camera or a video."],
  );
  assert.deepEqual(stepProblems("source", stateWith([])), []);
});

test("the vessels step needs at least one vessel", () => {
  assert.deepEqual(stepProblems("vessels", stateWith([])), ["Draw at least one vessel."]);
  assert.deepEqual(stepProblems("vessels", stateWith([{ label: "A" }])), []);
});

test("the roles step needs a role on every vessel and one control", () => {
  assert.deepEqual(stepProblems("roles", stateWith([{ label: "A", role: "treatment" }])), [
    "Mark at least one vessel as control.",
  ]);
  assert.deepEqual(stepProblems("roles", stateWith([{ label: "A", role: "control" }, { label: "B" }])), [
    "Give vessel B a role.",
  ]);
  assert.deepEqual(
    stepProblems(
      "roles",
      stateWith([
        { label: "A", role: "control" },
        { label: "B", role: "treatment" },
      ]),
    ),
    [],
  );
});

test("the check step needs the card or a ruler found", () => {
  assert.deepEqual(stepProblems("check", stateWith([{ label: "A" }])), ["Check the frame first."]);
  const none = { ...PREVIEW, calibration: null };
  assert.equal(stepProblems("check", stateWith([{ label: "A" }], { preview: none })).length, 1);
  assert.deepEqual(stepProblems("check", stateWith([{ label: "A" }], { preview: PREVIEW })), []);
});

test("the plan step needs the metric, the direction, the smallest effect and the checkpoint", () => {
  const plan = {
    hypothesis: "Warm water spreads dye faster.",
    prediction: "",
    threshold: "",
    rivals: [],
    metric: null,
    direction: null,
    min_effect: null,
    checkpoint_s: null,
    treatment: null,
  };
  assert.equal(stepProblems("plan", stateWith([], { plan })).length, 4);
  const done = { ...plan, metric: "delta_e", direction: "higher" as const, checkpoint_s: 300, min_effect: 5 };
  assert.deepEqual(stepProblems("plan", stateWith([], { plan: done })), []);
  assert.deepEqual(stepProblems("plan", stateWith([])), ["Write the plan."]);
});

test("new vessel labels skip the ones in use", () => {
  assert.equal(nextLabel([{ label: "A" }, { label: "C" }]), "B");
  assert.equal(nextLabel([]), "A");
});

test("regions are labelled A, B, C in reading order", () => {
  const box = (x: number, y: number): [number, number][] => [
    [x, y],
    [x + 40, y],
    [x + 40, y + 60],
    [x, y + 60],
  ];
  const drawn = [box(300, 4), box(0, 0), box(150, 120), box(20, 118)].map((roi) => ({
    label: "?",
    role: null,
    condition: null,
    roi,
  }));
  const labelled = inReadingOrder(drawn);
  assert.deepEqual(
    labelled.map((v) => [v.label, v.roi[0][0]]),
    [
      ["A", 0],
      ["B", 300],
      ["C", 20],
      ["D", 150],
    ],
  );
});
