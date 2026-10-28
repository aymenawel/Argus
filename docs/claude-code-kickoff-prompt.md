You are taking over the build of **Argus**, my entry for the Meta Global AI Developer Hackathon (Indie track, "Push the Frontier"). Building period is **Oct 27 – Nov 4, 2026; submission is due Wed Nov 4, 9:00 PM ET.** I'm a solo developer (team name Argus Labs). I want a product that could actually ship: professional, reliable, well organized, and impressive in a 3-minute demo.

## 1. Read everything before you plan

Read these fully, in this order, before proposing anything:

1. `CLAUDE.md`
2. Every file in `docs/knowledge-base/` — start with `README.md`, then `00` through `20` in order. Don't skim; the decisions, verified library verdicts, API details, costs, rubric and demo experiment are all there.
3. `prompts/` (system rules, deep-tier critique, JSON schemas) and `THIRD_PARTY_NOTICES.md`.

When you're done, give me a short summary of what Argus is, the hard rules, and the build plan, so I can confirm we're aligned. The knowledge base is the source of truth: where it says **[decided]**, follow it; where it says **[proposed]**, you may suggest something better (with reasons) before changing it. Log every new or changed decision in `docs/knowledge-base/15-decisions-log.md` and tick answered items in `16-open-questions.md`.

## 2. The vision (short version)

Argus is an AI lab partner that turns any webcam or camera into a scientific instrument. It runs a **closed experiment loop: plan → watch → measure → judge → next run.**

- A researcher sets up vessels (jars, dishes, wells) with a control and treatments, locks a hypothesis, and points a camera at them.
- A cheap local **watcher** decides when something changed; **SAM 3.1** segments each vessel's contents; Python code turns masks into **calibrated measurements in mm with ±** (Argus Card / ruler).
- **Muse Spark 1.3** writes structured, evidence-linked notes; **Muse Wonder** gives and critiques verdicts (SUPPORTED / NOT_SUPPORTED / INCONCLUSIVE / TOO_EARLY) with rival explanations; a **claim checker** rejects any AI note whose numbers don't match the data.
- **Ax** proposes the next run's settings; smart-plug control (later) closes the physical loop.
- It must never feel like a "simple image analyzer" (a banned anti-project). Change over time, real units, controls, verdicts and the next-run loop must be visible everywhere.

The first real demo experiment is already recording: **salt-stress germination dose-response** (mung beans, 3 salt levels × 2 jars, side view, Canon XA50 fast motion ×600, Oct 27–30). Protocol and import settings: `docs/knowledge-base/20-demo-experiment-germination.md`. Import video + labeled replay mode must handle it.

Judging rubric (optimize for it): **Impact 30%, Use of Meta AI tooling 25%, Demo 25%, Technical depth & execution 20%.**

## 3. Non-negotiable engineering rules

(From `CLAUDE.md` and `02-architecture.md`; repeated here because they matter.)

1. The LLM never computes numbers. Measurements, stats and curve fits are Python.
2. Only `segment()` and `reason()` call models. Model IDs, base URLs and keys come from config/env.
3. Prompts live in `prompts/`; outputs use the JSON schemas in `prompts/schemas/`; every AI note passes the claim checker.
4. Log every model call (model, tier, input/cached/output tokens, cost, latency) and enforce the per-run spend cap.
5. Evidence is never overwritten: observation → measurement → AI explanation → researcher review are separate records.
6. Public repo: no secrets in code or history. `.env` only; mirror variables in `.env.example`.
7. New work only. Nothing copied from other projects of mine.
8. Safety rules for hardware control and no medical advice.
9. Use the vocabulary in `18-glossary.md` in code, UI and docs.
10. Never fake data or results. Anything simulated or replayed is labeled as such in the UI.

if you think anything here doesnt make sense or there is better alternatives after understanding context let me know
## 4. Libraries and repos

Use the **verified verdicts in `docs/knowledge-base/11-tech-stack-and-libraries.md`** (USE / OPTIONAL / SKIP / BUILD) and the API details in `04-models-and-api.md`. In particular: `openai` SDK against `https://api.meta.ai/v1`, the official `meta-sam-parser`, OpenCV + scikit-image, numpy/scipy, statsmodels, `uncertainties`, Ax 1.x (`ax.api.client.Client` — not the old `AxClient`), ruptures, FastAPI, SQLite, Next.js + TypeScript, ffmpeg via subprocess. Respect the SKIP list (ffmpeg-python, go2rtc, supervision, etc.) and the license notes (keep GPL code out).

- Don't add a dependency that isn't in `11` without asking me first and explaining why it beats writing it ourselves.
- Check current docs before using an API (Context7 or the official docs); versions and APIs change. Pin versions in `requirements.txt` / `package.json` once they work.
- Use the Meta cookbook (`meta-models/meta-model-cookbook`) patterns for vision input, structured output, caching and SAM.

## 5. Skills

**Use these skills I already have installed:**

