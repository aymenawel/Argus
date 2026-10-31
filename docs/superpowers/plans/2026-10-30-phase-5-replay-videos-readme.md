# Phase 5: public replay, timelapse and reel, validation, README — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A logged-out Vercel link that replays finished runs read-only, a 1080p timelapse and a 30–60 s reel of any
finished run, a Videos card on Results, a validation table printed from the database, and the README.

**Architecture:** The worker exports a run bundle: its own GET responses recorded in-process, thinned frames and a
manifest. The same Next.js app built with `NEXT_PUBLIC_ARGUS_REPLAY=1` reads that bundle instead of the worker,
hides every write, and `proxy.ts` gates it to `/replay`. Videos are drawn from stored records with Pillow and encoded
by the ffmpeg CLI.

**Tech Stack:** Python 3.12 (uv, FastAPI TestClient, OpenCV, Pillow 13, ffmpeg/ffprobe CLI), Next.js 16.4.3 / React 19
/ TypeScript (node --test), Vercel CLI through `npx`.

**Spec:** `docs/superpowers/specs/2026-10-30-phase-5-replay-videos-readme-design.md` (decisions D-83 to D-86)

**Order and dates:** Tasks 1–3 by Oct 31 (the Genze replay public), 4–5 by Nov 1, 6–8 by Nov 2, 9 on Nov 2–3 after
the dye run. If time runs short, cut in the spec's order: Task 6's web card (the commands stay), reel ranking beyond
time order and the cap, validation rows beyond those already measured.

## Global Constraints

- Branch `phase-4`. Merging into `main` waits for Aymen's go-ahead (recommended by Nov 3).
- The LLM never computes numbers. The exporter, the media code and the validation command never call a model: they get
  no reasoner, and the exporter's segmenter raises if used.
- Repo is public. `web/public/bundles/`, `web/.vercel/` and `web/.next-replay/` are git-ignored; third-party frames
  never enter git. Before every commit run the key scan:
  `for name in MODEL_API_KEY BASETEN_API_KEY; do KEY=$(grep -E "^$name=" .env | cut -d= -f2-); if [ -n "$KEY" ] && git diff --cached | grep -qF "$KEY"; then echo "$name FOUND"; exit 1; fi; done`
- Only new dependency: Pillow (`pillow>=13.0.0`, worker). The Vercel CLI runs as `npx --yes vercel@<pinned>` and is not
  added to `package.json`. ffmpeg and ffprobe are called through `subprocess`.
- Never fake data. Every replay page says it is a replay; published data shows its credit and licence.
- Exact copy: "Replay · recorded <date> · nothing on this page is live"; "Published data: <credit> · <licence>";
  "Everything shown was built Oct 27 – Nov 4, 2026"; "This is a read-only replay" (the 405 detail).
- Bundle: frames 1280 px on the long side, JPEG quality 82; more than 400 frames are thinned; a bundle over 60 MB is
  refused. Source labels: `live recording`, `imported recording`, `published data`.
- Video: 1920 × 1080, H.264, yuv420p, 30 fps, `+faststart`. Timelapse default 20 s. Reel 30–60 s, 2 s before and 3 s
  after each moment.
- Vocabulary from `docs/knowledge-base/18-glossary.md` (readings, half-way time, vessel, run, plan locked, verdict).
- Style: ruff, line length 120; prettier, printWidth 120; runtime imports between `web/lib` files use the `.ts`
  extension (tsconfig allows it) so `node --test` can load them.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Worker checks: `cd worker && uv run pytest -q && uv run ruff check . && uv run ruff format --check .`.
  Web checks: `cd web && npm test && npm run typecheck && npm run lint && npm run format:check`.

## Review Focus

1. Exporting while another run is live: the app's lifespan marks running runs as stopped, so an exporter that ran it
   would stop a live run. Expected: the database is unchanged. Test: Task 1
   `test_exporting_leaves_a_running_run_running`.
2. The exporter and the web app naming the same request differently: it only shows as a missing file in the deployed
   replay. Expected: both read one shared table of names. Tests: Task 1 `test_bundle_file_names_match_the_shared_fixture`
   and Task 2 `bundle file names match the worker's fixture`.
3. Paths near the replay prefix (`/replayx`, `/bundles/...`, `/_next/...`, icons, `/`). Expected: nothing outside
   `/replay` leaks and no redirect loops. Test: Task 2 `only the replay, its bundles and assets pass the gate`.
4. A run with one frame, or with every frame at the same `t`. Expected: the timelapse is a still of the chosen length,
   not a crash. Test: Task 4 `test_a_single_frame_run_makes_a_still`.
5. A reel for a run with no moments, or with moments that fill less than 30 s. Expected: one chapter covering the whole
   run, or chapters slowed down to reach 30 s. Tests: Task 5 `test_a_run_without_moments_gets_one_chapter_of_the_whole_run`
   and `test_a_short_reel_slows_down_to_thirty_seconds`.

## Open items for Aymen (stops during execution)

- Task 3: run `npx --yes vercel@<pinned> login` once in his terminal, then OK the first production deploy.
- Task 4: OK the Inter download (filename, source and size are stated when asking).
- Task 8: which licence the README states for Argus's own code.
- Task 9: starts after his dye run; the merge into `main` needs his go-ahead.

---

### Task 1: Run bundle exporter (worker)

**Files:**
- Create: `worker/argus/export/__init__.py`, `worker/argus/export/paths.py`, `worker/argus/export/thinning.py`,
  `worker/argus/export/bundle.py`
- Create: `worker/tests/fixtures/bundle_paths.json`, `worker/tests/test_bundle.py`
- Modify: `worker/tests/records.py` (add `finished_run`), `worker/argus/storage/files.py` (add `media_path`),
  `worker/argus/cli.py` (add `export-bundle`), `.gitignore`

**Interfaces:**
- Produces:
  - `bundle_file(path: str, query: str = "") -> str` in `argus/export/paths.py`. `"/api/runs/r1/fits", "metric=delta_e"`
    → `"api/runs/r1/fits__metric=delta_e.json"`; no query → `"api/runs/r1/fits.json"`. Query pairs are sorted by key
    and joined by `&`. A key or value outside `^[A-Za-z0-9_.-]+$` raises `ValueError`.
  - `Thinning(kept: list[str], frame_map: dict[str, str])` (frozen dataclass) and
    `thin_frames(frames: Sequence[tuple[str, float]], cited_t: Sequence[float], limit: int = 400) -> Thinning`.
  - `BundleRefused(Exception)` with the reason as its message, and
    `export_bundle(db, settings, recipes, run_id, out_dir: Path, *, commit: str | None = None, max_frames: int = 400, max_bytes: int = 60_000_000) -> Path`
    (returns `out_dir / run_id`).
  - Bundle layout: `<run_id>/manifest.json`, `<run_id>/frames/<frame_id>.jpg`, `<run_id>/api/...json`, optional
    `<run_id>/timelapse.mp4` and `<run_id>/reel.mp4`; `out_dir/index.json` = `{"runs": [...]}`.
  - Manifest keys, exactly: `run_id, experiment_id, experiment_title, source_label, credit, licence, dataset_url,
    recorded, exported_at, commit, frames {total, shown, note}, frame_map, media, verdict`.
  - Index entry keys: `run_id, experiment_id, title, source_label, recorded, verdict`.
  - A recorded non-200 answer is saved as `{"argus_recorded_error": <status>, "detail": <detail>}`.
  - `RunFiles.media_path(kind: str) -> Path` = `<root>/media/<kind>.mp4`.
  - Test helper `finished_run(db, data_dir: Path, *, frames: int = 12, t_step: float = 600.0, provenance: Provenance | None = None, status: RunStatus = RunStatus.FINISHED) -> Run`
    in `tests/records.py`: experiment "Dye in warm and room water" on recipe `colour-reaction`; vessel A control, B
    treatment (condition `temperature`, 40, `°C`); `frames` grey 640 × 480 JPEGs written under `data_dir` at
    `t = i * t_step`; one `delta_e` reading per vessel per frame (B logistic from 0 to 30, A flat at 1 with ±0.2
    wobble); an intervention event with `{"message": "Dye added"}` at frame 2's `t`, a change event on B after it; a
    researcher note; the given status.

