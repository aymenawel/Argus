# Calm redesign and one-product demo (design)

Approved in conversation with Aymen on Nov 3, 2026 (decision D-98), from the Run-screen mockup in two looks; Aymen chose the light "clean lab" look. Deadline: submission Nov 4, 9 PM ET; the video comes after this.

## Goal

Argus feels organised, calm and clearly an AI lab partner: each screen answers one question, shows the answer first and tucks details behind a tap, in plain words (D-95). The public link opens the same product in a demo mode, not a separate "replay" site.

## Look

- **Light "clean lab" is the default**: warm off-white ground `#f5f6f3`, white surfaces, ink text `#0e1116`, muted `#5b6470`, hairlines `rgba(14,17,22,.08)`, one teal accent `#0f9f94` (ink `#0b7d74`), soft shadows, 16 px corners, Inter with tabular numbers. Dark ("instrument": ground `#07090d`, surfaces `#0e1218`, accent `#2dd4bf`) stays available; Settings offers Light, Dark and System. A viewer who never chose gets light.
- One primary action per screen; technical details behind an ⓘ; long text behind **More** / **Why**.

## Run screen ("What's happening?")

1. Header: crumb (Experiments / title), the title, one status line (state · run time · samples, and in the demo "Recorded run · nothing here is live"), and **See results**; **Stop run** while live.
2. **Argus line**: one or two sentences built by code from stored records, no model call. Lead: the sample whose main reading changed most since its first reading, with its value and ±, and the control's value when there is a control ("Sample C (test, warm) changed the most: 25.12 ± 0.06 ΔE, against 4.55 ± 0.06 ΔE for the control (B)."). Then the verdict's first sentence when a verdict exists, with its level as a tag in the page's words; else, with a plan, "Argus judges your idea from {check time}."; else nothing more. Nothing measured yet: "Argus is watching. Nothing measured yet."
3. The picture as the hero, with each sample's value tag and outlines as today; an ⓘ opens the details now spread around it (source, scale, SAM objects, spend, the thinned-pictures note). Published-data credit stays visible under the picture.
4. Sample cards (as today's readouts), the most-changed one highlighted.
5. A simple scrubber: one track from 0 to the run's end with the notable events as dots (hand or object, threshold, camera moved, check time) and a playhead; dragging or clicking sets the playhead. It replaces the Run screen's timeline panel.
6. Side panel: Notes | Ask Argus (D-97). A note shows its main sentence and chips; **More** opens confidence, other possible causes, suggestion and question.
7. The verdict panel leaves the Run screen (it lives on Results).

## Results ("What did we learn, and what next?")

1. Header as above with **Back to the run**.
2. The Argus line with the verdict.
3. The curves chart.
4. **What Argus checked**: one line counting the checks ("1 passed · 1 not settled · 1 failed"), opening the full verdict panel (checks, other possible causes, reviews).
5. **Next run**: the three tiles and the first sentence of the suggestion; **Why** opens the rest.
6. **Numbers**: the fitted-values table and the label comparison, folded.
7. Videos.

## Home

Experiments as cards: the latest picture, the title, a status line, the verdict tag; **New experiment**. The same card component serves the demo's list.

## Demo mode (`NEXT_PUBLIC_ARGUS_REPLAY=1`)

- The public link opens the Experiments list with the bundled runs (titled "Experiments", not "Replays"); the rail's Experiments goes there; a small **Demo** tag sits in the rail; the list says once "Everything shown was built Oct 27 – Nov 4, 2026".
- Every run page says it is recorded and not live (status line); published data keeps its credit and licence.
- Controls that need the worker are hidden or disabled with a short hint (new experiment, stop, add a note, ask, review, make videos), as today's read-only rules already do.
- The green banner component is removed.

## Setup wizard

New look through the tokens only; its steps don't change.

## Testing

Pure helpers get node tests: the Argus line (most-changed sample, the control comparison, the verdict sentence, the no-verdict and nothing-measured cases), the checks count, the theme default. Screens are checked by rendering the real runs (live app and demo) at desktop and phone width; tsc, eslint, prettier and the web tests stay clean.

## Out of scope

New features beyond the layout; changes to the worker; the setup wizard's structure.