- **superpowers** — use its workflow for the whole build: brainstorming before features, writing plans before code, test-driven development, systematic debugging for bugs, verification before claiming anything is done, and code review before merging a phase.
- **taste** and **impeccable** — for design quality and polish of the UI and the overall product.
- **Context7** — for up-to-date library documentation instead of relying on memory.
- **ui-ux-pro-max** — only if you judge it genuinely useful for this project; tell me if you use it and why.
- The 7 reviewed project skills in `.claude/skills/` (experimental-design, statistical-power, uncertainty-and-units, hypothesis-generation, scientific-critical-thinking, opencv, trackpy-particle-tracking) — use them for the science and vision code.

**Other skills mentioned in the knowledge base** (for example more from `K-Dense-AI/scientific-agent-skills` such as statistical-analysis, timesfm-forecasting, cellpose, protocolsio-integration, or from `jaechang-hits/SciAgent-Skills`): **if you think one would help and it isn't installed, ask me first.** I'll tell you whether to install it. Read a skill's `SKILL.md` and scan its scripts before using it. Never install the `what-if-oracle` skill (non-commercial license).

## 6. UI and design direction

I want a **modern, professional, calm "scientific instrument" interface** — something a real lab would trust and a judge would find genuinely cool to watch. Not a generic admin template, not a toy. Imagine if one of the big companies where to design and develope a product like this how it would look

I've attached three UI screenshots (they're also in my Downloads folder). **They are different products; use them only as inspiration for layout and feel, not as things to copy:**

1. **Camera event dashboard (evizz):** big video player in the center, an event **timeline scrubber with clip thumbnails** underneath, and a scrollable **feed of events** on the right with thumbnails and timestamps. → Inspiration for Argus's **run view**: live/replay video with mask overlays, a timeline with event markers, and a right-side feed of notes and events.
2. **Video editor (captions timeline):** stacked **tracks** under a player with a playhead, captions as blocks on the timeline, clean side tools. → Inspiration for Argus's **timeline**: one track per vessel showing its measurement curve and events, AI notes and researcher notes as blocks on their own tracks, a single playhead synced to the video.
3. **Robot operations dashboard (robodog):** live camera with on-image labels, status cards, parameters panel, controls, and a dense data chart. → Inspiration for **status cards** (current values, trend, time-to-target, verdict so far, spend), the **control panel** (smart plug, Ax next run), and the **results charts**.

Design requirements:
- Light and dark themes; a restrained palette with one accent color; clear typography; numbers with units and ± everywhere.
- The video and the data must feel connected: scrubbing the timeline moves the video, charts, notes and masks together.
- Every AI claim is clickable to its evidence (frame + measurement rows).
- Clear labels for **LIVE** vs **REPLAY** vs **IMPORTED**, and for provisional verdicts.
- Responsive enough for a laptop and a tablet; a phone view for alerts and status.
- Before building screens, show me a short design direction (layout sketches or a description per screen, color and type choices) for approval.

Screens I expect (refine with me during planning):
1. **Experiments** — list and create.
2. **Setup wizard** — camera source (webcam / imported video / replay), vessel detection with SAM and confirm/merge/remove, labels (control/treatment/replicate, blinded A–F), card/ruler calibration, lighting check, measurement preview, hypothesis + prediction + threshold, plan lock.
3. **Run view** — video with overlays, status cards, timeline tracks, notes/events feed, quick-tap intervention buttons, voice note.
4. **Results** — per-vessel and per-group curves with error bands, fitted parameters, dose-response, four-level verdict with rival explanations and critique findings, validation numbers.
5. **Next run** — Ax suggestions (batched across vessels) with Muse's explanation.
6. **Report and export** — report, CSV, run record.
7. **Settings / usage** — models per tier, spend per run and total, cache hit rate.
8. **Public replay page** — read-only static export of one finished run for judges and voters.

### Motion and micro-interactions (make it feel alive)

I want the app to feel alive and responsive, like a live instrument that is always watching. Motion should communicate state and cause-and-effect, never decorate for its own sake. Use the **taste** and **impeccable** skills to keep it tasteful.

Principles:
- **Purposeful:** every animation tells the user something (new data arrived, something is live, a claim was verified, a step completed).
- **Fast and calm:** most transitions 150–300 ms with smooth easing; nothing bouncy or slow. Larger moments (verdict reveal, plan lock) can take a little longer.
- **Performant:** animate only `transform` and `opacity` where possible; never let animation stutter the video or charts; keep 60 fps on my laptop.
- **Accessible:** respect `prefers-reduced-motion` (fall back to simple fades or no motion), and never use motion as the only way to show information.
- **Consistent:** define motion tokens (durations, easings) once and reuse them, like colors and spacing.

