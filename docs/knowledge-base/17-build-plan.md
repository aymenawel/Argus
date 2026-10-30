# 17 · Build plan (Oct 27 – Nov 4, 2026)

> Solo, 9 days. Rule: the working loop ships first; nice-to-haves start only if ahead; **the last two days protect the demo video**. If the Must tier slips past Nov 1, cut from Should first. Never cut demo time.

| Day | Date | Goal | Done when |
| --- | --- | --- | --- |
| 1 | Tue Oct 27 | Repo + env + day-one checks (`16-open-questions.md`). **Start the multi-day germination recording on the XA50** (setup below). Print and measure the Argus Card. Order the capture card and plug | API calls return with real token counts; webcam MJPEG 1440p and exposure lock tested; XA50 recording |
| 2 | Wed Oct 28 | Worker capture loop, frame-quality gate, watcher (ROI, normalization, keyframe SSIM + color, debounce/cooldown/check-in), SQLite schema. Watch **Agents 102 (12 PM)** | Watcher triggers on a real slow change and ignores a lamp switch |
| 3 | Thu Oct 29 | `segment()` with SAM 3.1 + parser; IoU ID matching; measurements (area, height, count, Lab color); ArUco scale; noise-floor self-test | Per-vessel numbers in mm with ± stored every trigger |
| 4 | Fri Oct 30 | `reason()` tiers, rules prompt, strict JSON notes, claim checker, event log, running summary; model-call cost logging | A trigger produces a saved, checked note; a bad number gets rejected |
| 5 | Sat Oct 31 | Next.js dashboard: setup wizard (vessels, labels, measurement preview, plan lock), live MJPEG view, timeline, live charts via SSE | Full run can be started and watched from the browser |
| 6 | Sun Nov 1 | Multi-vessel control comparison, curve fit + time-to-target, four-level verdict + deep critique, 2–3 recipes | A run ends with a verdict that cites rows and frames |
| 7 | Mon Nov 2 | ffmpeg timelapse with chart overlay + highlights reel; Import video (analyze the multi-day footage); Ax batched next run; smart-plug rule (if a plug is available) | Highlights reel exports; Ax returns a batch with an explanation |
| 8 | Tue Nov 3 | Validation runs (ruler accuracy, staged events), bug fixes, README (what was built during the hackathon, setup, licenses), **public replay page** (static export on Vercel), record demo footage incl. an XA50 infrared clip. Last day for submission questions | Validation table filled with real numbers; replay link works logged-out |
| 9 | Wed Nov 4 | Edit the 3-min video; final checks; **submit early (aim for the afternoon), deadline 9:00 PM ET**; then post the 20–30 s clip on X and submit the post link (Most Viral) | Repo public, video link works, submission confirmed, X post live |
| — | Nov 5–8 | Share the X post and gallery link (engagement counts until **Nov 8 EOD**) | — |
| — | Mon Nov 9, 12 PM | Closing ceremony and live final round (top 5 per track) | — |

## Progress

**Phase 1, foundation: done Oct 28** on branch `phase-1` (plan `docs/superpowers/plans/2026-10-28-phase-1-foundation.md`).

- **Worker:** config, domain records, SQLite (WAL, one writer, immutable measurements and locked plans, audit chain), four TOML recipes, live events with resume across restarts, card detection with print check and ruler fallback, colour reference and drift, geometry and colour metrics in mm with ±, and `python -m argus dev`.
- **Web:** v2 tokens, rail and shell, `/kit` with every shared component, and the Experiments page end to end.
- **Evidence:** 89 worker tests pass; ruff, ESLint, TypeScript and the Next build are clean. Browser checks at 1440 and 390 px in light and dark. Live: a new experiment reached a second tab over the event stream; with the worker down the page showed its URL and Retry; after a worker restart the open page reloaded its list by itself.
- **Final review:** a fresh reviewer found 1 Critical (inverted print-scale correction) and 7 Important issues. All Critical and Important issues were fixed with a failing test first, except `rectify` sizing, which moves to phase 2. 13 minors are deferred.
- **Against the day plan:** the SQLite schema (day 2), measurements and ArUco scale (day 3) and the UI foundation (day 5) are in place. The capture loop and the watcher (day 2) are not started; phase 2 begins with them, then `segment()`.

**Phase 2, watch and measure: built Oct 28-29** on branch `phase-2` (plan `docs/superpowers/plans/2026-10-28-phase-2-watch-and-measure.md`).