- [ ] **Step 1: Write the shared name table** `worker/tests/fixtures/bundle_paths.json`

```json
[
  { "path": "/api/runs/run_1", "query": "", "file": "api/runs/run_1.json" },
  { "path": "/api/runs/run_1/fits", "query": "metric=delta_e", "file": "api/runs/run_1/fits__metric=delta_e.json" },
  { "path": "/api/experiments/exp_1/recipe/detail", "query": "", "file": "api/experiments/exp_1/recipe/detail.json" },
  { "path": "/api/runs/run_1/frames/frm_9/detections", "query": "", "file": "api/runs/run_1/frames/frm_9/detections.json" },
  { "path": "/api/runs/run_1/agreement", "query": "metric=sprouted", "file": "api/runs/run_1/agreement__metric=sprouted.json" },
  { "path": "/api/runs/run_1/x", "query": "b=2&a=1", "file": "api/runs/run_1/x__a=1&b=2.json" }
]
```

- [ ] **Step 2: Write the failing tests** in `worker/tests/test_bundle.py`

```python
def test_bundle_file_names_match_the_shared_fixture():
    for case in json.loads((FIXTURES / "bundle_paths.json").read_text(encoding="utf-8")):
        assert bundle_file(case["path"], case["query"]) == case["file"]

def test_a_query_value_outside_the_safe_set_is_refused():
    with pytest.raises(ValueError):
        bundle_file("/api/runs/r/fits", "metric=a/b")

def test_thinning_keeps_every_frame_under_the_limit():
    frames = [(f"f{i}", i * 10.0) for i in range(400)]
    thinning = thin_frames(frames, [], limit=400)
    assert thinning.kept == [f for f, _ in frames] and thinning.frame_map["f7"] == "f7"

def test_thinning_keeps_even_steps_and_cited_frames():
    frames = [(f"f{i}", i * 10.0) for i in range(1000)]
    thinning = thin_frames(frames, cited_t=[5551.0], limit=400)
    assert 400 <= len(thinning.kept) <= 401 and "f555" in thinning.kept
    assert set(thinning.frame_map) == {f for f, _ in frames} and set(thinning.frame_map.values()) <= set(thinning.kept)

def test_irregular_t_maps_to_the_nearest_kept_frame():
    frames = [("a", 0.0), ("b", 1.0), ("c", 2.0), ("d", 50.0), ("e", 51.0)]
    thinning = thin_frames(frames, [], limit=2)  # keeps a and e
    assert thinning.frame_map == {"a": "a", "b": "a", "c": "a", "d": "e", "e": "e"}

def test_each_recorded_response_equals_the_live_response(db, tmp_path):
    # finished_run, export, then GET every recorded path from api_client and compare JSON bodies;
    # the runs list is compared after filtering the live list to this run.

def test_frames_are_shrunk_never_enlarged(db, tmp_path):
    # the fixture's 640 px frames stay 640 px wide; a frame rewritten at 1600 × 1200 comes out 1280 × 960

def test_a_running_run_is_refused(db, tmp_path):
    with pytest.raises(BundleRefused, match="still running"): ...

def test_an_oversize_bundle_is_refused_and_leaves_nothing(db, tmp_path):
    # max_bytes=1000: refused with the size in MB; out_dir has no run folder, no temp folder, no index entry

def test_exporting_leaves_a_running_run_running(db, tmp_path):
    # a second run with status running exists; after exporting the finished one its status is still running

def test_reexport_replaces_the_folder_and_its_index_entry(db, tmp_path):
    # export, drop a stale file in the folder, export again: stale file gone, index has one entry for the run

def test_no_model_is_called(db, tmp_path):
    assert logged_functions(db) == []  # after export

def test_manifest_labels_published_data_with_its_credit(db, tmp_path):
    # provenance given: source_label "published data", credit/licence/dataset_url from it, frames.note None
    # (12 frames, nothing thinned); without provenance and mode imported: "imported recording", credit None

def test_a_thinned_manifest_says_so(db, tmp_path):
    # 1000 frames, max_frames=200: frames == {"total": 1000, "shown": K, "note": f"1 frame in {round(1000/K)} shown; measurements use all 1,000 frames"}
```

- [ ] **Step 3: Run them to verify they fail**

Run: `cd worker && uv run pytest tests/test_bundle.py -q`
Expected: FAIL at import (`argus.export` does not exist).

- [ ] **Step 4: Implement `bundle_file` and `thin_frames`**

`thin_frames`: with more frames than `limit`, take `limit` target times evenly spaced from the first `t` to the last
(inclusive), keep the frame nearest each target and nearest each cited `t`, then map every frame to its nearest kept
frame (a tie goes to the earlier frame). `kept` is in `t` order.

- [ ] **Step 5: Implement `export_bundle` in `argus/export/bundle.py`**

- Refusals (`BundleRefused`): run not found; `run_id` outside `^[A-Za-z0-9_-]+$`; status `running`
  ("the run is still running"); a size over `max_bytes` (`f"the bundle is {mb:.1f} MB, over the {limit_mb} MB limit"`).
- The app: `create_app(settings, db, EventBroker(), recipes, jobs=RunJobs(..., segmenter=NoModels(), reasoner=None), hub=CameraHub())`
  wrapped in `TestClient(app)` **without** `with`, so the lifespan never runs. `NoModels` raises on every method.
- Recorded GETs: experiment; `recipe/detail`; the experiment's runs (filtered to this run); `plan`; run; timeline;
  notes; verdict; reviews; fits with no metric and with `?metric=` for each metric in the recipe detail; agreement
  `?metric=` for each of those metrics; next-run; detections for each kept frame. Each is saved at `bundle_file(...)`.
- Cited times for thinning: every note's `t`, every event's `t_start` except `tick` and `checkin`, and the verdict's `t`.
- Frames: read with OpenCV from `settings.data_dir / frame.path`, shrunk with `INTER_AREA` so the long side is at most
  1280 px, written with `IMWRITE_JPEG_QUALITY` 82.
- Source label: provenance → `published data`, mode `live` → `live recording`, else `imported recording`.
- Media: copy `RunFiles(...).media_path("timelapse")` and `media_path("reel")` when they exist; list their file names
  in `media`.
- Writing: build everything in `out_dir/.<run_id>.tmp`, check its size, remove any old `out_dir/<run_id>`, rename the
  temp folder, then rewrite `index.json` with this run's entry replaced, newest `recorded` first. Never write outside
  `out_dir`.

- [ ] **Step 6: Add the CLI command** in `argus/cli.py`

`export-bundle RUN_ID [--out PATH] [--max-frames N]`; `--out` defaults to `REPO_ROOT / "web" / "public" / "bundles"`,
`--max-frames` to 400 (the remedy when a bundle is refused for size). The commit comes from
`git rev-parse --short HEAD` (None if git fails). Prints the folder, its size in MB and the thinning note. A refusal
prints the reason to stderr and returns 1.

- [ ] **Step 7: Ignore the bundles** — append to `.gitignore`: `web/public/bundles/`, `web/.vercel/`,
  `web/.next-replay/`.

- [ ] **Step 8: Run the tests and the worker checks**

Run: `cd worker && uv run pytest tests/test_bundle.py -q`, then the worker checks.
Expected: all pass.

- [ ] **Step 9: Commit** (key scan first)

```bash
git add .gitignore worker/argus/export worker/argus/storage/files.py worker/argus/cli.py worker/tests/test_bundle.py worker/tests/records.py worker/tests/fixtures/bundle_paths.json
git commit -m "feat(export): run bundle of recorded responses, thinned frames and a manifest (D-83)"
```

---

