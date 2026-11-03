// Ask Argus (D-97): the helpers the chat panel uses, and the chat calls in the public demo.
import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";
import { ApiError, askChat, getChat } from "../lib/api.ts";
import { cleanQuestion, momentLabel, showSuggestions, SUGGESTIONS } from "../lib/chat.ts";
import { type BundleManifest, setActiveBundle } from "../lib/replay.ts";

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
  frames: { total: 1, shown: 1, note: null, scale: 1 },
  frame_map: {},
  media: [],
  verdict: null,
} satisfies BundleManifest;

const realFetch = globalThis.fetch;

afterEach(() => {
  process.env.NEXT_PUBLIC_ARGUS_REPLAY = "";
  setActiveBundle(null);
  globalThis.fetch = realFetch;
});

test("an answer says which moment it is about", () => {
  assert.equal(momentLabel(252, 1250), "about 4:12");
  assert.equal(momentLabel(6600, 6600), "about 1:50");
});

test("a question is trimmed and kept to 500 characters", () => {
  assert.equal(cleanQuestion("  hi  "), "hi");
  assert.equal(cleanQuestion("   "), null);
  assert.equal(cleanQuestion("x".repeat(500))?.length, 500);
  assert.equal(cleanQuestion("x".repeat(501)), null);
});

test("suggestions show only while the conversation is empty", () => {
  assert.equal(showSuggestions([]), true);
  assert.equal(SUGGESTIONS.length, 3);
  const asked = { id: "chat_1", run_id: "run_1", t: 0, question: "Hi?", answer: "Hello.", body: {} };
  assert.equal(showSuggestions([{ ...asked, check_status: "passed", model_call_id: null }]), false);
});

test("in the demo, a bundle without a chat shows an empty conversation", async () => {
  process.env.NEXT_PUBLIC_ARGUS_REPLAY = "1";
  setActiveBundle(manifest);
  globalThis.fetch = (async () => new Response("missing", { status: 404 })) as typeof fetch;
  assert.deepEqual(await getChat("run_1"), []);
});

test("in the demo, asking is refused without a request", async () => {
  process.env.NEXT_PUBLIC_ARGUS_REPLAY = "1";
  setActiveBundle(manifest);
  globalThis.fetch = (() => {
    throw new Error("no request expected");
  }) as typeof fetch;
  await assert.rejects(askChat("run_1", 0, "Hi?"), (e: ApiError) => e.status === 405);
});

beforeEach(() => {
  process.env.NEXT_PUBLIC_ARGUS_REPLAY = "";
});
