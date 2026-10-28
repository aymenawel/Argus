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