- **Worker:** detections, events and model calls with evidence triggers; run calibration (card or ruler) with a colour reference that settles over the first readings; SAM 3.1 image and video segmentation (one shared client, no hidden retries, spend reserved under the cap); outlines, vessel assignment and IoU tracking; video import (sampling, per-vessel SAM video, full-frame image fallback) and live runs (gate and watcher at up to 5 fps, background analysis, camera and card moves followed); the quality gate (sharpness around the vessels, lamp changes matched, hands by a vessel caught); `POST /runs`, timeline, frames, cameras and `argus run`.
- **Web:** the Run view (frame with outlines and regions in force, readouts, editor-style timeline with a draggable playhead) over a batched snapshot store; Node's test runner for its data layer.
- **Evidence on real data (Oct 28-29, food colouring in cold, room and warm water, compact card):**
  - Live run on the Nuroum at 720p, 21 min: 1,802 frames, 123 SAM calls all ok, $0.31. Warm water coloured through within ~2 min of the dye (25.6 dE00); room ~5 and cold ~3 at 18 min. Noise before the dye 0.6 dE00.
  - Import of a phone recording (6.8 min, 942 samples): 3 SAM video calls ok, $0.57, 16 min to process; the warm glass switched at the same moment as in the live run.
  - Scale: the card's printed 30 mm ruler measured 30.01-30.13 mm on the webcam and 30.15 mm on the phone (target within 2 %).
  - The real runs found five problems the synthetic tests missed, each fixed test-first (D-62 to D-64): a plain wall failed the sharpness gate; an arm in front of the glasses was measured as dye; a hand over the card read as a camera move; a camera still settling at the first frame skewed every colour reading; correction flickered at its cut-off. After the fixes the phone import's noise before the dye fell from 3.3-3.7 to 0.4-0.6 dE00 (2.1 in the cold glass, where the phone's exposure was locked 2 s in) and correction no longer flipped (74 times before).
