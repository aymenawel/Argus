# 16 · Open questions and day-one checks

> Close items here as they're answered; move the answer into the right file and log any decision in `15-decisions-log.md`.

## Waiting on information

- [x] **Q-01 Judging rubric.** Received Oct 27: Impact 30%, Use of Meta AI Tooling 25%, Technical Depth & Execution 20%, Demo 25% (`01-hackathon-rules-and-dates.md`).
- [x] **Q-02 Prize tables.** Received Oct 27: Indie $150K/$100K/$75K/$50K/$25K; bonus prizes listed in `01`.
- [x] **Q-03 Partner credits:** none came through (Oct 27). Only the $150 Meta credit, plus the $30 Modal signup credit.
- [x] **Q-11 Open-weight bonus without credits:** decided Oct 27: skip for now, keep Baseten as an option (D-33). Original question: pay Baseten per token with a card (~$24 for the routine tier, see `05`) to stay eligible for the $10K prize, or drop it and run everything on Meta's $150?
- [ ] **Q-04 Expiry of the $150 Meta credit** (check the Billing page) and set the Spend Limit notification.
- [x] **Q-05 Hardware on hand:** Nuroum V11 webcam (AW-V11) and Canon XA50. The XA50 stand is not available right now, so the XA50 sits flat on a table (side views). No USB microscope, no smart plug (`10-hardware-and-control.md`).
- [x] **Q-06 Demo experiment:** salt-stress germination dose-response, side view on the XA50 (D-31, `20-demo-experiment-germination.md`). Steel corrosion stays optional for later. A short genuinely live moment on the webcam is still needed for the video (e.g. setup wizard detecting the jars live). **Update Oct 27 evening: not started yet** (see Q-14).
- [x] **Q-07 Smart plug:** no (Oct 27, D-44). Plug control moves to Later.
- [x] **Q-08 USB HDMI capture card:** no (Oct 27, D-44). The XA50 is used for recordings only.
- [ ] **Q-12 Fast live experiment** for the live demo moment and the multi-round Ax loop (D-42). Undecided. Claude's suggestion: household iodine clock (vitamin C, 2% iodine tincture, 3% hydrogen peroxide, starch): a sharp color switch at a predictable time, rounds of a few minutes, Ax tunes amounts to hit a target time. Alternative: yeast foam height (~30 min per round)
- [ ] **Q-13 Demo video tooling:** undecided. Aymen will use AI tools and wants Claude to render motion graphics (logo sting, overlays, title cards) for a professional edit; formats to be chosen with the animation-tool research
- [ ] **Q-15 UI direction** (canvas https://claude.ai/artifact/2JeEMitFwx3e3egzNbptwg): v1 data-terminal style was too boxy (Aymen, Oct 28); v2 "soft instrument" (D-50) plus the view catalog (D-49) is on the canvas. Awaiting approval and a typeface pick: Inter, Manrope or Plus Jakarta Sans
- [ ] **Q-16 Animation tools:** recommended Motion (MIT) for UI motion plus CSS/SVG for pulses and outlines; HyperFrames (Apache-2.0) for demo-video motion graphics; skip GSAP in the app, Lottie, Rive, React Spring. Awaiting Aymen's pick
- [ ] **Q-17 Frontend dependencies not in `11`:** Tailwind CSS v4, Radix UI primitives, lucide-react icons, d3-scale/d3-shape, openapi-typescript (dev). Awaiting approval
- [ ] **Q-14 Germination start:** must start by **Oct 29** at the latest to have ~60–72 h of footage by Nov 1. Claude's suggested tweaks before starting are in `20-demo-experiment-germination.md`
- [ ] **Q-09 X account** for the Most Viral post (any account works; engagement counts until Nov 8 EOD).
- [ ] **Q-10 A real user:** can one teacher or lab instructor try Argus (or the replay page) before Nov 4 for an Impact quote?

## Day-one technical checks (answers replace estimates)

Run Oct 27 with the scripts in `worker/probes/` (total spend ≈ $0.19). Numbers are recorded in `04`, `05`, `09` and `11`.

- [x] Real token count for `muse-spark-1.3` with 2 snapshots: 3,805 input tokens at 1280 px, 1,725 at 768 px
- [x] Same on `muse-wonder-1.0`; image input works
- [x] Strict JSON-schema output with `note.json` and `verdict_critique.json` on the Responses API (`text.format`) on both models
- [x] Prompt caching: **only with `prompt_cache_key`** (D-39); then 95% of input cached
- [x] SAM 3.1 image call parsed with `meta-sam-parser`: 24/24 coins on a test photograph. **Still open:** one-word concepts on real seeds, roots, foam, liquid level (needs the real setup)
- [x] SAM 3.1 video call on a short MP4: works, 16-object cap, stable IDs
- [x] Short MP4 to Muse Spark: ~72 input tokens per second at 240×240, 10 fps
- [x] Voice note through `/v1/asr/transcribe`: correct transcript in 1.9 s
- [ ] **Nuroum webcam** (not connected on Oct 27): MJPEG 2560×1440 @ 30 fps, exposure/WB lock read back, closest sharp distance. The built-in HP camera was tested instead: MJPEG 720p, WB lock reads back, exposure lock unknown (`09`)
- [ ] XA50: fast-motion recording keeps going on AC power for hours; real start time; HDMI overlays (when the experiment starts)
- [x] `cv2.aruco.ArucoDetector` available in `opencv-python` 5.0.0; detects all 4 card markers
- [x] `ax-platform` 1.3.1 installs on Windows + Python 3.12 (~45 s, torch 2.14.1 CPU); outcome constraints and attached trials verified

## Questions for Meta office hours (weekdays 10–11 AM ET, `#office-hours`)

- Exact token cost of video input for Muse Spark (fps sampling)? (Measured ~72 tokens/s at 240×240, 10 fps; how it scales with resolution and fps is still unknown)
- Are SAM 3.1 concept-prompt object ordinals stable across video frames? (Probe: yes within one video request; across separate requests unknown)
- Is a `prompt_cache_key` required for prompt caching? (Probe: no hits without it; the docs call it optional)
- Recommended `reasoning.effort` for short structured outputs on Muse Spark 1.3?
- Any limits on base64 image size/throughput for SAM image calls at ~1 request per second?

## Decided not to pursue (for now)

Local Glimmer or Spark Open hosting, self-hosted SAM, fine-tuning anything, materials-only focus, equipment anomaly monitoring.