### Task 2: Replay mode (web)

**Files:**
- Create: `web/lib/replay.ts`, `web/lib/links.ts`, `web/proxy.ts`, `web/scripts/replay.mjs`,
  `web/components/replay/ReplayBanner.tsx` (+ `.module.css`), `web/app/replay/page.tsx`,
  `web/app/replay/ReplayIndex.tsx`, `web/app/replay/page.module.css`, `web/app/replay/[runId]/page.tsx`,
  `web/app/replay/[runId]/ReplayRun.tsx`, `web/app/replay/[runId]/results/page.tsx`, `web/tests/replay.test.ts`
- Modify: `web/lib/api.ts`, `web/lib/events.ts`, `web/components/shell/Rail.tsx`,
  `web/app/experiments/[id]/run/RunScreen.tsx`, `web/app/experiments/[id]/results/ResultsScreen.tsx`,
  `web/components/feed/Feed.tsx`, `web/components/verdict/VerdictPanel.tsx`, `web/components/results/NextRunCard.tsx`,
  `web/components/run/RunFrame.tsx`, `web/next.config.ts`, `web/package.json` (script only), `.claude/launch.json`

**Interfaces:**
- Consumes: Task 1's bundle layout, manifest and index keys, the recorded-error shape, `bundle_paths.json`.
- Produces (`lib/replay.ts`):
  - `isReplay(): boolean` — `process.env.NEXT_PUBLIC_ARGUS_REPLAY === "1"`, read at call time.
  - `bundleFile(path: string, query: string): string` — same rule as `bundle_file`; throws `Error` on an unsafe pair.
  - `isReplayPath(pathname: string): boolean`.
  - Types `BundleManifest`, `BundleIndex` (the Task 1 keys).
  - `openBundle(runId: string): Promise<BundleManifest>` (fetches `/bundles/<runId>/manifest.json` and makes it the
    active bundle), `setActiveBundle(manifest: BundleManifest | null): void`, `activeBundle(): BundleManifest | null`,
    `getReplayIndex(): Promise<BundleIndex>`.
  - `replayFrameUrl(manifest: BundleManifest, frameId: string): string` → `/bundles/<run>/frames/<mapped>.jpg`.
  - `mapFramePath(path: string, manifest: BundleManifest): string` — rewrites the frame id in
    `/api/runs/<run>/frames/<id>/detections` through the frame map; other paths unchanged.
  - `useReadOnly(): boolean` — `isReplay()`.
- Produces (`lib/links.ts`): `runHref(experimentId: string, runId: string): string` and
  `resultsHref(experimentId: string, runId: string): string` (`/replay/<runId>[/results]` in replay mode, else
  `/experiments/<id>/run|results`); `homeLink(): { href: string; label: string }` (`/replay` "Replays" or `/`
  "Experiments").
- Produces (`lib/api.ts`): `errorText(error: ApiError): string` — the two existing worker messages live; in replay
  mode `The replay couldn't load ${error.detail}.` Screens use it in their error states.
- `RunScreen` and `ResultsScreen` take an optional `experimentId?: string` prop, used instead of the URL's `id`.

- [ ] **Step 1: Write the failing tests** in `web/tests/replay.test.ts`

```ts
const manifest = { run_id: "run_1", frame_map: { frm_a: "frm_a", frm_b: "frm_a" } /* other keys filled */ } as BundleManifest;

test("bundle file names match the worker's fixture", () => {
  const cases = JSON.parse(readFileSync(new URL("../../worker/tests/fixtures/bundle_paths.json", import.meta.url), "utf8"));
  for (const c of cases) assert.equal(bundleFile(c.path, c.query), c.file);
});
test("an unsafe query value is refused", () => assert.throws(() => bundleFile("/api/runs/r/fits", "metric=a%2Fb")));
test("only the replay, its bundles and assets pass the gate", () => {
  for (const p of ["/replay", "/replay/run_1", "/replay/run_1/results", "/bundles/index.json", "/_next/static/x.js", "/icon.svg", "/apple-icon.png", "/favicon.ico", "/__nextjs_font/x"])
    assert.equal(isReplayPath(p), true, p);
  for (const p of ["/", "/replayx", "/experiments/e/run", "/settings", "/kit", "/bundlesx"]) assert.equal(isReplayPath(p), false, p);
});
test("writes are refused in replay mode without a request", async () => {
  process.env.NEXT_PUBLIC_ARGUS_REPLAY = "1";
  globalThis.fetch = (() => { throw new Error("no request expected"); }) as typeof fetch;
  await assert.rejects(postNote("run_1", { t: 0, tag: "observation", text: "x" }), (e: ApiError) => e.status === 405 && e.detail === "This is a read-only replay");
});
test("reads come from the active bundle", async () => {
  setActiveBundle(manifest);
  let asked = "";
  globalThis.fetch = (async (url: string) => { asked = url; return Response.json({ ok: 1 }); }) as typeof fetch;
  await getFits("run_1", "delta_e");
  assert.equal(asked, "/bundles/run_1/api/runs/run_1/fits__metric=delta_e.json");
});
test("a recorded 404 raises the same ApiError", async () => {
  globalThis.fetch = (async () => Response.json({ argus_recorded_error: 404, detail: "run not found" })) as typeof fetch;
  await assert.rejects(getRun("run_1"), (e: ApiError) => e.status === 404 && e.detail === "run not found");
});
test("a missing bundle file says which", async () => {
  globalThis.fetch = (async () => new Response("", { status: 404 })) as typeof fetch;
  await assert.rejects(getRun("run_1"), (e: ApiError) => e.status === 404 && e.detail.includes("/bundles/run_1/api/runs/run_1.json"));
});
test("frames and their outlines map through the manifest", () => {
  assert.equal(frameUrl("run_1", "frm_b", 160), "/bundles/run_1/frames/frm_a.jpg");
  assert.equal(mapFramePath("/api/runs/run_1/frames/frm_b/detections", manifest), "/api/runs/run_1/frames/frm_a/detections");
});
test("links point at the replay routes in replay mode", () => {
  assert.equal(resultsHref("exp_1", "run_1"), "/replay/run_1/results");
  process.env.NEXT_PUBLIC_ARGUS_REPLAY = "";
  assert.equal(resultsHref("exp_1", "run_1"), "/experiments/exp_1/results");
});
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd web && npm test`
Expected: FAIL (cannot find `../lib/replay.ts`).

- [ ] **Step 3: Implement `lib/replay.ts` and `lib/links.ts`** (no imports from `api.ts`, so there is no cycle).

- [ ] **Step 4: Route `lib/api.ts` through the bundle in replay mode**

`request()`: in replay mode a method other than GET throws `ApiError(405, "This is a read-only replay")`; a GET
splits path and query, applies `mapFramePath`, fetches `/bundles/<active run>/<bundleFile(...)>`, throws
`ApiError(404, "<that url> is missing from the replay")` on a non-OK answer, and turns an `argus_recorded_error` body
into `ApiError(status, detail)`. With no active bundle: `ApiError(404, "no replayed run is open")`. `frameUrl` returns
`replayFrameUrl` (the width is ignored). `lib/events.ts` `subscribe` returns a no-op stop in replay mode.

- [ ] **Step 5: Run the tests**

Run: `cd web && npm test`
Expected: PASS.

- [ ] **Step 6: Hide the writes and route the links**

- `useReadOnly()` hides: Stop run (`RunScreen`), `NoteComposer` (`Feed`), Get a verdict and the Confirm / Dismiss /
  Mark resolved buttons (`VerdictPanel`), Suggest the next run (`NextRunCard`). With nothing to show instead:
  "No verdict was asked for this run." and "No next run was suggested for this run."
- `RunScreen` / `ResultsScreen`: `const id = experimentId ?? params.id`; the crumb's first link is `homeLink()`; the
  Results and Run links use `resultsHref` / `runHref` with the shown run's id; the error states use `errorText`.
