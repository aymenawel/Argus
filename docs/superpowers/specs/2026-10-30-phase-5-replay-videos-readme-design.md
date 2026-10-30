# Public replay, timelapse and reel, validation and README — design (phase 5)

Date: Oct 30, 2026 · Status: design approved by Aymen in chat in two parts (hosting on Vercel, Pillow approved, the
same app gated to `/replay`); this written spec awaits his review · Builds on branch `phase-4` · Decisions: D-83 to
D-86

## Why

Phases 1–4 built the loop (plan → watch → measure → judge → next run) and proved it on real data, but only on this
laptop. Judges and voters have no webcam, no worker and no keys. They need three things: a link that opens a finished
run without logging in, a video that shows days of an experiment in seconds with the measurements drawn over it, and a
README that says what was built in the hackathon and how well it measures. The rubric weighs exactly these: a public
replay link and validation numbers under Impact (30 %), the timelapse with chart overlay under Demo (25 %), and a
short clip on X for Most Viral (KB 01, 13).

**Success (by Nov 3, before the video is cut):**
- A Vercel link, opened logged out, lists the replayed runs and shows each one's Run view and Results read-only, every
  page labelled as a replay (and as published data, with credit, for the Genze plate).
- Any finished run exports a 1080p timelapse with its curves drawn over it and a 30–60 s highlights reel, from the
  command line and from a Videos card on Results.
- The README states what Argus is, that everything shown was built Oct 27 – Nov 4, 2026, how to set it up, which
  Meta models it uses where, and a validation table whose every number a script read from the database.

## Decisions

- **D-83 The public replay is the same app, gated, reading a recorded bundle.** Built with
  `NEXT_PUBLIC_ARGUS_REPLAY=1`, the web app reads GET requests from a run bundle instead of the worker, hides every
  action that writes, and a `proxy.ts` sends every path outside `/replay` (and its assets) to `/replay`. A bundle is
  the worker's own responses to the requests the Run and Results screens make, recorded in-process, so its shapes
  are the live API's by construction. Deployed from this laptop with `vercel build` and `vercel deploy --prebuilt`
  (Vercel Hobby). Bundles are git-ignored and reach Vercel only in the prebuilt output, so third-party frames never
  enter the repository. Rejected: a pure static export (Next 16 can't export the existing dynamic routes or run
  `proxy.ts`, so it needs a second root layout and replay-only page files); GitHub Pages (the frames would have to
  be committed); a hand-built standalone page (duplicates the UI the video shows).
- **D-84 Overlays are drawn with Pillow in Inter.** Pillow is approved as a direct worker dependency (Aymen, Oct 30;
  already installed as scikit-image's dependency, 13.0.0, HPND licence). Inter, the app's typeface, is committed as
  `worker/argus/media/fonts/Inter[opsz,wght].ttf` with its `OFL.txt` (SIL Open Font License 1.1), fetched from
  Google Fonts' repository after Aymen's OK on the download, and credited in `THIRD_PARTY_NOTICES.md`. Rejected:
  OpenCV's built-in stroke fonts.
- **D-85 The timelapse and the reel are made only from stored records.** Frames, outlines, readings, fits, events,
  notes and the verdict as saved; no model call, no recomputation, every number formatted by the worker. Captions are
  stored note text, which already passed the claim checker. Time on screen comes from each frame's `t`.
- **D-86 The validation table is printed by code from the database.** `python -m argus validation` builds every row
  from stored records and names the run each comes from. A row with no data behind it is printed as "not measured
  yet", never filled in by hand.
- **Scope cuts:** no 9:16 export, no music or voice-over, no report or PDF page, no editing of the 3-minute video, no
  Vercel Blob. If time runs short, cut in this order: the Videos card (the commands stay), reel moment ranking beyond
  "in time order, capped", validation rows beyond those already measured.

## Components

### 1. The run bundle (worker, D-83)

- `python -m argus export-bundle <run_id> [--out ../web/public/bundles]` writes `bundles/<run_id>/`, and
  `bundles/index.json` lists every exported run (id, title, source label, recorded date, verdict level). Re-exporting
  replaces that run's folder and its index entry.
- **Recorded responses.** The exporter drives the worker app in-process (FastAPI's `TestClient`, no network, no
  reasoner, no camera) and saves the JSON body of each GET the two screens make, at a path derived from the request:
  `api/<path with "/" kept>[__<query as k=v joined by &>].json`. The set: experiment, experiment recipe detail, the
  experiment's runs (only this run is kept in the list), plans, run, timeline, notes, verdict, reviews, fits (with no
  metric and per measured metric), agreement per measured metric (when the run has labels), next run, and each kept
  frame's detections. A request that answers 404 is saved as a recorded 404, so the page behaves as it does live
  (no verdict yet, no next run).
