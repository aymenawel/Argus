# 07 · Features and priorities

> Priority key: **MUST** = needed for the Nov 4 demo · **SHOULD** = build if time allows · **LATER** = after the hackathon (roadmap slide). Build MUST items first, in the order of `17-build-plan.md`.

## Must have for the demo

| # | Feature | Spec in one line |
| --- | --- | --- |
| M1 | Setup wizard + measurement preview | SAM outlines vessels → researcher confirms/merges/removes → labels control/treatment/replicate → card + lighting check → first measurement shown on the live frame for approval → plan locked |
| M2 | Argus Card calibration | ArUco markers give mm per pixel and perspective; gray patch corrects color drift (`09-measurement-and-calibration.md`) |
| M3 | Multi-vessel tracking | One camera, several vessels, stable IDs, per-vessel ROI and events |
| M4 | 2–3 recipes | Color-change reaction, foam/growth height, seed germination |
| M5 | Measurements with ± | Units from calibration; ± from the noise-floor self-test (first minutes measure things that should not change) |
| M6 | Curve fit + time-to-target | Fit growth/decay/kinetics models; report rate, lag, half-life with confidence intervals; "reaches target in ~2 h 10 min" |
| M7 | Structured AI notes + claim checker | JSON notes (`prompts/schemas/note.json`); code checks every number against the database before saving |
| M8 | Four-level verdict with rival explanations | SUPPORTED / NOT_SUPPORTED / INCONCLUSIVE / TOO_EARLY; deep-tier self-critique (`prompts/deep/verdict-critique.md`) |
| M9 | Timelapse with synced chart overlay | Video plus chart, timestamp and notes in step |
| M10 | Ax next-run suggestion, batched | Several vessels = several trials per round; Muse explains the pick |
| M11 | Import video (moved up from Should, D-29) | MP4 or photo folder through the same pipeline; **time-scale factor** for in-camera fast motion (XA50 ×600/×1200) plus a start time, so frames get real timestamps. Needed for the multi-day demo run |
| M12 | Public replay page (D-30) | Read-only static export of one finished run (timelapse + overlay, timeline, charts, verdict, validation) that judges and voters can open without hardware |
| M13 | View catalog, AI-picked views (D-49) | Fixed frame on every experiment plus data views from a catalog; Muse picks in setup (strict JSON, catalog IDs only), code checks each pick against its data needs, the researcher confirms or swaps. 12 views for the hackathon |

## Should have

- Phone alerts via ntfy (event + clip link)
- **Ask Argus**: chat that answers by querying the measurement/event database, every answer linked to rows and frames
- Report (Markdown/PDF) + CSV export + run record
- Design-of-experiments planner and replicate calculator
- Researcher review: confirm/dismiss every alert; reports stay **draft until approved**

## Features by area (full detail)

### Watching
- Live view (also from a phone), adaptive pace, switchable analysis modes (`06-modes-and-recipes.md`)
- Trigger on the metric once measurements exist; phase detection (lag / growth / plateau)
- Frame-quality gate (blur, glare, occlusion); hand-in-frame detection logs a likely intervention and asks what happened
- Drift watch: background brightness, card color, camera position; says which measurements may be affected

### Memory and timeline
- Event log: every event has a timestamp, snapshot(s) and an AI note
- Clickable timeline: jump to any event and see frames before and after
- Smart timelapse: full timelapse + highlights reel (chaptered by events, captions, 30–60 s, smart speed, flicker smoothing, stabilization, side-by-side treatment vs control)
- Running summary: hourly summaries roll up into daily summaries (keeps long runs cheap)
- Status card always on screen: current values, trend arrows, predicted time to target, verdict so far

### AI notes
- Fixed structure: observation (numbers) · interpretation · confidence · links to frame and chart point
- Three levels: event, checkpoint, insight
- No spam: repeated "no change" collapses into one line ("No significant change 02:00–05:30")
- **Claim checker** rejects and regenerates notes whose numbers don't match the data (fits the "Verifiable Agents" session)

### Researcher notes and AI questions
- Typed or voice notes (Muse Voice Transcribe), pinned to the exact frame or any timeline point
- Tags: **Observation**, **Intervention**, **Question**; AI answers questions and links interventions to what follows ("bubbling rose 40% within 10 min of your sugar addition at 3:15 PM")
- Quick-tap buttons (added water, moved jar, opened lid)
- AI asks questions when unclear ("The plant moved out of frame at 2:00 AM. Intentional?"), batched and rate-limited so it doesn't nag

### Science (see `08-science-rigor.md`)
- Hypothesis builder, rival explanations up front, pre-registration lock, randomized layout, blinding, controls/replicates prompts, DOE planner, replicate calculator
- Statistics in code, four verdicts, self-critique, what-if planning for the next run
- Compare runs; run history across a recipe

### Closed loop and control (see `10-hardware-and-control.md`)
- Ax suggestions (batch trials, warm start from the DOE plan, two objectives, safety bounds, "why this pick", researcher override)
- Smart-plug rules ("heater off if foam > 50 mm", "lights 16 h on / 8 h off"), approval mode, hard limits, dry-run, emergency stop; every action logged as an intervention

### Plant mode specifics
- Day/night aware (measure only with lights on, or switch the light on briefly for a photo)
- Events: wilting, new leaf, flowering, watering (sudden soil color change)
- Daily growth report per plant

### Reproducibility and sharing (see `08-science-rigor.md`)
- Run record, raw data kept, re-analyze old runs with a newer recipe, tamper-evident hash chain
- Exports: report, CSV, Jupyter notebook that rebuilds figures, RO-Crate package, eLabFTW entry, highlights video
- Share link, "Replicate this" button, privacy (local-only mode, face blurring)

## Later (roadmap)

- Smart-plug rules (Plant mode light schedule, "heater off if foam > 50 mm"), AI proposes / human approves, hard limits (moved from Should: no plug this hackathon, D-44)
- Sensors (Bluetooth thermometers, Arduino serial, instrument-display reading, instrument log import), cross-checks between sources, sensor health
- More cameras (top + side), phone as camera, microscope profiles, OpenFlexure
- Lab-notebook and RO-Crate exports, share links, "Replicate this", recipe library, recipe builder from plain words
- Flow fields (OpenPIV), animal tracking, colony counting
- Robots via PyLabRobot (Opentrons OT-2 etc.)
- A pilot with one real lab (e.g. a local college biology or chemistry course lab) to measure time saved and which events matter