- `RunFrame`: when `activeBundle()?.frames.note` is set, show it under the frame in the muted caption style.
- `Rail`: in replay mode, `MAIN` is one item (href `/replay`, label "Replays", the Experiments icon) and the bottom
  item is an external link to `https://github.com/aymenawel/Argus` (label "Source on GitHub", `target="_blank"`,
  `rel="noreferrer"`) instead of Settings.

- [ ] **Step 7: Add the routes and the banner**

- `ReplayBanner({ manifest }: { manifest: BundleManifest | null })`: line 1 "Replay · recorded <date> · nothing on
  this page is live" (date: `toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })`;
  without a manifest, "Replay · nothing on this page is live"); line 2 for published data "Published data: <credit> ·
  <licence>" with the credit linked to `dataset_url`; line 3 "Everything shown was built Oct 27 – Nov 4, 2026". It
  is a `role="note"` strip above the page header using the existing tokens (no new colours).
- `/replay` (`ReplayIndex`): banner, `PageHeader` title "Replays", one card per index entry (title, source label,
  recorded date, `VerdictChip`, links "Run view" and "Results"); no entries: "No runs are bundled yet."
- `/replay/[runId]` and `/replay/[runId]/results` (`ReplayRun` with a `view: "run" | "results"` prop): `openBundle`
  then the banner and `<RunScreen experimentId={manifest.experiment_id} />` or `<ResultsScreen ... />`; a failed
  `openBundle` shows the error panel with `errorText`. Pages follow the existing pattern (client screen inside
  `Suspense`, `metadata` title "Replay · Argus").

- [ ] **Step 8: Add the gate and the local replay server**

- `web/proxy.ts`: `export function proxy(request: NextRequest)` returns `NextResponse.next()` outside replay mode or
  when `isReplayPath(pathname)`, else redirects to `/replay`.
- `next.config.ts`: `distDir: process.env.ARGUS_DIST_DIR || ".next"`.
- `web/scripts/replay.mjs`: sets `NEXT_PUBLIC_ARGUS_REPLAY=1` and `ARGUS_DIST_DIR=.next-replay`, runs `next dev -p 3001`
  (so it runs beside the normal dev server). `package.json` script `"replay": "node scripts/replay.mjs"`.
  `.claude/launch.json` gets a `replay` configuration (`npm run replay`, port 3001).

- [ ] **Step 9: Check in the browser** with a test bundle

Export the Genze run from `data/argus.sqlite` with `uv run python -m argus export-bundle <id>` (Task 3 Step 3 shows
how to find its id), start the `replay` preview, then check `/replay`, the Run view and Results at 1440 px and 390 px in light and dark: banner present, no
write buttons, frames and outlines draw, scrubbing works, `/` and `/settings` land on `/replay`. Also confirm the normal
dev server on 3000 is unchanged.

- [ ] **Step 10: Run the web checks and commit** (key scan first)

```bash
git add web .claude/launch.json
git commit -m "feat(replay): the app in replay mode reads a run bundle, read-only, gated to /replay (D-83)"
```

---

### Task 3: Deploy the replay with the Genze plate

**Files:**
- Create: `web/scripts/deploy-replay.sh`
- Modify: `docs/knowledge-base/11-tech-stack-and-libraries.md` (Vercel CLI row: pinned version, run through npx)

- [ ] **Step 1: Pin the CLI**

Run: `npm view vercel time --json` and take the newest version published on or before 2026-10-16.
Look up Vercel's current upload limit for a CLI deploy on Hobby (WebSearch, standard) and note both in the script.

- [ ] **Step 2: Write `web/scripts/deploy-replay.sh`**

From `web/`: refuse when `public/bundles` is over the Hobby limit found in Step 1 (prints the size), then
`npx --yes vercel@<pinned> pull --yes --environment=production`,
`NEXT_PUBLIC_ARGUS_REPLAY=1 npx --yes vercel@<pinned> build --prod`,
`npx --yes vercel@<pinned> deploy --prebuilt --prod`; prints the production URL. `set -euo pipefail`.

- [ ] **Step 3: Export the Genze bundle**

Find the run: `cd worker && uv run python -c "import sqlite3; c = sqlite3.connect('../data/argus.sqlite'); print(c.execute('select r.id, e.title, r.status from runs r join experiments e on e.id = r.experiment_id').fetchall())"`.
Run: `uv run python -m argus export-bundle <genze run id>`
Expected: the folder, a size well under 60 MB, `published data` in its manifest.

- [ ] **Step 4: STOP — ask Aymen** to run `npx --yes vercel@<pinned> login` in his terminal, and for his OK to create
  the Vercel project `argus-replay` and deploy it to production (public).

- [ ] **Step 5: Link and deploy**

Run (from `web/`): `npx --yes vercel@<pinned> link --yes --project argus-replay`, then `bash scripts/deploy-replay.sh`.
Expected: a production URL.

- [ ] **Step 6: Check it logged out**

Open the URL in the built-in browser (no Vercel session): `/replay` lists the Genze run with "published data" and its
credit; Run view and Results load; `/` and `/experiments/x/run` land on `/replay`; no request goes to
`localhost:8000` (read the network requests). If Vercel asks for a login, tell Aymen: that is his project's deployment
protection setting, not something to change from here.

- [ ] **Step 7: Commit** (key scan first; confirm `git status` shows no bundle and no `.vercel/`)

```bash
git add web/scripts/deploy-replay.sh docs/knowledge-base/11-tech-stack-and-libraries.md
git commit -m "chore(replay): deploy script with a pinned Vercel CLI; the Genze replay is public"
```

---

### Task 4: Timelapse with overlay (worker)

**Files:**
- Create: `worker/argus/media/__init__.py`, `layout.py`, `records.py`, `draw.py`, `encode.py`, `make.py`,
  `worker/argus/media/fonts/Inter[opsz,wght].ttf`, `worker/argus/media/fonts/OFL.txt`
- Create: `worker/tests/test_media_layout.py`, `worker/tests/test_media_encode.py`, `worker/tests/test_timelapse.py`
- Modify: `worker/pyproject.toml` (Pillow), `worker/argus/analyze/fits.py` (add `fits_view`),
  `worker/argus/api/results.py` (route calls `fits_view`), `worker/argus/cli.py` (`media timelapse`)

