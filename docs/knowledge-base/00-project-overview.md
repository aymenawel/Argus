# 00 · Project overview

> **Read this first.** One page that explains what Argus is, who it is for, and what makes it different. Every other file goes deeper on one part.

## What Argus is

**Argus is an AI lab partner that watches experiments through a webcam or USB microscope, measures what changes in real units, judges the researcher's hypothesis, and suggests the next run.** It is named after Argus Panoptes, the hundred-eyed watchman of Greek myth who never slept.

The product is a **closed experiment loop**, not a camera that describes pictures:

```
Plan  →  Watch  →  Measure  →  Judge  →  Next run  →  (back to Plan)
```

| Stage | What happens | Main parts |
| --- | --- | --- |
| Plan | Hypothesis, prediction and success threshold are locked; controls and replicates set up | Setup wizard, design-of-experiments helpers |
| Watch | Cameras and sensors stream; a cheap local watcher decides when something changed | OpenCV watcher, analysis modes |
| Measure | SAM 3.1 masks each vessel; code turns masks into calibrated numbers with ± | `segment()`, measurement code, Argus Card |
| Judge | Statistics in code; AI notes and a four-level verdict with rival explanations | `reason()`, claim checker, deep-tier critique |
| Next run | Ax proposes settings (several vessels = several trials at once); smart plug can act | Ax, smart-plug rules |

## One-liners (approved wording)

- Form one-liner: **"Argus is an AI lab partner that watches your experiments, records every moment that matters, and tells you what to try next."**
- Short: **"An AI lab partner that watches your experiments so you don't have to."**
- Pitch line: **"Self-driving-lab intelligence for anyone with a webcam."**
- Access angle: AI that monitors and reasons about experiments today lives in multimillion-dollar self-driving labs and enterprise systems; students, teachers and small teams don't have it.

## Who it is for

Classroom and university labs, small R&D teams (food, cosmetics, materials), plant growers, hobby scientists. It is pitched as a **research tool**, never as a tutoring chatbot (see `13-demo-and-pitch.md`).

## The problem it solves

- Key events happen overnight or between checks, so onset times are guesses.
- Researchers measure once at the end and lose the rate, lag and curve shape.
- Judgments like "looks browner" vary by person.
- Notes are written later from memory; settings are forgotten.
- Controls and real replicates are often missing; confounders (lighting, evaporation) go unnoticed.
- The next run is chosen by gut feeling.
- In a 2016 Nature survey of 1,500+ researchers, 70% had failed to reproduce someone else's experiment and 50% their own.

## What makes Argus different

1. **General purpose through recipes.** A recipe is a config file (what to segment, which measurements, which curve, which events). New field of science = new recipe, not new code.
2. **Real units.** A printed Argus Card (ArUco markers + gray/color patches) gives mm and lighting-corrected color, with a ± on every number.
3. **Hypothesis-aware and honest.** Four verdicts (SUPPORTED, NOT_SUPPORTED, INCONCLUSIVE, TOO_EARLY), rival explanations, and a claim checker that rejects any AI note whose numbers don't match the data.
4. **Many vessels, one camera.** Control and treatments side by side, replicates built in.
5. **Cheap.** Only spends AI on frames where something changed; webcam + printed card + laptop.
6. **Closes the loop.** Ax picks next settings; a smart plug can run lights or heaters with safety limits.

## Status (as of Oct 27, 2026)

- Accepted into the **Meta Global AI Developer Hackathon**, **Indie Developer** track, theme **Push the Frontier**. Solo builder Aymen, team name **Argus Labs**.
- Building period **Oct 27 – Nov 4, 2026**. Submission due **Wed Nov 4, 9:00 PM ET**. Public repo **github.com/aymenawel/Argus**, first commit Oct 27 (new-work rule). Day-one API probes done Oct 27 (`16-open-questions.md`); the germination run has not started yet (Q-14).
- The project was called **LabLoop** until it was renamed Argus. Old docs that say LabLoop mean Argus.
- Argus is **not** the Congressional App Challenge project (that was a different app, "Whose Job?"). No code is shared between them.

## Where to go next

| You want to… | Read |
| --- | --- |
| Know the rules and dates | `01-hackathon-rules-and-dates.md` |
| Understand the system | `02-architecture.md`, `03-watcher-design.md` |
| Call the Meta API correctly | `04-models-and-api.md` |
| Check what is in scope this week | `07-features.md`, `17-build-plan.md` |
| Pick a library | `11-tech-stack-and-libraries.md` (every entry verified) |
| Understand why a choice was made | `15-decisions-log.md` |
