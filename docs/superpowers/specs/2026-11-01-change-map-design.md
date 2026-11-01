# Point SAM at what changed — design (fix 2)

Date: Nov 1, 2026 · Status: design approved by Aymen in chat (Nov 1); this written spec awaits his review · Builds on
branch `phase-4`, after fix 1 (D-90, D-91) · Decisions: D-92, D-93 · Source: fix 2 of
`reports/Detecting anything in lab images.md` · Time box: one day (Nov 2)

## Why

SAM 3.1 traces shapes well but recognises few lab words. Asked for "microbial colony", it found the swarming run's
colonies in only 10–67% of the pictures (fliA 0.1: 15 of 145; gfp 0.1: 97 of 145). Since fix 1 those misses are
honest gaps, but they are still gaps. A swarm that is hard to see in one picture is obvious against the same dish at
the start, and the Meta API accepts boxes and points as prompts, which need no vocabulary.

**Success:** on a re-import of the swarming run, every dish is found in clearly more pictures than before, each
outline says who drew it (SAM by name, SAM pointed at a box, or code), and nothing changes for recipes whose objects
are there from the start (seeds, glasses, foam).

## Decisions

- **D-92 When SAM finds nothing, Argus points it at what changed since the start, and outlines the change itself as a
  last resort.** Only for a concept marked `appears = true` in its recipe (an object that is not there at the start
  and grows into view; colony-spread v2 marks "microbial colony"). Per vessel and concept, on a frame where the
  by-name answer is empty:
  1. Argus computes the **change map**: how far each pixel inside the vessel has moved in colour (ΔE, CIE76 in Lab)
     from the vessel's **start reference**, the per-pixel median of its first 3 kept crops. The rim is left out (the
     vessel's region eroded by 6% of its equivalent radius). Light that changed everywhere is taken out first: the
     median Lab shift of the crop's pixels outside the vessel is subtracted, when there are at least 500 of them.
  2. A pixel has changed when it passes hysteresis thresholds set from the reference's own noise (noise = 1.4826 ×
     the median ΔE of the 3 reference crops from their median): a core of at least 25 connected px above max(8 × noise,
     6 ΔE), grown into connected pixels above max(4 × noise, 3 ΔE). Connected regions smaller than max(0.2% of the vessel's area, 25
     px) are dropped; the 16 largest are kept.
  3. With at least one region, Argus asks SAM again on the vessel's crop with one box per region (its bounding box
     padded by 15%, clipped to the crop, `x2`/`y2` inclusive) and, if the probe shows the API accepts it, a positive
     point at the region's strongest change. One request, $0.0025, logged like every call. A SAM mask covering 85% or
     more of the vessel is dropped when the change regions cover less than 50% of it (SAM outlined the dish).
  4. If SAM still returns nothing, the change regions themselves are the outline (**code outline**), measured in mm²
     like any mask.
  5. With no region, nothing is asked: the empty answer stands, a gap after a first sighting (D-90) or a zero before.

  The reference resets when the vessel's region changes (a camera move); until 3 new crops are in, nothing is
  pointed. Pictures are not aligned to each other: the scanner frames already are, and live runs track the card.

- **D-93 Every outline says who drew it, and everything downstream says so too.** A detection's `backend` is
  `sam-3.1/image` or `sam-3.1/video` (by name, as today), `sam-3.1/pointed` (SAM, prompted by boxes), or `change-map`
  (code). Each SAM answer row records `via`: `name`, `pointed` or `code` (the final answer for that frame, vessel
  and concept; `pointed` and `code` imply the by-name answer was empty). Coverage counts pictures found by each.
  Results' column is renamed "Found" and adds a line like "55 by name · 30 pointed · 12 by code" when any picture was
  found by pointing or code. The Run page draws code outlines dashed, titled "Outlined by code (change since the
  start), not SAM". When a vessel's latest reading comes from a code outline, its measurement ref label adds
  ", outlined by code from the change since the start, not by SAM", and rule 3 of the scientific rules tells the
  model to say so when citing it.

