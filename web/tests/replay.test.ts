// Replay mode (D-83): the app reads a recorded run bundle instead of the worker. Run with `npm test`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { afterEach, beforeEach, test } from "node:test";
import { ApiError, frameUrl, getFits, getRun, postNote } from "../lib/api.ts";
import { resultsHref, runHref } from "../lib/links.ts";
import {
  type BundleManifest,
  bundleFile,
  isReplayPath,
  mapFramePath,
  originalSize,
  setActiveBundle,
} from "../lib/replay.ts";

const manifest = {
  run_id: "run_1",
  experiment_id: "exp_1",
  experiment_title: "Dye in warm and room water",
  source_label: "imported recording",
  credit: null,
  licence: null,
  dataset_url: null,
  recorded: "2026-10-29T10:00:00+00:00",
  exported_at: "2026-10-31T09:00:00+00:00",
  commit: "abc1234",
  frames: { total: 2, shown: 1, note: "1 frame in 2 shown; measurements use all 2 frames", scale: 1.5 },
  frame_map: { frm_a: "frm_a", frm_b: "frm_a" },
  media: [],
  verdict: null,
} satisfies BundleManifest;

const realFetch = globalThis.fetch;

beforeEach(() => {
  process.env.NEXT_PUBLIC_ARGUS_REPLAY = "1";
  setActiveBundle(manifest);
});

afterEach(() => {
  process.env.NEXT_PUBLIC_ARGUS_REPLAY = "";
  setActiveBundle(null);
  globalThis.fetch = realFetch;
});

test("bundle file names match the worker's fixture", () => {
  const fixture = new URL("../../worker/tests/fixtures/bundle_paths.json", import.meta.url);
  const cases: { path: string; query: string; file: string }[] = JSON.parse(readFileSync(fixture, "utf8"));
  for (const c of cases) assert.equal(bundleFile(c.path, c.query), c.file);
});

test("an unsafe query value is refused", () => {
  assert.throws(() => bundleFile("/api/runs/r/fits", "metric=a%2Fb"));
  assert.throws(() => bundleFile("/api/runs/../fits", ""));
});

test("only the replay, its bundles and assets pass the gate", () => {
  const open = [
    "/replay",
    "/replay/run_1",
    "/replay/run_1/results",
    "/bundles/index.json",
    "/_next/static/x.js",
    "/icon.svg",
    "/apple-icon.png",
    "/favicon.ico",
    "/__nextjs_font/x",
  ];
  for (const p of open) assert.equal(isReplayPath(p), true, p);
  for (const p of ["/", "/replayx", "/experiments/e/run", "/settings", "/kit", "/bundlesx"]) {
    assert.equal(isReplayPath(p), false, p);
  }
});

test("writes are refused in replay mode without a request", async () => {
  globalThis.fetch = (() => {
    throw new Error("no request expected");
  }) as typeof fetch;
  await assert.rejects(
    postNote("run_1", { t: 0, tag: "observation", text: "x" }),
    (e: ApiError) => e.status === 405 && e.detail === "This is a read-only replay",
  );
});

test("reads come from the active bundle", async () => {
  let asked = "";
  globalThis.fetch = (async (url: string) => {
    asked = url;
    return Response.json({ ok: 1 });
  }) as typeof fetch;
  await getFits("run_1", "delta_e");
  assert.equal(asked, "/bundles/run_1/api/runs/run_1/fits__metric=delta_e.json");
});

test("a recorded 404 raises the same ApiError", async () => {
  globalThis.fetch = (async () =>
    Response.json({ argus_recorded_error: 404, detail: "run not found" })) as typeof fetch;
  await assert.rejects(getRun("run_1"), (e: ApiError) => e.status === 404 && e.detail === "run not found");
});

test("a missing bundle file says which", async () => {
  globalThis.fetch = (async () => new Response("", { status: 404 })) as typeof fetch;
  await assert.rejects(
    getRun("run_1"),
    (e: ApiError) => e.status === 404 && e.detail.includes("/bundles/run_1/api/runs/run_1.json"),
  );
});

test("with no bundle open, reads fail plainly", async () => {
  setActiveBundle(null);
  await assert.rejects(getRun("run_1"), (e: ApiError) => e.status === 404 && e.detail === "no replayed run is open");
});

test("frames and their outlines map through the manifest", () => {
  assert.equal(frameUrl("run_1", "frm_b", 160), "/bundles/run_1/frames/frm_a.jpg");
  assert.equal(
    mapFramePath("/api/runs/run_1/frames/frm_b/detections", manifest),
    "/api/runs/run_1/frames/frm_a/detections",
  );
  assert.equal(mapFramePath("/api/runs/run_1/timeline", manifest), "/api/runs/run_1/timeline");
});

test("a shrunk frame is drawn over in the original frame's pixels", () => {
  assert.deepEqual(originalSize(1280, 720), { w: 1920, h: 1080 });
  setActiveBundle(null);
  assert.deepEqual(originalSize(1280, 720), { w: 1280, h: 720 });
});

test("links point at the replay routes in replay mode", () => {
  assert.equal(resultsHref("exp_1", "run_1"), "/replay/run_1/results");
  assert.equal(runHref("exp_1", "run_1"), "/replay/run_1");
  process.env.NEXT_PUBLIC_ARGUS_REPLAY = "";
  assert.equal(resultsHref("exp_1", "run_1"), "/experiments/exp_1/results");
  assert.equal(runHref("exp_1", "run_1"), "/experiments/exp_1/run");
});
