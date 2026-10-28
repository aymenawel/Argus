# 16 · Open questions and day-one checks

> Close items here as they're answered; move the answer into the right file and log any decision in `15-decisions-log.md`.

## Waiting on information

- [x] **Q-01 Judging rubric.** Received Oct 27: Impact 30%, Use of Meta AI Tooling 25%, Technical Depth & Execution 20%, Demo 25% (`01-hackathon-rules-and-dates.md`).
- [x] **Q-02 Prize tables.** Received Oct 27: Indie $150K/$100K/$75K/$50K/$25K; bonus prizes listed in `01`.
- [x] **Q-03 Partner credits:** none came through (Oct 27). Only the $150 Meta credit, plus the $30 Modal signup credit.
- [x] **Q-11 Open-weight bonus without credits:** decided Oct 27: skip for now, keep Baseten as an option (D-33). Original question: pay Baseten per token with a card (~$24 for the routine tier, see `05`) to stay eligible for the $10K prize, or drop it and run everything on Meta's $150?
- [ ] **Q-04 Expiry of the $150 Meta credit** (check the Billing page) and set the Spend Limit notification.
- [x] **Q-05 Hardware on hand:** Nuroum V11 webcam (AW-V11) and Canon XA50. The XA50 stand is not available right now, so the XA50 sits flat on a table (side views). No USB microscope, no smart plug (`10-hardware-and-control.md`).
- [x] **Q-06 Demo experiment:** salt-stress germination dose-response, side view on the XA50 (D-31, `20-demo-experiment-germination.md`). Steel corrosion stays optional for later. A short genuinely live moment on the webcam is still needed for the video (e.g. setup wizard detecting the jars live).
- [ ] **Q-07 Smart plug:** buy a Shelly (Gen2+ local API) for the closed-loop demo beat?
- [ ] **Q-08 USB HDMI capture card + mini-HDMI cable:** buy one so the XA50 can be a live camera?
- [ ] **Q-09 X account** for the Most Viral post (any account works; engagement counts until Nov 8 EOD).
- [ ] **Q-10 A real user:** can one teacher or lab instructor try Argus (or the replay page) before Nov 4 for an Impact quote?

## Day-one technical checks (answers replace estimates)

- [ ] Real token count for a `muse-spark-1.3` call with 2 snapshots (expect ~3,000 image tokens at ~1280 px; try 768 px)
- [ ] Same call on `muse-wonder-1.0`; confirm image input works
- [ ] Strict JSON-schema output with `prompts/schemas/note.json` on the Responses API (`text.format`)
- [ ] Prompt caching hit on the second call (`usage.input_tokens_details.cached_tokens > 0`)
- [ ] SAM 3.1 image call on a real frame; parse with `meta-sam-parser`; check how well one-word concepts work on foam, seeds, liquid level
- [ ] SAM 3.1 video call on a short MP4 downsampled to 1–2 fps
- [ ] Short MP4 to Muse Spark: token cost of clip mode
- [ ] Voice note through `/v1/asr/transcribe` (WAV mono 16-bit, 16/24 kHz)
- [ ] Webcam: request MJPEG and confirm 2560×1440 @ 30 fps actually arrives (YUV is capped at 360p); can exposure and white balance be locked with `CAP_DSHOW` (focus is fixed)? Read values back; find the closest sharp distance
- [ ] XA50: fast-motion recording keeps going on AC power for hours (check after 1 h); note the real start time; check whether on-screen displays can be turned off on HDMI out
- [ ] `cv2.aruco.ArucoDetector` available in the installed OpenCV
- [ ] `pip install ax-platform` works on Windows + Python 3.12

## Questions for Meta office hours (weekdays 10–11 AM ET, `#office-hours`)

- Exact token cost of video input for Muse Spark (fps sampling)?
- Are SAM 3.1 concept-prompt object ordinals stable across video frames?
- Recommended `reasoning.effort` for short structured outputs on Muse Spark 1.3?
- Any limits on base64 image size/throughput for SAM image calls at ~1 request per second?

## Decided not to pursue (for now)

Local Glimmer or Spark Open hosting, self-hosted SAM, fine-tuning anything, materials-only focus, equipment anomaly monitoring.