- **Final review:** a fresh reviewer found 2 Critical and 11 Important issues (a dead camera's frozen frame stored as evidence; the gate stuck after a lamp change; the spend cap overshot; hidden SDK retries; Stop ignored; and more). All were fixed with a failing test first; minors are in the ledger. 221 worker tests and 6 web tests pass.

**Recipes from words and re-analysis of published data: built Oct 29** on branch `reanalysis` (plan `docs/superpowers/plans/2026-10-29-recipes-from-words-and-published-data.md`, D-70 to D-74).

- **Built:** Argus drafts an experiment's own recipe from the researcher's words, checked against its toolbox (D-73) and editable until the plan locks; the "What will you do?" dialog; `touching_count`; published image sequences with a manifest and provenance (badge and credit on every frame); the dish rim as the ruler; retrospective verdicts and the run-to-run rival; agreement with a dataset's labels, kept apart from measurements; the Genze plate adapter (`python -m argus dataset genze`).
- **Evidence on real data (Genze & Grimm, rye vs pearl millet, 6 dishes from 4 runs, 95 frames over 47 h):** the dialog drafted seed + root, "seeds with a root" (touching ≥ 2 mm) every 30 min, in 11–17 s for ~$0.006 a draft. The dish ruler gave **6.90 px/mm ± 5.1 %** (expected ≈ 7). The import made 12 SAM video calls (all ok), one note and a Wonder verdict: **$0.33 in all**. The verdict was **Inconclusive · retrospective** with the run-to-run rival open, numbers only from code.
- **What it found:** SAM 3.1 segments the seeds but **no roots** (0 objects for nine phrasings, image and video; KB 04), so Argus counted 0 germinated seeds in every dish while the labels reach 6–10. The agreement table shows it plainly: **off by 5.3 seeds on average, the same in 23 % of frames**, half-way never reached against 12–24 h in the labels. The measurement must change before this plate can carry the demo (open item: count seeds whose SAM outline grew, since SAM's seed masks follow the radicle).
- **After the final review (1 Critical, 6 Important, all fixed test-first) and `grown_count` (D-75), re-run Oct 30:** drafted from the same words, the recipe looked only for "seed" and counted "seeds that grew 2 mm". Against the labels: **off by 2.0 seeds on average (was 5.3), the same in 35 % of frames**. Rye dishes ended at 7, 9 and 8 against labels of 9, 9 and 10, reaching half-way 3–8 h after the labels (a seed counts once its outline is 2 mm longer, later than the eye sees a radicle). SAM found no seeds in two of the three millet dishes, so those are gaps, not zeros. The verdict was Inconclusive · retrospective (1 of 3 treatment dishes measured; rivals open). $0.20 for the import, notes and verdict.
- **Stills and the latch (D-76), same experiment and plan, Oct 30:** whole-frame image calls (95, all ok) measured every dish; a seed once seen grown stays counted. **Off by 1.5 seeds on average** (best of the three runs). Final counts: rye 8, 9, 9 against 9, 9, 10; millet 6, 9, 9 against 6, 10, 9. Argus reaches half-way at 21–27.5 h, 2–15 h after the labels, latest for millet, whose first radicles are under the 2 mm threshold. Verdict Inconclusive · retrospective with all three millet dishes measured and the rivals open. $0.37 for the run's calls.

**Phase 4: speed in the verdict, the next run, and Results: built Oct 30** on branch `phase-4` (plan `docs/superpowers/plans/2026-10-30-phase-4-speed-next-run-results.md`, D-78 to D-80).

- **Built:** the plan says whether it predicts a level, a half-way time or a rate (D-78, migration 008); the recipe's curve fitted per vessel with ± and named refusals (D-79); the verdict on fitted half-way times and rates, naming refused or unreached fits and plateaus more than a quarter apart; a Results page (curves per condition with the checkpoint and half-way points, the fitted values with ±, the verdict, the agreement with labels, the next run) linked from the Run view; the next run: vessels per condition from a two-sample t-test on the run's own spread, run length from the slowest curve, Ax levels for a numeric factor (`ax-platform` 1.3.1), explained by Muse Wonder through the claim checker (D-80, migration 009).
- **Evidence on the Genze plate, judged on speed (Oct 30):** "I'll test whether pearl millet germinates faster than rye" was drafted by Muse Spark Open as half-way time, lower in pearl millet by at least 6 h (the checkpoint was moved from the drafted 48 h to 24 h, inside the 47 h plate). All six dishes fitted a logistic curve: rye half-way at **22.3–25.7 h**, pearl millet at **26.1–26.5 h** (each ± 0.1–0.3 h). The verdict was **Inconclusive · retrospective**: the millet dishes reached half-way 2.0–2.4 ± 1.6 h *later* than rye (± 1.0 h before the review added the spread between dishes), below the 6 h smallest effect, with plateaus from 6.0 to 9.1 (named) and four rivals open. Against the labels, off by 1.5 seeds on average (35 % exact); the labels put millet's half-way at 12–19 h, before rye, so Argus's 2 mm outline threshold delays millet, whose first radicles are thin and short; the measurement, not the biology, makes millet look slower. Next run: **3 vessels per condition** (spread 1.2 h within conditions against 6 h) and **48 h**, no levels (species isn't numeric); Wonder suggested both species side by side in one run with watering, temperature and seed batch logged. $0.71 for the experiment (import $0.39, three verdicts, two next-run calls).
- **Found and fixed on the real run:** the plan's smallest effect printed as a bare "6" for a half-way time (the ref took the metric's unit; now "6 h", or unit/h for a rate); the first real next-run answer put labels ("Observation:") in its prose and repeated a unit ("16 vessels vessels"), fixed in the prompt.
- **Final review (fresh Opus reviewer):** 1 Critical, 8 Important, 15 minor. Fixed test-first (D-81): a dish with no fitted value no longer drops out of a fitted verdict (it caps it at Inconclusive); fitted effects aren't judged by the readings' noise floor; no rate from a curve still rising; 2 controls and the spread between dishes in each difference's ±; a baseline refused; Ax reads "20 °C", skips a "water" control and picks every level from its model; the prompts state a half-way plan as one. 580 worker tests and 30 web tests pass.

## Today: start the chosen experiment

**Salt-stress germination dose-response, side view on the Canon XA50 (no stand needed).** Full protocol: `20-demo-experiment-germination.md`. Start tonight (Oct 27), stop Thursday evening (Oct 30).

## Optional purchases (not needed for the experiment)

- USB HDMI capture card (UVC) + mini-HDMI-to-HDMI cable: makes the XA50 a live second camera
- Shelly smart plug (Gen2 or newer local API) + a lamp to switch: closes the loop in the demo

## Order of work inside the stack

Meta API + `meta-sam-parser` and the cookbook patterns on day 1 → watcher on days 1–2 → measurements by day 3 → reasoning by day 4 → UI by day 5 → science by day 6 → video, Ax and control by day 7.

## Submission checklist

- [ ] Repo **public**; no keys in history (`.env` ignored; `.env.example` committed)
- [ ] README: what Argus is, **"Everything shown was built Oct 27 – Nov 4, 2026"**, setup, Meta models used, validation table, `THIRD_PARTY_NOTICES.md`
- [ ] 3-minute video, link accessible without login
- [ ] Submission lists every contributor (solo: Aymen)
- [ ] Meta credits claimed (done) and spend limit set
