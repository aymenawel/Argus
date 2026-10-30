# 18 · Glossary

Use these words consistently in code, UI and docs.

| Term | Meaning |
| --- | --- |
| **Experiment** | One configured study with a locked plan, a recipe and one or more runs |
| **Run** | One period of watching (one Ax round when optimizing) |
| **Vessel** | One jar, well, pot, dish or region being measured; has a role: control, treatment or replicate |
| **Replicate** | An independent vessel under the same condition. Repeated frames of one vessel are **not** replicates |
| **Recipe** | Config for an experiment type: SAM concepts, measurements, curve, events, watcher preset, method card |
| **Method card** | Short prompt file per recipe, loaded only for that recipe |
| **Plan / pre-registration** | Hypothesis, prediction and success threshold, locked with a timestamp at start |
| **ROI** | Region of interest: the vessel's area the watcher looks at |
| **Keyframe** | The last frame that was analyzed; the watcher compares new frames to it |
| **Trigger** | Watcher decision that something changed enough to call SAM |
| **Check-in** | Scheduled forced analysis even without a trigger |
| **Track** | Argus's object format from any vision backend: id, label, mask, box, confidence |
| **Measurement** | A number computed in code from masks, with unit, ± and method version |
| **Noise floor** | Spread of readings on things that shouldn't change; effects < ~3× it are "not real yet" |
| **Event** | Something detected (onset, overflow, intervention), with start/end time and evidence frames |
| **Note** | Structured AI or researcher entry on the timeline (AI notes: event, checkpoint, insight) |
| **Claim checker** | Code that rejects any AI note whose numbers don't match stored measurements |
| **Verdict** | SUPPORTED, NOT_SUPPORTED, INCONCLUSIVE or TOO_EARLY (provisional while a run is live) |
| **Rival explanation** | Something other than the treatment that could explain a result (lighting, temperature, position…) |
| **Tier** | `routine` (Muse Spark 1.3) or `deep` (Muse Wonder 1.0) |
| **Argus Card** | Printed card with ArUco markers and neutral/color patches for scale and color correction |
| **Intervention** | Anything done to the experiment by a person or by Argus (logged automatically for plug actions) |
| **Highlights reel** | Short video of detected events; the full timelapse is separate |
| **Own recipe** | A recipe Argus drafted from the researcher's words for one experiment (id `own`), editable until the plan locks, then frozen with it (D-73) |
| **Toolbox** | The measurements Argus can make (area, height, skeleton length, component count, touching count, Lab mean, ΔE); a drafted recipe may use only these |
| **Touching count** | How many objects of one concept touch another at least a set length long (seeds with a root ≥ 2 mm) |
| **Grown count** | How many objects grew at least a set length longer than when Argus first saw them (seeds whose sprout shows in their outline, D-75) |
| **Published data** | Frames someone else recorded and published, re-analysed by Argus with their provenance (dataset, DOI, licence, credit) shown on every view |
| **Manifest** | The file naming a published image sequence: its frames, interval, tiles, labels and provenance |
| **Virtual plate** | Published per-dish images tiled by Argus into one frame per time point, one vessel per tile (D-72) |
| **Dish ruler** | Millimetres per pixel from the rims of dishes of a known diameter, when no card is in view; ± at least about 5 % |
| **Retrospective** | A verdict on data recorded before the plan existed; judged against a plan locked before Argus measured it, and labelled so (D-71) |
| **Reference values** | A dataset's own values (its human labels), kept apart from Argus's measurements |
| **Agreement** | Argus's readings against the reference values at the same times: mean difference, share of exact matches, time to half the final value |
