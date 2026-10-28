// The Run view's data store (lib/run-snapshot.ts): run with `npm test` (Node's own test runner, no packages).
import assert from "node:assert/strict";
import { test } from "node:test";
import { SnapshotStore, type RunSnapshot } from "../lib/run-snapshot.ts";
import type { MeasurementRow, RunView, Timeline } from "../lib/types.ts";

const VIEW = { running: true, spend_usd: 0, vessels: [], calibration: null } as unknown as RunView;

function by(id: string, t: number): MeasurementRow {
  const display = `${t} mm`;
  return { id, vessel_id: "A", frame_id: null, t, metric: "length", value: t, uncertainty: 0.1, unit: "mm", display };
}

const timeline = (measurements: MeasurementRow[]): Timeline => ({ frames: [], measurements, events: [] });

function harness() {
  const seen: RunSnapshot[] = [];
  const jobs: (() => void)[] = [];
  const store = new SnapshotStore(
    (s) => seen.push(s),
    (flush) => jobs.push(flush),
  );
  const frame = () => jobs.splice(0).forEach((flush) => flush()); // one animation frame
  return { store, seen, frame };
}

test("events published while a reload is in flight are kept", () => {
  const { store } = harness();
  store.beginLoad();
  store.finishLoad(VIEW, timeline([by("a", 1)]));
  store.beginLoad(); // a resync: the page reloads from REST
  store.receive("measurement", { ...by("b", 2) }); // published meanwhile, after REST read its rows
  const reloaded = store.finishLoad(VIEW, timeline([by("a", 1)]));
  assert.deepEqual(
    reloaded.measurements.map((m) => m.id),
    ["a", "b"],
  );
});

test("a burst of events makes one update, in time order, without duplicates", () => {
  const { store, seen, frame } = harness();
  store.beginLoad();
  store.finishLoad(VIEW, timeline([by("a", 1)]));
  seen.length = 0;
  for (let i = 0; i < 3000; i++) store.receive("measurement", { ...by(`r${i}`, 2 + i) });
  store.receive("measurement", { ...by("a", 1) }); // already there
  store.receive("measurement", { ...by("late", 1.5) }); // arrived out of order
  assert.equal(seen.length, 0);
  frame();
  assert.equal(seen.length, 1);
  const ids = seen[0].measurements.map((m) => m.id);
  assert.equal(ids.length, 3002);
  assert.deepEqual(ids.slice(0, 3), ["a", "late", "r0"]);
});

test("an event that closes gets its end time", () => {
  const { store, seen, frame } = harness();
  store.beginLoad();
  store.finishLoad(VIEW, timeline([]));
  store.receive("event", { id: "evt_1", t: 60, kind: "quality", vessel_id: null, detail: { message: "m" } });
  store.receive("event", { id: "evt_1", t: 60, t_end: 180, kind: "quality", vessel_id: null, detail: {} });
  frame();
  const [event] = seen.at(-1)!.events;
  assert.deepEqual([event.t_start, event.t_end, seen.at(-1)!.events.length], [60, 180, 1]);
});
