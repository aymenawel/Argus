// What the Run view derives from a snapshot (lib/run-data.ts): run with `npm test`.
import assert from "node:assert/strict";
import { test } from "node:test";
import { byVessel, regionAt, runNotice } from "../lib/run-data.ts";
import type { MeasurementRow, RunEvent, RunView, Vessel } from "../lib/types.ts";

const row = (vessel: string, t: number, metric = "length") =>
  ({ id: `${vessel}${t}${metric}`, vessel_id: vessel, t, metric }) as MeasurementRow;

const event = (kind: RunEvent["kind"], t: number, detail: Record<string, unknown> = {}): RunEvent => ({
  id: `${kind}${t}`,
  vessel_id: null,
  t_start: t,
  t_end: null,
  kind,
  source: "pipeline",
  detail,
});

test("rows are grouped per vessel, in order, for the metrics asked", () => {
  const rows = [row("A", 0), row("B", 0), row("A", 1), row("A", 1, "colour_l"), row("A", 2)];
  const groups = byVessel(rows, new Set(["length"]));
  assert.deepEqual(
    groups.get("A")!.map((r) => r.t),
    [0, 1, 2],
  );
  assert.equal(groups.get("B")!.length, 1);
});

test("after a camera move the vessel's region is the moved one", () => {
  const vessel = {
    id: "A",
    roi: [
      [0, 0],
      [10, 0],
      [10, 10],
    ],
  } as unknown as Vessel;
  const moved = event("camera_moved", 100, {
    rois: {
      A: [
        [40, 30],
        [50, 30],
        [50, 40],
      ],
    },
  });
  const cardOnly = event("camera_moved", 200, { message: "card moved: recalibrated" });
  assert.deepEqual(regionAt(vessel, [moved, cardOnly], 50), vessel.roi);
  assert.deepEqual(regionAt(vessel, [moved, cardOnly], 250), [
    [40, 30],
    [50, 30],
    [50, 40],
  ]);
});

test("notices say why a run stopped, and drop the calibration notice once calibrated", () => {
  const calibrated = { calibration: { id: "cal" } } as unknown as RunView;
  const uncalibrated = { calibration: null } as unknown as RunView;
  const lost = runNotice([event("interrupted", 9, { reason: "camera_lost" })], uncalibrated);
  assert.match(lost ?? "", /camera stopped sending frames/);
  const crashed = runNotice([event("interrupted", 9, { error: "ValueError: bad" })], uncalibrated);
  assert.match(crashed ?? "", /an error.*ValueError: bad/);
  assert.equal(runNotice([event("no_calibration", 0)], calibrated), null);
  assert.match(runNotice([event("no_calibration", 0)], uncalibrated) ?? "", /No Argus Card/);
});
