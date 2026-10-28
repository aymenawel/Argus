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