**Interfaces:**
- Consumes: `RunFiles.media_path` (Task 1), `finished_run` (Task 1).
- Produces:
  - `MediaError(Exception)` (encode or draw failed; message is the reason) and `MediaRefused(Exception)` in
    `argus/media/__init__.py`.
  - `fits_view(db, recipes, run_id: str, metric: str | None = None) -> dict` in `argus/analyze/fits.py`: the body the
    fits route returns today; raises `LookupError("run not found")` and `ValueError(<the route's 422 detail>)`.
  - `Slot(t: float, a: int, b: int | None, w: float)` and
    `schedule(ts: Sequence[float], seconds: float, *, fps: int = 30, t_from: float | None = None, t_to: float | None = None) -> list[Slot]`
    in `layout.py` (`a`, `b` index into `ts`; `w` is the weight of `b`).
  - `segments(points: Sequence[tuple[float, float]], gap_factor: float = 3.0) -> list[list[tuple[float, float]]]`,
    `clock_text(t: float, start_time: datetime | None) -> str`, `caption_at(notes: Sequence[Note], t: float) -> str | None`,
    `source_line(run: Run) -> str`, `PALETTE: dict[str, str]` in `layout.py`.
  - `RunRecords` (frozen dataclass: `run, experiment, plan, vessels, frames` (sorted by `t`), `fits` (the `fits_view`
    of the plan's metric), `notes, events, verdict, next_run, files: RunFiles`), and
    `load_records(db, settings, recipes, run_id) -> RunRecords` and `refusal(db, run_id) -> str | None`
    ("the run is still running", "the run has no frames") in `records.py`.
  - `Drawer(records: RunRecords, settings: Settings)` with `run_frame(slot: Slot, caption_kind: str | None = None, caption: str | None = None) -> Image.Image`
    and `card(lines: Sequence[str]) -> Image.Image` in `draw.py` (1920 × 1080 RGB).
  - `encode(frames: Iterable[Image.Image], out: Path, *, fps: int = 30, size: tuple[int, int] = (1920, 1080)) -> Path`
    in `encode.py`.
  - `make_timelapse(db, settings, recipes, run_id: str, *, seconds: float = 20.0, progress: Callable[[float], None] | None = None) -> Path`
    in `make.py`.

- [ ] **Step 1: STOP — ask Aymen for the font download.** Before asking, read the sizes with
  `curl -sIL https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz,wght%5D.ttf | grep -i content-length`
  (and the same for `ofl/inter/OFL.txt`); state filename, source and size. On OK, download each into its own new empty
  folder in the scratchpad, check the TTF starts with bytes `00 01 00 00`, and copy both into `argus/media/fonts/`.
  If he declines: use `ImageFont.load_default(size)` and leave Inter out of the notices.

- [ ] **Step 2: Add Pillow** — `cd worker && uv add "pillow>=13.0.0"`

- [ ] **Step 3: Write the failing tests**

`tests/test_media_layout.py`:

```python
def test_schedule_covers_the_run_in_the_chosen_length():
    ts = [i * 1800.0 for i in range(95)]  # 47 h
    slots = schedule(ts, 20.0)
    assert len(slots) == 600 and slots[0].t == 0.0 and slots[-1].t == ts[-1]

def test_each_slot_shows_the_frame_at_or_before_its_t():
    ts = [0.0, 10.0, 100.0, 1000.0]
    slots = schedule(ts, 1.0, fps=10)
    assert all(ts[s.a] <= s.t for s in slots) and slots[-1].a == 3

def test_cross_fade_holds_then_dissolves():
    slots = schedule([0.0, 100.0], 10 / 30, fps=30)  # 10 slots across one gap
    weights = [round(s.w, 2) for s in slots[:-1]]
    assert weights[:5] == [0.0] * 5 and weights[-1] > 0.75 and weights == sorted(weights)

def test_dense_frames_never_cross_fade():
    assert all(s.w == 0.0 for s in schedule([i * 1.0 for i in range(3000)], 2.0))

def test_a_single_frame_run_makes_a_still():
    slots = schedule([5.0], 2.0)
    assert len(slots) == 60 and all(s.a == 0 and s.b is None and s.t == 5.0 for s in slots)
    assert len(schedule([5.0, 5.0, 5.0], 2.0)) == 60

def test_gaps_in_readings_stay_gaps():
    points = [(0, 1), (60, 2), (120, 3), (3600, 4), (3660, 5)]
    assert [len(s) for s in segments(points)] == [3, 2]

@pytest.mark.parametrize("t, start, text", [
    (84600.0, None, "t 23.5 h"),
    (1500.0, None, "t 25 min"),
    (1500.0, datetime(2026, 11, 2, 14, 0, tzinfo=UTC), "t 25 min · 14:25"),
])
def test_clock_text(t, start, text):
    assert clock_text(t, start) == text

def test_the_caption_is_the_stored_note_in_effect():
    # notes at t=10 (AI, body observation "Glass B darkened.") and t=50 (researcher, body text "Dye added")
    assert caption_at(notes, 5) is None and caption_at(notes, 20) == "Glass B darkened." and caption_at(notes, 60) == "Dye added"

def test_the_palette_matches_the_web_tokens():
    # parse the :root[data-theme="dark"] block of web/styles/tokens.css
    assert {k: tokens[f"--{k}"] for k in ("ground", "text", "muted", "accent")} == PALETTE
```

`tests/test_media_encode.py`:

```python
def test_encode_makes_an_mp4_of_the_expected_duration(tmp_path):
    out = encode((Image.new("RGB", (320, 180), c) for c in ("red", "green", "blue")), tmp_path / "x.mp4", fps=1, size=(320, 180))
    probe = ffprobe(out)  # width, height, codec, pix_fmt, duration
    assert (probe.width, probe.height, probe.codec, probe.pix_fmt) == (320, 180, "h264", "yuv420p")
    assert abs(probe.duration - 3.0) < 0.1

def test_a_failed_encode_leaves_no_file(tmp_path):
    def frames():
        yield Image.new("RGB", (320, 180))
        raise RuntimeError("drawing failed")
    with pytest.raises(MediaError):
        encode(frames(), tmp_path / "x.mp4", size=(320, 180))
    assert list(tmp_path.iterdir()) == []

def test_a_missing_ffmpeg_is_a_media_error(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(MediaError, match="ffmpeg is not on PATH"):
        encode(iter([]), tmp_path / "x.mp4")
```

`tests/test_timelapse.py`:

```python
def test_fits_view_matches_the_route(db, tmp_path): ...  # same dict as GET /api/runs/{id}/fits

def test_a_timelapse_of_a_finished_run(db, tmp_path):
    out = make_timelapse(db, settings, recipes, run.id, seconds=1.0)
    assert out == RunFiles(...).media_path("timelapse")
    probe = ffprobe(out); assert (probe.width, probe.height) == (1920, 1080) and abs(probe.duration - 1.0) < 0.1

def test_a_running_run_is_refused(db, tmp_path):
    with pytest.raises(MediaRefused, match="still running"): ...

def test_a_run_without_readings_has_no_curve_panel(db, tmp_path):
    # readings deleted from the fixture: Drawer(...).run_frame(...) succeeds and records.fits has no readings;
    # the panel text is f"No readings of {metric} to draw"

def test_no_model_is_called(db, tmp_path):
    assert logged_functions(db) == []  # after make_timelapse
```

- [ ] **Step 4: Run them to verify they fail**

Run: `cd worker && uv run pytest tests/test_media_layout.py tests/test_media_encode.py tests/test_timelapse.py -q`
Expected: FAIL at import (`argus.media` does not exist).

- [ ] **Step 5: Implement `layout.py`**

- `schedule`: `n = max(1, round(seconds * fps))` slots; slot `k` at `t_from + (t_to - t_from) * k / (n - 1)` (all at
  `t_from` when the range is zero or `n == 1`). `a` is the last frame with `ts[a] <= t`, else frame 0; `b = a + 1`
  when it exists. Cross-fade only when the gap `ts[b] - ts[a]` is longer than one slot step: `frac` is the position in
  the gap and `w = clamp((frac - 0.5) / 0.5, 0, 1)` (hold for the first half, dissolve in the second); otherwise
  `w = 0`.
- `segments`: break where the step between readings exceeds `gap_factor` × the median step.
- `clock_text`: at or over 3600 s `f"t {t / 3600:.1f} h"`, else `f"t {t / 60:.0f} min"`; with a start time, append
  `" · "` and `start_time + t` as `%H:%M` in the start time's own offset.
- `caption_at`: the latest note with `note.t <= t`; text is `body["observation"]` for AI notes and `body["text"]`
  for researcher notes.
- `source_line`: provenance → `f"Published data: {credit} · {licence}"`; live → "Live recording"; else "Imported recording".
- `PALETTE`: `{"ground": "#0d0e10", "text": "#f5f7fa", "muted": "#aab0b9", "accent": "#2dd4bf"}` (videos use the
  dark theme).

- [ ] **Step 6: Implement `fits_view`, `records.py` and the route change**

The fits route becomes a wrapper turning `LookupError` into 404 and `ValueError` into 422; `test_api_results.py` stays
green unchanged.

- [ ] **Step 7: Implement `draw.py`**

Layout at 1× (draw the overlay at 2× on a transparent layer, downscale with LANCZOS, composite on the 1× photo):

| Element | Place | Content |
|---|---|---|
| Frame | fitted into x 40, y 40, 1240 × 1000, centred | frame `a`, blended with `b` by `w`; each vessel's outline from frame `a`'s detections, 3 px, `muted` for controls and `accent` for treatments |
| Clock | x 1320, y 48 | `clock_text`, Inter 600 at 56 px; the second part (`· 14:25`) in `muted` |
| Metric | x 1320, y 150 | as Results words it: `delta e in dE00`, or the metric's words alone when the unit is `count` |
| Chart | x 1320–1880, y 190–690 | readings per vessel up to `t` (lines broken by `segments`, dots), fitted samples up to `t`, a vertical cursor at `t`; x is the run's `t` range, y the readings' and samples' range with 5 % padding; dashes `None`, `(7, 4)`, `(2, 4)` and dot shapes circle, square, diamond per treatment condition as `conditionGroups` in `web/lib/chart.ts`; controls grey, solid, round |
| Legend | x 1320, y 705 | one entry per condition: "Control" or `f"Treatment: {value}"` |
| Caption | x 1320–1880, y 760–1000 | optional kind line in `accent` (reel), then the caption, Inter 400 at 26 px, wrapped, at most 5 lines with an ellipsis |
| Source | x 1320, y 1020 | `source_line`, `muted`, 20 px |

With no readings, the chart area shows `f"No readings of {metric} to draw"` in `muted`. `card(lines)`: the lines
centred on the ground, the first in Inter 600 at 56 px, the rest Inter 400 at 32 px, wrapped at 1400 px. Inter's
`opsz` axis is set to the pixel size clamped to the font's range, `wght` to 400 or 600.

- [ ] **Step 8: Implement `encode.py` and `make_timelapse`**

`encode`: `shutil.which("ffmpeg")` or `MediaError("ffmpeg is not on PATH")`; run
`ffmpeg -y -f rawvideo -pix_fmt rgb24 -s WxH -r FPS -i - -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart <out>.part.mp4`
with stderr to a temporary file; write each frame's RGB bytes to stdin; on any failure kill ffmpeg, delete the part
file and raise `MediaError` with ffmpeg's last stderr line (or the exception's message); on success rename to `out`.
`make_timelapse`: `refusal` → `MediaRefused`; `schedule` over all frames; `progress(k / n)` every 30 slots.

- [ ] **Step 9: Add the CLI** — `media timelapse RUN_ID [--seconds 20]` prints the file and its size; a refusal or
  `MediaError` prints the reason and returns 1.

- [ ] **Step 10: Run the tests and the worker checks**, then make the Genze timelapse
  (`uv run python -m argus media timelapse <genze run id>`) and look at three frames of it (`ffmpeg -ss <t> -frames:v 1`
  into the scratchpad, then read the images): curves, outlines, clock, credit line.

- [ ] **Step 11: Commit** (key scan first)

```bash
git add worker/pyproject.toml worker/uv.lock worker/argus/media worker/argus/analyze/fits.py worker/argus/api/results.py worker/argus/cli.py worker/tests/test_media_*.py worker/tests/test_timelapse.py
git commit -m "feat(media): timelapse with the curves drawn over the run, from stored records (D-84, D-85)"
```

---

### Task 5: Highlights reel (worker)

**Files:**
- Create: `worker/argus/media/moments.py`, `worker/tests/test_moments.py`
- Modify: `worker/argus/media/make.py` (`make_reel`), `worker/argus/cli.py` (`media reel`), `worker/tests/test_timelapse.py`

**Interfaces:**
- Consumes: `RunRecords`, `schedule`, `Drawer.run_frame` / `Drawer.card`, `encode` (Task 4).
- Produces:
  - `Moment(t: float, kind: Literal["intervention", "quality", "half_way", "checkpoint", "change"], caption: str)`
    and `collect_moments(records: RunRecords) -> list[Moment]`.
  - `Chapter(t_from: float, t_to: float, seconds: float, moments: list[Moment])`,
    `reel_pace(ts: Sequence[float]) -> float` (run seconds per reel second: `max(1.0, 2 × the median step between
    frames)`, so a chapter shows about two source frames per second; 1.0 for a single frame) and
    `plan_chapters(moments: Sequence[Moment], t0: float, t1: float, pace: float) -> list[Chapter]`.
  - `title_lines(records) -> list[str]`, `end_lines(records) -> list[str]`.
  - `make_reel(db, settings, recipes, run_id: str, *, progress=None) -> Path` (writes `media_path("reel")`).
  - Constants: `TITLE_S = 3.0`, `END_S = 4.0`, `PRE_S = 2.0`, `POST_S = 3.0`, `MIN_S = 30.0`, `MAX_S = 60.0`,
    `RANK = {"intervention": 0, "quality": 0, "half_way": 1, "checkpoint": 2, "change": 3}`.

- [ ] **Step 1: Write the failing tests** in `tests/test_moments.py`

```python
def test_moments_come_only_from_stored_records(db, tmp_path):
    moments = collect_moments(load_records(...))  # finished_run
    assert ("intervention", "Dye added") in [(m.kind, m.caption) for m in moments]
    # every caption is a stored event message, a stored note text, a check's text, or a half-way line built from the fit

def test_half_way_moments_name_the_median_vessel_of_each_condition(): ...
    # caption f"Half-way: {label} ({group label}) · {format_measurement(h, u, 'h')}", t = half_time_h * 3600

def test_no_half_way_moments_without_readings(): ...

def test_the_pace_shows_about_two_frames_per_second():
    assert reel_pace([0, 600, 1200, 1800]) == 1200.0 and reel_pace([5.0]) == 1.0 and reel_pace([0, 0.2, 0.4]) == 1.0

def test_close_moments_merge_into_one_chapter():
    chapters = plan_chapters([m("change", 1000), m("change", 1010)], 0, 72000, pace=600)
    assert len(chapters) == 1 and len(chapters[0].moments) == 2

def test_the_budget_drops_the_lowest_ranked_moments_first():
    moments = [m("intervention", 500)] + [m("change", 4000 * i) for i in range(1, 17)]  # 17 separate chapters
    chapters = plan_chapters(moments, 0, 72000, pace=600)
    total = TITLE_S + END_S + sum(c.seconds for c in chapters)
    kept = [x for c in chapters for x in c.moments]
    assert 30 <= total <= 60 and moments[0] in kept
    assert [x.t for x in kept if x.kind == "change"] == [4000 * i for i in range(1, 10)]  # the latest went first

def test_a_short_reel_slows_down_to_thirty_seconds():
    chapters = plan_chapters([m("intervention", 36000)], 0, 72000, pace=600)
    assert TITLE_S + END_S + sum(c.seconds for c in chapters) == pytest.approx(MIN_S)

def test_a_run_without_moments_gets_one_chapter_of_the_whole_run():
    assert plan_chapters([], 0, 72000, pace=600) == [Chapter(0, 72000, MIN_S - TITLE_S - END_S, [])]

def test_title_and_end_cards(db, tmp_path):
    # locked plan: [experiment title, f"Hypothesis: {h}", f"Prediction: {p}", f"Plan locked {date:%b %d, %Y}"];
    # no locked plan: [title, "No plan was locked for this run"];
    # verdict: [f"Verdict: {level words}", first check with ok False, else ok None, its text, f"Next run: {change}" when non-empty];
    # no verdict: ["No verdict yet"]
```

and in `tests/test_timelapse.py`: `test_a_reel_of_a_finished_run` (probe: 1920 × 1080, duration within 30–60 s ± 0.2).

- [ ] **Step 2: Run them to verify they fail**

Run: `cd worker && uv run pytest tests/test_moments.py -q`
Expected: FAIL at import.

- [ ] **Step 3: Implement `collect_moments`**

- `intervention`: events of that kind, caption `detail["message"]`.
- `quality`: events `quality` and `camera_moved`; caption `detail["message"]` if present, else the text of the first
  note whose `evidence` holds the event id, else "Quality flag" / "Camera moved".
- `change`: events `change`; caption from the first note citing it, else `f"Change detected: {vessel label}"`.
- `half_way`: per condition group (as the legend groups them), the vessel at the lower median of its fitted
  `half_time_h` (`fit.ok` and `fit.reached`); `t = half_time_h[0] * 3600`; caption as in the test, the number formatted
  by `format_measurement`.
- `checkpoint`: at the verdict's `t` with the verdict body's first sentence of its explanation; with no verdict, the
  last note of level `checkpoint` with its observation; neither: no moment.

- [ ] **Step 4: Implement `plan_chapters`**

```text
pace = reel_pace(frame ts)                                # run seconds per reel second
window(m) = [max(t0, m.t - PRE_S * pace), min(t1, m.t + POST_S * pace)]
chapters = merge the windows of time-sorted moments where they overlap; seconds = (t_to - t_from) / pace
while TITLE_S + END_S + sum(seconds) > MAX_S and more than one moment is left:
    drop the moment with the highest RANK value, the latest first among equals; re-merge
if no moments: one chapter [t0, t1] with seconds MIN_S - TITLE_S - END_S
elif the total is under MIN_S: multiply every chapter's seconds by (MIN_S - TITLE_S - END_S) / sum(seconds)
```

- [ ] **Step 5: Implement `make_reel`**: the title card for `TITLE_S`, each chapter through
  `schedule(frame ts, seconds, t_from=, t_to=)` with the caption of the latest chapter moment at or before the slot's
  `t` (the first moment's before it) and its kind in words, the end card for `END_S`, all through one `encode` call.
  CLI `media reel RUN_ID`.

- [ ] **Step 6: Run the tests and the worker checks**, make the Genze reel and look at the title card, one chapter and
  the end card as in Task 4 Step 10.

- [ ] **Step 7: Commit** (key scan first)

```bash
git add worker/argus/media worker/argus/cli.py worker/tests/test_moments.py worker/tests/test_timelapse.py
git commit -m "feat(media): highlights reel cut from stored moments, 30-60 s (D-85)"
```

---

### Task 6: Videos on Results (worker API and web)

**Files:**
- Create: `worker/argus/media/jobs.py`, `worker/argus/api/media.py`, `worker/tests/test_api_media.py`,
  `web/lib/media.ts`, `web/components/results/VideosCard.tsx` (+ `.module.css`), `web/tests/media.test.ts`
- Modify: `worker/argus/api/app.py`, `worker/argus/export/bundle.py` (record `/media`), `worker/tests/test_bundle.py`,
  `web/lib/types.ts`, `web/lib/api.ts`, `web/app/experiments/[id]/results/ResultsScreen.tsx`

**Interfaces:**
- Consumes: `make_timelapse`, `make_reel`, `refusal`, `MediaRefused`, `RunFiles.media_path`.
- Produces:
  - `MediaJobs(db, settings, recipes, makers: Mapping[str, Callable[..., Path]] | None = None)` with
    `start(run_id: str, kind: str) -> None` (raises `MediaBusy` or `MediaRefused`) and
    `states(run_id: str) -> dict[str, dict]`. A state is `{"state": "none"}`, `{"state": "running", "progress": float}`,
    `{"state": "ready", "size_bytes": int, "made_at": str}` (from the file on disk, so it survives a restart) or
    `{"state": "failed", "reason": str}`. Jobs run on a daemon thread.
  - Routes: `POST /api/runs/{run_id}/media/{kind}` (kind `timelapse` or `reel`) → 202 with the new state; 404 run not
    found; 409 `f"a {kind} is already being made"` or the refusal reason. `GET /api/runs/{run_id}/media` →
    `{"timelapse": state, "reel": state}`. `GET /api/runs/{run_id}/media/{kind}.mp4` → the file as `video/mp4`, or 404
    `f"no {kind} yet"`.
  - `create_app(..., media: MediaJobs | None = None)`.
  - Web: types `MediaKind`, `MediaState`, `MediaView`; `getMedia(runId)`, `makeMedia(runId, kind)`,
    `mediaUrl(runId, kind)` (`/bundles/<run>/<kind>.mp4` in replay mode); `formatBytes(n: number): string` and
    `videoRow(state: MediaState, readOnly: boolean): { status: string; action: "make" | "again" | null; download: boolean }`
    in `lib/media.ts`.

- [ ] **Step 1: Write the failing worker tests** in `tests/test_api_media.py` (fake makers that wait on an event and
  write a small file, injected through `create_app(media=...)` in a variant of `api_client`)

```python
def test_making_a_video_answers_202_then_becomes_ready(...):
    assert client.post(f"/api/runs/{run.id}/media/timelapse").status_code == 202
    release.set()
    state = wait_for(lambda: (s := client.get(f"/api/runs/{run.id}/media").json()["timelapse"])["state"] == "ready" and s)
    assert state["size_bytes"] > 0
    r = client.get(f"/api/runs/{run.id}/media/timelapse.mp4")
    assert r.status_code == 200 and r.headers["content-type"] == "video/mp4"

def test_a_second_request_while_making_is_409(...): ...      # "a timelapse is already being made"
def test_a_running_run_is_refused_with_409(...): ...         # "the run is still running"
def test_a_failed_job_says_why(...): ...                     # maker raises MediaError("x") → {"state": "failed", "reason": "x"}
def test_no_video_yet_is_404(...): ...                       # GET reel.mp4 → 404 "no reel yet"
def test_an_unknown_kind_is_422(...): ...
```

and in `tests/test_bundle.py`: the recorded set includes `/api/runs/<id>/media`, and a made timelapse is copied in and
listed in `media`.

- [ ] **Step 2: Write the failing web test** `web/tests/media.test.ts`

```ts
test("sizes read like the rest of the app", () => {
  assert.equal(formatBytes(31_400_000), "31.4 MB");
  assert.equal(formatBytes(950_000), "0.9 MB");
});
test("each state offers what can be done", () => {
  assert.deepEqual(videoRow({ state: "none" }, false), { status: "Not made yet", action: "make", download: false });
  assert.deepEqual(videoRow({ state: "running", progress: 0.42 }, false), { status: "Making… 42 %", action: null, download: false });
  assert.deepEqual(videoRow({ state: "ready", size_bytes: 31_400_000, made_at: "2026-11-01T10:00:00Z" }, false), { status: "31.4 MB", action: "again", download: true });
  assert.deepEqual(videoRow({ state: "failed", reason: "ffmpeg is not on PATH" }, false), { status: "Failed: ffmpeg is not on PATH", action: "again", download: false });
  assert.deepEqual(videoRow({ state: "none" }, true), { status: "Not made for this run", action: null, download: false });
});
```

- [ ] **Step 3: Run both to verify they fail**

Run: `cd worker && uv run pytest tests/test_api_media.py -q` and `cd web && npm test`
Expected: FAIL (no routes; no `lib/media.ts`).

- [ ] **Step 4: Implement `MediaJobs`, the routes and the `/media` recording**

- [ ] **Step 5: Implement the web side.** `VideosCard({ runId })`: a `Panel` titled "Videos" placed after the next-run
  panel on Results; two rows, "Timelapse" ("The whole run in 20 s with its curves") and "Highlights reel" ("The
  moments that mattered, 30–60 s"); each shows `videoRow`'s status, a Make / Make again button (hidden when
  read-only), and a Download link (`<a href={mediaUrl(...)} download>`) when ready. While a row is running, the card
  polls `getMedia` every 2 s. A 409 from `makeMedia` shows its detail under the row.

- [ ] **Step 6: Run the worker and web checks; check the card in the browser** (live on 3000: make a timelapse of the
  Genze run from the card, watch the progress, download it; replay on 3001 after re-exporting: Download only).

- [ ] **Step 7: Commit** (key scan first)

```bash
git add worker/argus/media/jobs.py worker/argus/api worker/argus/export/bundle.py worker/tests/test_api_media.py worker/tests/test_bundle.py web/lib web/components/results web/app/experiments web/tests/media.test.ts
git commit -m "feat(results): Videos card makes and downloads the timelapse and the reel"
```

---

### Task 7: Validation table (worker)

**Files:**
- Create: `worker/argus/analyze/validation.py`, `worker/tests/test_validation.py`
- Modify: `worker/argus/cli.py` (`validation`)

**Interfaces:**
- Produces: `Row(check: str, run: str, result: str)` (frozen dataclass),
  `validation_rows(db, recipes, run_ids: Sequence[str] | None = None) -> list[Row]` (default: every `finished` or
  `stopped` run, oldest first) and `render_table(rows: Sequence[Row]) -> str` (`| Check | Run | Result |` Markdown).
  The run cell is `f"{experiment title} ({run id})"`. A check with nothing stored for a run gives
  `Row(check, run, "not measured yet")`.

- [ ] **Step 1: Write the failing tests** in `tests/test_validation.py` (each builds `finished_run` and adds the rows
  it needs through `repos`)

```python
def test_scale_from_a_card_with_its_print_check(): ...
    # calibration card "standard", mm_per_px 0.2, rel 0.01, print_scale 0.98 →
    # "standard card · 0.2000 ± 0.0020 mm/px · print check 98.0 mm of 100 mm" (the ± part from format_measurement)
def test_scale_from_dish_rims(): ...                 # "dish rims at the dataset's stated 90 mm diameter · <mm/px ±>"
def test_noise_floor_names_its_method(): ...         # derived noise_floor, method noise_floor/1 →
    # "delta_e: 0.21 dE00 (still period)"; noise_floor_wobble/1 → "(wobble of all readings)"
def test_counting_against_labels(): ...              # reference values → "sprouted: mean absolute error 0.40 count, exact on 80% of 20 frames"
def test_events_caught(): ...                        # "'Dye added' at t 20 min → change after 45 s"; none after → "→ no change detected after it"
def test_claim_checker_counts(): ...                 # "3 accepted first try, 1 after a retry, 1 written by code; rejections: number outside a ref ×2, unknown ref ×1"
def test_models_and_spend(): ...                     # "SAM 4 of 5 calls succeeded · spend $0.12"
def test_a_run_with_nothing_stored_reads_not_measured_yet(): ...
    # bare finished run: every check's row is "not measured yet" (models: "SAM 0 of 0" is not printed; it is "not measured yet")
def test_the_table_is_markdown():
    assert render_table([Row("Scale", "Dye (r1)", "x")]).splitlines() == ["| Check | Run | Result |", "|---|---|---|", "| Scale | Dye (r1) | x |"]
```

- [ ] **Step 2: Run them to verify they fail** — `cd worker && uv run pytest tests/test_validation.py -q` → FAIL at import.

- [ ] **Step 3: Implement the rows** (all from stored records; nothing recomputed but counts, differences and means)

- Scale: the run's first calibration. Card: `f"{card} card · {mm/px ±} · print check {print_scale * 100:.1f} mm of 100 mm"`;
  `ruler`: `f"two-click ruler · {mm/px ±}"`; `dish`: `f"dish rims at the dataset's stated {d:g} mm diameter · {mm/px ±}"`
  with `d` the `dish_diameter_mm` of the run's manifest (`load_manifest(run.source.manifest)`), or `f"dish rims · {mm/px ±}"`
  when the run has no manifest. The ± is `format_measurement(mm_per_px, mm_per_px * rel_uncertainty, "mm/px")`.
- Noise floor: the latest `noise_floor` derived row per metric, `f"{metric}: {value:.2g} {unit} ({method})"`.
- Counting against labels: `agreement(db, run_id, metric)` for each metric with reference values;
  `f"{metric}: mean absolute error {mae:.2f} {unit}, exact on {share:.0%} of {frames} frames"`.
- Events caught: each intervention, `f"'{message}' at {clock} → change after {lag:.0f} s"` with the first `change`
  event at or after it; the clock as `clock_text` without the time of day.
- Claim checker: note attempts per note slot; passed on attempt 1, passed after attempt 1, notes with
  `check_status == "fallback"`; rejection reasons counted by the text before the first `:`, the three most common.
- Models: `function == "segment"` calls with status `ok` of all, and `run_spend_usd`; no segment calls → not measured yet.

- [ ] **Step 4: Add the CLI** — `validation [--runs ID ...]` prints `render_table(validation_rows(...))`.

- [ ] **Step 5: Run the tests and the worker checks, then print the table for the real database**
  (`uv run python -m argus validation`) and read every row against what the app shows for that run.

- [ ] **Step 6: Commit** (key scan first)

```bash
git add worker/argus/analyze/validation.py worker/argus/cli.py worker/tests/test_validation.py
git commit -m "feat(validation): the README's table, printed by code from the database (D-86)"
```

---

### Task 8: README, notices and docs

**Files:**
- Create: `README.md`
- Modify: `THIRD_PARTY_NOTICES.md`, `docs/knowledge-base/11-tech-stack-and-libraries.md` (Pillow, Inter),
  `docs/knowledge-base/17-build-plan.md` (phase 5 progress), `docs/knowledge-base/15-decisions-log.md` (one row per
  ruling made during execution that changes a decision)

- [ ] **Step 1: STOP — ask Aymen** which licence the README states for Argus's own code (he chooses; nothing is
  assumed).

- [ ] **Step 2: Write `README.md`** with these sections, in this order: the one-line pitch and the loop (plan → watch
  → measure → judge → next run); "Everything shown was built Oct 27 – Nov 4, 2026" (verbatim, its own line, bold); the
  public replay link (the Task 3 URL); how it works in five bullets (frames, SAM outlines, measurements in code with ±,
  claim-checked notes, verdict ceiling); Meta models and where each is used — SAM 3.1 (segmentation), Muse Spark 1.3
  (routine notes and recipe drafts), Muse Wonder 1.0 (verdicts, critique, next run), Muse Spark Open on Baseten (the
  routine tier, switchable in Settings); setup (uv, Node 24, ffmpeg on PATH, copy `.env.example` to `.env`,
  `cd worker && uv run python -m argus dev`); making videos and bundles (the three commands); the validation table as
  printed by `uv run python -m argus validation` (pasted unedited, with the command above it); safety rules (CLAUDE.md
  rule 8 in plain words, and no medical advice); licence and `THIRD_PARTY_NOTICES.md`. No voice features, no
  screenshots containing third-party frames (screenshots come from the dye run in Task 9).

- [ ] **Step 3: Notices** — add Inter (Rasmus Andersson and contributors, SIL Open Font License 1.1, file
  `worker/argus/media/fonts/OFL.txt`, used for the video overlays) and Pillow (HPND).

- [ ] **Step 4: Re-export the Genze bundle with its videos and redeploy** (`export-bundle`, then
  `bash scripts/deploy-replay.sh`), and check the Videos card's downloads on the public link, logged out.

- [ ] **Step 5: Commit** (key scan first)

```bash
git add README.md THIRD_PARTY_NOTICES.md docs/knowledge-base
git commit -m "docs: README with the replay link, models, setup and the validation table; notices for Inter and Pillow"
```

---

### Task 9: The dye run's bundle, videos and redeploy (after Aymen's dye run)

**Files:**
- Modify: `README.md` (validation table, screenshots), `docs/images/` (new screenshots of the dye run only),
  `docs/knowledge-base/17-build-plan.md`

- [ ] **Step 1: STOP until the dye run is recorded and finished.** Then make its timelapse and reel from the Videos
  card and watch both in full.
- [ ] **Step 2: Export its bundle and redeploy**; check both runs on the public link at 1440 and 390 px, logged out.
- [ ] **Step 3: Re-print the validation table into the README unedited**; add two screenshots of the dye run's
  replay (Run view, Results) to `docs/images/` and the README.
- [ ] **Step 4: Run the worker and web checks, commit** (key scan first):
  `git commit -m "docs: the dye run's replay, videos and validation"`.
- [ ] **Step 5: STOP — ask Aymen for the go-ahead to merge into `main`** (recommended by Nov 3).