- **Frames.** Each kept frame is saved once, 1280 px on the long side, JPEG quality 82. A run with more than 400
  frames is thinned: frames are kept at even steps of `t`, and every frame cited by a note, an event or the verdict is
  kept too. `manifest.json` maps every frame id of the run to the kept frame shown in its place (the nearest kept frame
  in `t`), and records the thinning ("1 frame in 5 shown; measurements use all 1,802 frames").
- **Manifest.** Run id, experiment title, source label (`live recording`, `imported recording`, `published data`),
  credit and licence for published data (from the run's provenance), the recorded date, the export time, the git
  commit, the frame map and counts, and the media files included.
- **Media.** If `timelapse.mp4` or `reel.mp4` exist for the run, they are copied into the bundle.
- **Refusals.** A run still `running` is refused with the reason (`finished` and `stopped` runs export). So is a
  bundle over 60 MB after thinning, with its size, so the deploy limit is met before upload.

### 2. Replay mode (web, D-83)

- `lib/replay.ts`: `isReplay()` reads `NEXT_PUBLIC_ARGUS_REPLAY`; `bundlePath(runId, path, query)` maps an API
  request to its bundle file; `replayFrame(runId, frameId)` maps through the manifest's frame map.
- `lib/api.ts`: in replay mode its request function fetches the bundle file for GETs (a recorded 404 raises the same
  `ApiError`) and refuses every other method with `ApiError(405, "This is a read-only replay")`. `frameUrl` returns
  the bundle frame. `lib/events.ts` opens no event stream in replay mode.
- **Read-only flag.** One `useReadOnly()` (true in replay mode) hides: Stop, the note composer and quick
  interventions, Get a verdict, verdict reviews (Confirm, Dismiss, Mark resolved), Suggest the next run, and the
  Videos card's export buttons (its download links stay when the bundle has the files).
- **Routes.** `/replay`: one card per bundled run (title, source label, recorded date, verdict chip, links to its Run
  view and Results). `/replay/[runId]` and `/replay/[runId]/results` render the existing `RunScreen` and
  `ResultsScreen`, given the experiment id from the manifest. In replay mode the rail shows Replay and a link to the
  GitHub repository only.
- **Labels.** A banner on every replay page: "Replay · recorded <date> · nothing on this page is live", plus, for
  published data, "Published data: <credit> · <licence>", and "Everything shown was built Oct 27 – Nov 4, 2026". When
  frames were thinned, the Run view's frame says so (from the manifest).
- `proxy.ts`: in replay mode, redirects every path except `/replay`, `/replay/*`, `/bundles/*`, `/_next/*` and the
  icons to `/replay`; outside replay mode it does nothing.
- **Deploy.** `npx vercel@<version> build` then `deploy --prebuilt --prod` from `web/` with the replay variable set,
  the version pinned exactly in the plan (a release at least two weeks old); the Vercel CLI runs through `npx` and is
  not added to `package.json`. Aymen runs `npx vercel login` once in his
  terminal; `.vercel/` and `web/public/bundles/` are git-ignored.

### 3. Timelapse with overlay (worker, D-84, D-85)

- `argus/media/` (new): `layout.py` (where each element goes and what text it shows, at a time `t`), `draw.py`
  (Pillow drawing at 2× and downscaled), `encode.py` (ffmpeg fed raw RGB frames on stdin: H.264, yuv420p, 30 fps,
  `+faststart`), `moments.py` (the reel's chapters).
- **Frame layout, 1920 × 1080.** The run frame on the left (fitted to 1240 × 1000) with each vessel's outline in its
  condition's colour; on the right, the main measurement's curve per vessel drawn up to the current `t` with a cursor,
  in the Results chart's colours, dashes and dot shapes; a clock in run time ("t 23.5 h") and the time of day when the
  run has a start time; the source label, and the credit line for published data; the caption of the note in effect.
- **Timing.** The output covers the run's `t` range in a chosen length (default 20 s; `--seconds`). Each output frame
  shows the source frame at or before its `t`, cross-faded into the next one when source frames are sparser than the
  output, so 95 frames over 47 h play smoothly. Gaps in readings stay gaps on the curve.
- `python -m argus media timelapse <run_id> [--seconds 20]` writes `data/<exp>/<run>/media/timelapse.mp4`.

### 4. Highlights reel (worker, D-85)

- **Chapters.** A title card (the question, the hypothesis as locked, "Plan locked <date>"), then one chapter per
  moment, then an end card (the verdict level, its first failed or open check, and the next run in one line when there
  is one).
- **Moments,** from stored records: researcher interventions (the dye drop), detected changes, quality flags (a lamp
  change, a camera move, a hand by a vessel), each condition's half-way point from its fit, and the checkpoint. Each
  chapter plays about 2 s of run before the moment and 3 s after, at a speed that fits the budget, with its caption
  (the event's or note's stored text).
- **Budget.** 30–60 s in all. When the moments don't fit, they are ranked (interventions and quality flags, then
  half-way points, then the checkpoint, then changes; earlier first within a rank) and the lowest are dropped; moments
  closer than their pre- and post-roll merge into one chapter.
- `python -m argus media reel <run_id>` writes `.../media/reel.mp4`.

### 5. Videos on Results (worker API and web)

- `POST /api/runs/{id}/media/{timelapse|reel}` starts a background job (one per run and kind at a time; 409 while one
  runs) and answers 202; `GET /api/runs/{id}/media` lists each kind's state (none, running with progress, ready with
  size and time, failed with the reason); `GET /api/runs/{id}/media/{kind}.mp4` serves the file. A refused run (not
  finished, no frames) answers 409 with the reason.