Moments I want (refine and add your own ideas):
- **Live indicator:** a soft pulse on the LIVE badge and on vessels that are currently changing; REPLAY and IMPORTED badges are calm and static.
- **Logo as the "watching" loader:** the tracking point orbits the iris ring while Argus is analyzing, and the ring closes when a measurement locks in (see `brand/README.md`).
- **SAM masks:** outlines trace in or fade in when segmentation returns; vessel boxes draw in during setup detection; hover highlights a vessel everywhere it appears (video, timeline track, chart line, feed).
- **Numbers:** values tween smoothly to their new value (with units and ±) instead of jumping; trend arrows animate on change.
- **Feed:** new notes and events slide in at the top with a brief highlight; a note that passes the claim checker shows a small "verified" check animation; a rejected claim is shown subtly, not alarmingly.
- **Timeline:** a smooth playhead; event markers grow on hover and show a frame thumbnail preview; scrubbing snaps gently to events; video, masks, charts and notes move together.
- **Charts:** new points extend the line smoothly; fitted curves and error bands draw in on the Results screen.
- **Verdict:** a deliberate reveal when the verdict changes (provisional → final), with the evidence chips appearing in sequence.
- **Setup wizard:** step transitions, the measurement preview appearing on the live frame, and a satisfying lock animation when the plan is locked.
- **Controls:** clear hover, press and focus states on every interactive element; skeleton loaders shaped like the content; toasts for alerts.

Library: see "Animation tools: brainstorm, then ask me" below. Don't add any animation dependency without my OK.

### Brand and logo

A logo and brand kit are in `brand/` (read `brand/README.md`): an eye whose iris is an open measurement ring with a tracking point orbiting in the gap. I like this logo; treat it as the **reference and starting point**, not a locked file.

- **Fit it to the product.** You may refine it so it sits well in the website and app (stroke weights, spacing, sizes, how it pairs with the type and palette), as long as the concept stays recognizable: the eye, the open ring, the orbiting tracking point.
- **Bring it to life.** Add micro-animation to the logo, for example the tracking point orbiting the ring while Argus is watching or analyzing, the ring closing when a measurement locks in, a gentle "blink" or settle on page load. Use it as the app's loading/"watching" indicator.
- **Demo video asset.** Produce an animated version of the logo we can use in the demo video (an intro/outro sting of a few seconds): a high-quality export such as MP4/WebM with a transparent or matching background, plus the source used to make it.
- **Colors:** build the UI palette around the tokens in `brand/README.md`: ink `#0B1220` / `#F5F7FA` and the single accent, Argus teal `#0FA3A3` (light) / `#2DD4BF` (dark). Use the favicon and app icons in the Next.js app and the logo in the README.
- **Show me first.** Before replacing any file in `brand/`, show me the refined logo and the animation (screenshots or a short preview) for approval, and keep the originals until I approve.

### Animation tools: brainstorm, then ask me

Before adding any animation dependency, research and brainstorm the options (libraries, repos, tools) that could help with the UI micro-interactions, the animated logo and the demo-video asset. For example: Motion (formerly Framer Motion), CSS/View Transitions, GSAP, Lottie/dotLottie, Rive, React Spring, Remotion for rendering video, and anything else you find. For each, give me: what it would be used for, why it fits, license (and whether it's free for our use), bundle/performance cost, maintenance status, and whether it's worth it versus doing it ourselves. Recommend a short list, then **ask me which to use** before installing anything (none of these are in the verified list in `11`).

## 7. Code quality ("a developer can pick this up")

- Clear module boundaries matching `02-architecture.md` (`worker/`: capture, watcher, segment, measure, analyze, reason, claims, storage, api; `web/`: Next.js app with typed API client and reusable components).
- Typed everywhere (Python type hints + pydantic models; TypeScript strict). Small functions, descriptive names, no dead code, no copy-paste duplication.
- Tests for the measurement, calibration, stats, claim checker and watcher logic (use recorded sample frames as fixtures). Lint and format (ruff + black or ruff format; ESLint + Prettier).
- A real `README.md`: what Argus is, architecture diagram, setup, how to run, Meta models used, validation table, "Everything shown was built Oct 27 – Nov 4, 2026", licenses.
- Small, meaningful commits with clear messages.

## 8. How to work with me

- **Plan first.** After reading, propose the implementation plan phase by phase, aligned with `17-build-plan.md`, and wait for my approval before writing code.
- **Day-one checks first** (`16-open-questions.md`): real token usage with 2 snapshots, strict JSON schema output, a SAM 3.1 call parsed with `meta-sam-parser`, the Nuroum webcam in MJPEG at 1440p with exposure locking. Report the real numbers and update the knowledge base.(Based on the context if you believe there is a better way feel free to let me know)
- **Ask, don't guess.** If something isn't answered in the knowledge base, ask me. Don't invent requirements, data, prices or API behavior.
- **Push back.** If you see a better alternative, or think something in the plan is a bad idea, tell me with reasons before building it.
- **Features must actually work.** Verify each feature end to end with real runs and tests before calling it done; show me the evidence (test output, screenshots, real measurements). No mock data passed off as real.
- **Protect the deadline.** Must-have features first (`07-features.md`); flag early if anything is slipping so we can cut from the Should list, never from demo time.
- Keep the knowledge base current as decisions are made.

Start by reading everything in section 1, then give me your summary and your questions.