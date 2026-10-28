# 20 · Chosen demo experiment: salt-stress germination dose-response

> **Decided Oct 27, 2026 (D-31).** This is the main real experiment for the demo. The steel corrosion test (`06-modes-and-recipes.md` catalog) stays a **later, optional** second run if time allows.

## Status and suggested tweaks (Oct 27 evening) [proposed, Q-14]

**Not started yet.** Start by **Oct 29** at the latest; mung beans sprout within about a day, so 60–72 h of footage is enough and leaves Nov 1–2 for analysis. Suggested changes before starting (none needs new purchases):

1. **8 beans per jar instead of 5** (48 total): sprouted-fraction steps of 12.5% instead of 20% give a better time-to-50% per jar, and 8 stays under SAM video's 16-object limit per jar crop.
2. **Print the Argus Card** (Claude generates the printable file first) and tape it upright in the plane of the jar fronts, plus the ruler as a backup. The card gives automatic mm scale; one object of known length in frame (e.g. a measured toothpick) becomes the "measurement accuracy" row of the validation table.
3. **Salt by weight if a kitchen scale is available:** 0, ~3 and ~12 g/L (about ⅛ and ½ tsp per cup), with the actual grams written down. Ax then works in real units (g/L).
4. **Analysis as a dose trend across all 6 jars** (time-to-50% per jar from a fitted curve, then a regression on salt) alongside the locked pairwise prediction. This uses every jar, which matters with 2 jars per dose. A third jar per dose (9 jars) would help further if the frame still shows every bean clearly.
5. **Start time:** film the phone clock for 5 s in **normal** mode, then switch to fast motion (at ×600 a 5 s clip is less than one recorded frame). Set the camera's date and time; the MP4's creation time is the backup.
6. **About 24 h in, take one phone photo** of the jars from the camera's position so SAM concepts ("mung bean", "root", "sprout") can be tested on real roots before the footage is ready.

## Why this experiment

- Looks like real research: a dose-response with replicates, the kind used in crop salinity-tolerance and seed testing.
- Shows the most of Argus: multiple vessels with a control, sprout onset per seed, root length in mm, curves, time to 50%, the salt level that halves sprouting, a verdict with evidence, an Ax next-run suggestion.
- Works with owned hardware: the Canon XA50 sitting **flat on a table** (no stand available), side view.
- Fits the schedule: start Oct 27 evening, stop Oct 30 evening.
- Known limits: barely uses color correction; only one Ax round fits (Argus suggests the next salt levels, but there's no time to run them).

## Design

| Item | Value |
| --- | --- |
| Hypothesis | More salt makes mung beans sprout slower and less |
| Prediction | High-salt beans reach 50% sprouted at least 12 hours later than no-salt beans |
| Factor | Salt level, 3 doses: none, low (⅛ tsp per cup water), high (½ tsp per cup water). Starting guesses; Ax refines later |
| Replicates | 2 jars per dose = **6 jars**. The jar is the replicate, not the bean |
| Seeds | 5 dried mung beans per jar (30 total) |
| Blinding | Lids labeled A–F only; the letter→dose key is written down out of the camera's view |
| Randomization | Left-to-right order drawn by lot (A–F on paper scraps) |
| View | **Side view** through the clear wall, like vertical root assays in plant labs |
| Duration | ~72 h (Oct 27 evening → Oct 30 evening); extend to Nov 1 at most |

## Materials

**Buy:** dried mung beans (not cooked/canned), 6 identical clear containers or jars with lids (flat-sided square containers preferred; round jars OK), brown paper towels or brown coffee filters or blue shop towels (dark background for white roots), masking tape.

**Have:** Canon XA50 + AC adapter + SD card, table salt, tap water, measuring spoons (⅛, ½ tsp, tablespoon), 3 mixing cups, ruler or printed Argus Card, marker, books to raise the camera, plain sheet for the background, phone.

## Steps

1. **Mix 3 waters:** 1 cup each of plain, + ⅛ tsp salt, + ½ tsp salt. Stir until dissolved; label the cups.
2. **Per jar:** soak a dark paper towel in that jar's water, squeeze out the extra, press it flat against the inside of the front wall. Hold 5 beans against the clear wall and press the towel over them, so the order from the camera is: wall → beans → towel. Stuff the middle with more wet crumpled towel to hold everything against the glass. Beans sit about one-third down from the top.
3. **Add about 2 tablespoons** of the same water to the bottom. The towel's bottom edge must touch it; the beans must stay well above it (they need air). Lid on.
4. **Make 2 jars per water** (6 total). Rinse the spoon between salt levels.
5. **Label lids A–F,** draw the order by lot, write the key out of view.
6. **Line them up in one straight row,** bean side facing forward, same distance from the camera, plain sheet behind them. Tape the ruler or card **upright on the front of the first jar** (same plane as the beans).
7. **XA50 flat on the table** facing the row, raised on books so the lens is level with the beans; zoom to fill the frame with all 6 jars and the ruler.
8. **Light stays constant for 3 days:** room lights on day and night with blinds closed, or an LED lamp to the side (not reflecting into the lens, not too close or the lids fog). A big open cardboard box around the jars and lamp blocks room light changes.
9. **Camera:** AC power, manual focus, manual exposure, fixed white balance, Full HD, **fast motion ×600** (one frame every 20 s; ~7 min of video, ~2 GB for 72 h).
10. **Write the hypothesis and prediction with the time,** film the phone clock for 5 s, start recording. Check after 1 hour that it's still recording.
11. **Don't touch anything.** If a towel dries out, add the same small amount of water to every jar and note the time.
12. **Stop Thursday evening (Oct 30):** stop recording, film the clock again, copy the video to the laptop, keep the A–F key.

## What Argus measures

| Level | Measurements |
| --- | --- |
| Each bean | Sprouted or not, and when (root longer than a set threshold, e.g. 2 mm); root length in mm over time; growth speed in mm/h |
| Each salt level | % sprouted over time; time to 50% sprouted ± error; mean root length and growth speed |
| Overall | Salt level that halves sprouting (fitted dose-response); four-level verdict with evidence; Ax suggestion for the next salt levels |
| Quality checks | Lighting drift, camera bumps (ruler/marker shift), fogged lids, drying towels, effects below the noise floor, researcher notes linked to changes |

## Import into Argus

Import video with: start time from the clock clip, **time-scale factor 600**, the A–F → dose key, recipe `seed-germination` (side view: concepts `seed` and `root`; root length via skeleton). Replay mode can play it through the live pipeline, labeled on screen as a replay.

## Later, optional

Steel corrosion run (rust area % and color, hours per round, 2–3 Ax rounds) if time allows after Oct 30.