- A **Videos** card on Results: per kind, Make / progress / Download and the file's size.

### 6. Validation table (worker, D-86)

`python -m argus validation [--runs <id>...]` prints a Markdown table, each row naming its run:

- **Scale:** the run calibration's ruler length against its printed length (card), or px/mm against the dataset's
  stated dish size (Genze).
- **Noise floor:** the spread of readings before the first intervention.
- **Counting against labels:** mean absolute error and the share of exact frames (from the stored agreement).
- **Events caught:** each logged intervention against the first detected change after it, in seconds.
- **Claim checker:** notes accepted on the first try, after a retry, or written by code; rejections by reason.
- **Models:** SAM calls that succeeded out of all; spend per run.

### 7. README and notices

`README.md`: what Argus is and the loop; "Everything shown was built Oct 27 – Nov 4, 2026"; the replay link and
screenshots; the Meta models and where each is used (SAM 3.1 for segmentation, Muse Spark 1.3 for routine notes and
drafts, Muse Wonder 1.0 for verdicts, critique and the next run, Muse Spark Open on Baseten as the switchable routine
tier); setup (uv, Node, ffmpeg, `.env` from `.env.example`); the validation table as printed; the safety rules;
licences and `THIRD_PARTY_NOTICES.md` (adds Inter, SIL OFL 1.1).

## Error handling

- ffmpeg missing or failing: the media job fails with ffmpeg's last stderr line; nothing half-written is kept (written
  to a temporary name, renamed when complete).
- A run with no readings for the main measurement: the timelapse draws no curve panel and says so; the reel has no
  half-way chapters.
- A bundle file missing at view time: the page shows the same error state as a worker that's down, with the path.
- The exporter never writes outside its output folder; it never calls a model.

## Testing

- **Worker:** each recorded response equals the live response for the same request; an unfinished run and an oversize
  bundle are refused; thinning keeps cited frames and maps every frame id; frames placed by `t` (irregular `t`, gaps);
  cross-fade weights; moment selection, ranking, merging and the budget; captions only from stored text; an encode
  smoke test (3 synthetic frames → an MP4 of the expected duration, probed with ffprobe); the media routes (202, 409,
  states, file served); each validation row on a fixture database, and "not measured yet".
- **Web:** request-to-bundle path mapping (with and without a query); writes refused in replay mode; the frame map.
- **Browser:** the replay pages at 1440 and 390 px in both themes; after deploy, the link opened logged out.
- **Real runs:** the Genze plate bundled, deployed and exported as timelapse and reel; then the dye run once recorded.

## Order and dates

1. Bundle and replay mode, deployed with the Genze plate (Oct 31).
2. Timelapse and reel from the command line (Nov 1).
3. Videos card, validation table, README (Nov 2).
4. After Aymen's dye run: its bundle, timelapse and reel; the validation table re-printed; redeploy (Nov 2–3). Merge
   into `main` by Nov 3.

## Open items for Aymen

- `npx vercel login` once, in his terminal, before the first deploy.
- OK to download Inter's font file (about 0.9 MB, Google Fonts repository, SIL OFL) when the timelapse task starts.
