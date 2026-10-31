// The Videos card's words (lib/media.ts): run with `npm test`.
import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import { mediaUrl } from "../lib/api.ts";
import { formatBytes, videoRow } from "../lib/media.ts";

afterEach(() => {
  process.env.NEXT_PUBLIC_ARGUS_REPLAY = "";
});

test("sizes read like the rest of the app", () => {
  assert.equal(formatBytes(31_400_000), "31.4 MB");
  assert.equal(formatBytes(950_000), "0.9 MB");
});

test("each state offers what can be done", () => {
  assert.deepEqual(videoRow({ state: "none" }, false), { status: "Not made yet", action: "make", download: false });
  assert.deepEqual(videoRow({ state: "running", progress: 0.42 }, false), {
    status: "Making… 42 %",
    action: null,
    download: false,
  });
  assert.deepEqual(videoRow({ state: "ready", size_bytes: 31_400_000, made_at: "2026-11-01T10:00:00Z" }, false), {
    status: "31.4 MB",
    action: "again",
    download: true,
  });
  assert.deepEqual(videoRow({ state: "failed", reason: "ffmpeg is not on PATH" }, false), {
    status: "Failed: ffmpeg is not on PATH",
    action: "again",
    download: false,
  });
});

test("a replay only offers what it carries", () => {
  assert.deepEqual(videoRow({ state: "none" }, true), {
    status: "Not made for this run",
    action: null,
    download: false,
  });
  assert.deepEqual(videoRow({ state: "ready", size_bytes: 6_300_000, made_at: "2026-11-01T10:00:00Z" }, true), {
    status: "6.3 MB",
    action: null,
    download: true,
  });
});

test("downloads come from the worker live and from the bundle in a replay", () => {
  assert.equal(mediaUrl("run_1", "reel"), "http://localhost:8000/api/runs/run_1/media/reel.mp4");
  process.env.NEXT_PUBLIC_ARGUS_REPLAY = "1";
  assert.equal(mediaUrl("run_1", "reel"), "/bundles/run_1/reel.mp4");
});
