# A miss is a gap, not a zero — design (fix 1)

Date: Nov 1, 2026 · Status: design approved by Aymen in chat (Nov 1); this written spec awaits his review · Builds on
branch `phase-4` · Decisions: D-90, D-91 · Source: fix 1 of `reports/Detecting anything in lab images.md`

## Why

When SAM is asked about a dish and finds nothing, Argus records a reading of zero. Before the object first appears,
that is right: nothing has grown yet. After it has been seen, it is usually wrong: the colony is still there, SAM just
missed it. In the swarming run, SAM found the fliA 0.1 swarm at 11.2 h and then missed it in most later scans, so the
dish read zero for most of the day, and the verdict and notes compared those zeros with the other dishes as if they
were measurements.

**Success:** a dish SAM loses after first seeing it gets no reading for those pictures, the timeline shows a "missed"
stretch, the notes and verdict never present the last reading before a miss as current, and Results shows per dish
how often SAM found the object. Foam, which can really collapse to nothing, keeps its zeros.

## Decisions

- **D-90 An empty SAM answer after a first sighting is a miss: no reading, and a `missed` event.** Per vessel and
  concept, once SAM has returned at least one object for it on a kept frame (not occluded), a later empty answer is
  dropped before measuring: no geometry reading, the newest outline in `last_masks` stays as it was. One `missed`
  event (source `pipeline`, the vessel's id, detail `concept`, `last_seen_t`, `message`) opens at the first empty
  answer of a stretch and closes with `close_event` when the object is found again; still open at the run's end means
  never found again. Empty answers before the first sighting still read zero. A concept marked `can_vanish = true` in
  its recipe (foam) keeps today's behaviour: an empty answer reads zero, no event. Every answer SAM gives is also kept
  as evidence in a new `sam_answers` table (frame, vessel, concept, number of objects found), so coverage is counted
  from records, not guessed.
- **D-91 A reading after which SAM lost the object is not current.** When building refs at time t, a vessel's latest
  reading of a metric counts as current unless a `missed` event for a concept that metric reads (its `from` or
  `touching`) started after that reading. Such a reading keeps its `m:` id (so notes may still cite it) but its kind
  becomes `last_reading` and its label says it is the last reading before SAM lost the object. It is left out of the
  controls' mean, a treatment in that state gets no `diff:` ref, and the verdict counts only current readings as
  measured, so the ceiling's existing replicate checks treat that dish as not measured now. Quiet periods with no
  segmentation (a live run's smart trigger) never make a reading stale: only a miss does.

## Components

| Unit | Change |
|---|---|
| `worker/argus/domain.py` | `EventKind.MISSED = "missed"` |
| `storage/migrations/010_sam_answers.sql`, `repos.py` | Table `sam_answers(run_id, frame_id, vessel_id, concept, found ≥ 0)`, one row per frame, vessel and concept, with the evidence triggers (no update, delete or replace); `add_sam_answers`, `sam_answers_for_run` |
| `recipes/model.py`, `recipes/foam-height.toml` | `Concept.can_vanish: bool = False`; foam sets it, recipe version 2. `Recipe.concepts_read(metric) -> set[str]` maps a stored metric (lab_mean's `_l/_a/_b` too) to the concepts it reads |
| `pipeline/analyzer.py` | In `analyze_frame`, after the occlusion filter: record answers, apply D-90 with new `RunContext` fields `sighted` (vessel → concepts seen), `missing` ((vessel, concept) → open event id) and `last_found_t`. `AnalysisOutcome.segmented` stays true when SAM answered at all |
| `claims/refs.py` | D-91 in `build_refs`; `missed` joins `NOTABLE`, and its event ref is labelled with the concept and vessel instead of "Time of the missed event". Not a note trigger, so a flickering dish doesn't buy a note per miss |
| `pipeline/verdict.py` | Controls and `measured` count only refs of kind `measurement` |
| `analyze/fits.py` (`fits_view`) | Each vessel gains `coverage` for the concept the shown metric is measured from: concept, asked, found, first found at, missed after that; `null` when the run has no recorded answers (older runs, bundles already published) |
| `web/lib/types.ts`, `FitTable.tsx` | `RunEventKind` adds `"missed"`; `coverage?` is optional. Results' fit table gains a "Found by SAM" column, e.g. "14 of 145 pictures" and "missed 131 after first seen at 11.2 h" |
| `web/components/run/Timeline.tsx`, `NoteCard.tsx` | Missed stretches drawn on the vessel's lane, an open one to the end of the run; event label "Lost by SAM" |
| `prompts/` | Colony-spread method card: a lost colony is a gap, not a zero. System rules: a reading labelled as the last before SAM lost the object is not a reading of now; say when it was taken |
| Docs | D-90, D-91 in KB 15; "miss" in the glossary (KB 18) |

## What is unaffected, on purpose

- **Colour** is still measured on the newest outline, as it already is between segmentations, so a missed liquid
  keeps giving colour readings from where it was last outlined. The dye run is not changed by this fix beyond that.
- **Fitted quantities** (half-way time, rate) still fit every reading there is; fewer false zeros make those fits
  better, not different in kind.
- **Occluded vessels** (a hand in front) are already a gap; their answers aren't recorded and they neither open nor
  close a miss.

## Testing

Test-first, in `worker/tests` and `web/tests`:
- seen, then two empty answers: no reading on either, one `missed` event, closed at the frame where it is found again;
- empty before the first sighting: a zero reading, no event;
- `can_vanish` concept: a zero reading after a sighting, no event;
- occluded vessel: no answer row, its open miss neither closed nor duplicated;
- `sam_answers` rows hold the object counts; the table refuses update and delete;
- refs: a control lost after its last reading is left out of the controls' mean, a lost treatment has no `diff:`,
  its `m:` ref has kind `last_reading`; a colour metric still read after a miss stays current;
- verdict: a lost control is not counted as measured;
- `fits_view` coverage numbers on a small run, `null` without answers; FitTable shows the column and copes without it;
- end to end: re-import the swarming scans (about $2.20 of SAM calls) and check fliA 0.1 reads gaps, not zeros, after
  11.2 h, and that the verdict counts it as not measured at 24 h. The run stays local (D-89).

## Not in this fix

The Muse Spark "can you see it: yes / no / unsure" cross-check and a claim-checker rule against claims of absence
(fix 1 part B); breaking a chart's line across a missed stretch; re-exporting the published replay bundles (task 9).
