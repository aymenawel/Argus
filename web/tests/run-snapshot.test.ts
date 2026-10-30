// The Run view's data store (lib/run-snapshot.ts): run with `npm test` (Node's own test runner, no packages).
import assert from "node:assert/strict";
import { test } from "node:test";
import { SnapshotStore, type RunSnapshot } from "../lib/run-snapshot.ts";
import type { MeasurementRow, Note, RunView, Timeline, Verdict } from "../lib/types.ts";

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

function note(id: string, t: number, extra: Partial<Note> = {}): Note {
  return {
    id,
    run_id: "run_1",
    t,
    t_end: null,
    author: "ai",
    level: "checkpoint",
    tag: null,
    body: { observation: "No change." },
    refs: [],
    evidence: [],
    check_status: "passed",
    model_call_id: null,
    ...extra,
  };
}

function verdict(id: string, level: Verdict["verdict"]): Verdict {
  return {
    id,
    run_id: "run_1",
    t: 600,
    provisional: true,
    allowed: [level],
    checks: [],
    verdict: level,
    body: {
      explanation: "",
      rivals: [],
      what_would_change_it: "",
      confidence: "low",
      confidence_reason: "",
      findings: [],
      written_by: "model",
      critique_dropped: [],
    },
    draft: {},
    critique: null,
    refs: [],
    model_call_ids: [],
    fell_back: false,
  };
}

test("notes and the verdict come with the first load", () => {
  const { store } = harness();
  store.beginLoad();
  const loaded = store.finishLoad(VIEW, timeline([]), {
    notes: { notes: [note("n2", 240), note("n1", 120)], rejected: 2 },
    verdict: verdict("v1", "TOO_EARLY"),
  });
  assert.deepEqual(
    loaded.notes.map((n) => n.id),
    ["n1", "n2"],
  );
  assert.equal(loaded.rejected, 2);
  assert.equal(loaded.verdict?.id, "v1");
});

test("a collapsed note updates in place", () => {
  const { store, seen, frame } = harness();
  store.beginLoad();
  store.finishLoad(VIEW, timeline([]));
  store.receive("note", { run_id: "run_1", t: 120, note: note("n1", 120) });
  store.receive("note", { run_id: "run_1", t: 240, note: note("n1", 120, { t_end: 240 }) });
  store.receive("note", {
    run_id: "run_1",
    t: 60,
    note: note("n0", 60, { author: "researcher", tag: "intervention" }),
  });
  frame();
  const notes = seen.at(-1)!.notes;
  assert.deepEqual(
    notes.map((n) => [n.id, n.t_end]),
    [
      ["n0", null],
      ["n1", 240],
    ],
  );
});

test("a rejected note bumps the count without adding a note", () => {
  const { store, seen, frame } = harness();
  store.beginLoad();
  store.finishLoad(VIEW, timeline([]));
  store.receive("note_rejected", {
    run_id: "run_1",
    t: 120,
    attempt_id: "att_1",
    reasons: ["number outside a ref: 25"],
  });
  frame();
  assert.equal(seen.at(-1)!.rejected, 1);
  assert.deepEqual(seen.at(-1)!.notes, []);
});

test("a verdict event replaces the verdict", () => {
  const { store, seen, frame } = harness();
  store.beginLoad();
  store.finishLoad(VIEW, timeline([]));
  store.receive("verdict", { run_id: "run_1", t: 600, verdict: verdict("v1", "TOO_EARLY") });
  store.receive("verdict", { run_id: "run_1", t: 700, verdict: verdict("v2", "INCONCLUSIVE") });
  frame();
  assert.equal(seen.at(-1)!.verdict?.id, "v2");
});

test("each note keeps the model that wrote it, from the load and from live notes", () => {
  const { store, seen, frame } = harness();
  store.beginLoad();
  const loaded = store.finishLoad(VIEW, timeline([]), {
    notes: { notes: [note("n1", 120, { model_call_id: "mc_1" })], rejected: 0, models: { mc_1: "muse-spark-1.3" } },
    verdict: null,
  });
  assert.deepEqual(loaded.models, { mc_1: "muse-spark-1.3" });
  store.receive("note", {
    run_id: "run_1",
    t: 240,
    note: note("n2", 240, { model_call_id: "mc_2" }),
    model: "meta-models/muse-spark-open-1026",
  });
  frame();
  assert.deepEqual(seen.at(-1)!.models, { mc_1: "muse-spark-1.3", mc_2: "meta-models/muse-spark-open-1026" });
});