## Components

- **Probe first** (`worker/probes/sam_pointed.py`): on one swarming crop where the by-name answer was empty, send a
  box (and, separately, a box with a point for the same object). Record in KB 04 which forms the API accepts and what
  comes back. If boxes are refused, step 3 of D-92 is dropped and code outlines carry the fix.
- **`argus/segment/change.py`** (code only, no model): `ChangeReference` (reference Lab, noise, vessel mask, the
  region it was taken with), built from 3 crops; `change_regions(reference, crop) -> list[ChangeRegion]` (bounding
  box, peak point, mask, in crop pixels).
- **`argus/segment/sam.py`**: `segment()` takes `prompts` (box and optional points per object); with prompts, the
  text part is the `<0f>` token string instead of the concept, image mode only. `MaskPatch` gains `source` (kept by
  `shifted`).
- **`argus/pipeline/analyzer.py`**: the `Segmenter` protocol gains `pointed(image, concept, prompts)`;
  `segment_with_retries` passes prompts through; `RunContext` keeps the start references. A shared step,
  "point again", runs D-92 for one vessel and concept, used by the live path (`analyze_frame`, after the by-name
  call) and the still-picture import path (`_segment_stills`). `_store_detections` takes each patch's source.
- **Storage:** migration 011 adds `sam_answers.via` (`name` by default, checked against the three values);
  `add_sam_answers` takes the via per key.
- **Recipes:** `Concept.appears: bool = False`; `recipes/colony-spread.toml` version 2 with `appears = true`.
- **Coverage, API, web:** `Coverage` gains `by_name`, `pointed`, `by_code`; the detections endpoint returns
  `backend`; `coverageLines` words the split; `RunFrame` dashes code outlines; FitTable's header reads "Found".
- **Claims:** `build_refs` labels a code-outlined latest reading (D-93); `prompts/system/scientific-rules.md` rule 3
  gains one sentence; the fallback text says "outlined by code".
- **Docs:** D-92 and D-93 in KB 15; "Change map" and "Code outline" in KB 18; box prompts in KB 04; `appears` in KB
  06; the outcome in KB 17.

## What is unaffected, on purpose

Recipes without an `appears` concept (seed germination, colour reaction, foam, general) never compute a change map
or point SAM. Video-mode imports (per-vessel clips) keep by-name only. Old runs and old bundles read `via = name` and
show solid outlines. Recipes Argus drafts from words don't get `appears` yet.

## Testing

- Change map on made-up crops: a faint disc growing on noisy agar is found, with its box around it; pure noise gives
  no region; the whole crop brightening (outside included) gives no region; a speck below the size floor is dropped;
  the rim is left out.
- Prompt tokens: the exact string for two boxes on a known crop size, `x2`/`y2` inclusive, padded and clipped.
- Point again, with a fake segmenter: an empty by-name answer plus a change leads to a pointed call; an empty pointed
  answer leads to a code outline with backend `change-map` and via `code`; a dish-sized SAM mask is dropped; no change
  means no call; a recipe without `appears` never points; the reference resets after the vessel's region moves.
- Storage: migration 011, the via values, user_version 11. Coverage counts by via. The detections endpoint returns
  backend. The ref label and the rule sentence. Web: `coverageLines` with the split, dashed code outlines.
- **On real data:** re-import the swarming run as a new run (the old one stays untouched for comparison), about
  $3.50 (870 by-name calls plus at most one pointed call per missed picture). Compare pictures found per dish with
  the old run, and look at about ten outlines by eye, code outlines first.

## Not in this fix

Rewinding from the last picture (fix 3), aligning pictures after a camera move, video-mode imports, `appears` in
drafted recipes, negative points (unless the probe shows SAM outlining the dish), dashed code outlines in the
exported videos (only if time is left), and a check that a code outline persists across pictures.
