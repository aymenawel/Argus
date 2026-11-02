// The words a reader with no lab training sees (D-95): the code keeps its names, the page uses these. Mirrors the
// worker's argus/plain.py, which words the notes, verdicts and videos the same way.

const METRIC_WORDS: Record<string, string> = {
  delta_e: "colour change",
  germinated_count: "sprouted seeds",
  sprouted: "sprouted seeds",
  skeleton_length: "length",
  component_count: "count",
  lab_mean: "colour",
};

// ΔE is the standard colour-difference number: about 1 is the smallest change an eye can see.
const UNIT_WORDS: Record<string, string> = { dE00: "ΔE", mm2: "mm²", Lab: "L*a*b*" };

/** A measurement's id as a person would say it: "delta_e" → "colour change", "root_length" → "root length". */
export function metricWords(metric: string): string {
  return METRIC_WORDS[metric] ?? metric.replace(/_/g, " ");
}

export function unitLabel(unit: string): string {
  if (unit.endsWith("/h")) return `${unitLabel(unit.slice(0, -2))} per hour`;
  return UNIT_WORDS[unit] ?? unit;
}

/** A vessel's role on the page: the treatment is the "test" sample, beside its control. */
export function roleWord(role: "control" | "treatment"): string {
  return role === "treatment" ? "test" : "control";
}

/** One line under a chart or reading that says what ΔE means, for the units that need it. */
export function unitKey(unit: string): string | null {
  return unit.startsWith("dE00")
    ? "ΔE: how much the colour changed. About 1 is the smallest change you can see."
    : null;
}

/** The first letter capitalised, for a label that starts a line: "colour change" → "Colour change". */
export function sentence(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

const CURVE_WORDS: Record<string, string> = {
  logistic: "S-shaped",
  gompertz: "S-shaped",
  exponential: "ever-faster",
  first_order: "fast, then slowing",
  linear: "straight-line",
};

/** A fitted curve's shape as people describe it: a logistic curve is "S-shaped". */
export function curveWords(curve: string): string {
  return CURVE_WORDS[curve] ?? curve;
}

/** A verdict as the page names it: "Inconclusive" reads as "Unclear" (D-95); the stored level keeps its name. */
export const VERDICT_WORDS = {
  SUPPORTED: "Supported",
  NOT_SUPPORTED: "Not supported",
  INCONCLUSIVE: "Unclear",
  TOO_EARLY: "Too early",
} as const;

/** A note field without its own name in front ("Observation: the glass…" reads "The glass…"). The worker drops it
 * when it saves a note; notes saved before that still carry it. */
export function withoutLabel(text: string, name: string): string {
  const label = new RegExp(`^\\s*${name.replace(/_/g, "[ _]")}\\s*:\\s*`, "i").exec(text);
  if (!label) return text;
  const rest = text.slice(label[0].length);
  return rest.charAt(0).toUpperCase() + rest.slice(1);
}

// What happened, as the worker's argus/plain.py EVENT_WORDS says it, for event chips saved under the code's names.
const EVENT_WORDS: Record<string, string> = {
  intervention: "a hand or object was at the samples",
  rule: "a set threshold was crossed",
  camera_moved: "the camera moved",
  segment_failed: "SAM couldn't outline a picture",
  interrupted: "the run was interrupted",
  spend: "the spending limit was reached",
  quality: "the picture had a problem",
};

/** An evidence chip's hover text: an older "Time of the intervention event" reads "Time a hand or object was…". */
export function chipTitle(label: string): string {
  const old = /^Time of the (\w+) event$/.exec(label);
  return old && EVENT_WORDS[old[1]] ? `Time ${EVENT_WORDS[old[1]]}` : label;
}
