// A recipe in the researcher's words, and the edits the "What will you do?" dialog makes to a drafted one (D-73).
// The worker validates every recipe again when it is saved; these only keep an edit consistent with itself.
import type { MeasurementSpec, RecipeSpec, Tool } from "./types";

const trim = (n: number) => String(Number(n.toFixed(1)));

/** 1800 → "30 min", 0.5 → "0.5 s", 7200 → "2 h". */
export function stepInWords(seconds: number): string {
  if (seconds < 60) return `${trim(seconds)} s`;
  if (seconds < 3600) return `${trim(seconds / 60)} min`;
  return `${trim(seconds / 3600)} h`;
}

/** touching_count reads as "seeds with a root", grown_count as "seeds that grew 2 mm"; the rest by their names. */
export function measurementInWords(m: MeasurementSpec): string {
  if (m.method === "touching_count" && m.touching) return `${m.from}s with a ${m.touching}`;
  if (m.method === "grown_count" && m.min_length_mm != null) return `${m.from}s that grew ${m.min_length_mm} mm`;
  return m.id.replaceAll("_", " ");
}

export function recipeInWords(recipe: RecipeSpec): { lookFor: string; measure: string; every: string } {
  return {
    lookFor: recipe.concepts.map((c) => c.name).join(", "),
    measure: recipe.measurements.map((m) => `${measurementInWords(m)} (${m.unit})`).join(", "),
    every: `every ${stepInWords(recipe.analysis_step_s)}`,
  };
}

/** A concept's new name, carried to every measurement that reads from it or counts what touches it. */
export function renameConcept(recipe: RecipeSpec, from: string, to: string): RecipeSpec {
  const swap = (name: string | null | undefined) => (name === from ? to : name);
  return {
    ...recipe,
    concepts: recipe.concepts.map((c) => (c.name === from ? { name: to } : c)),
    measurements: recipe.measurements.map((m) => ({
      ...m,
      from: swap(m.from) ?? m.from,
      ...(m.touching != null ? { touching: swap(m.touching) } : {}),
    })),
  };
}

/** The measurement with another toolbox method: family and unit come with it; only touching_count touches, and
 * only it and grown_count take a minimum length. */
export function withMethod(m: MeasurementSpec, tool: Tool, recipe: RecipeSpec): MeasurementSpec {
  const touches = tool.method === "touching_count";
  const lengthens = touches || tool.method === "grown_count";
  const other = recipe.concepts.find((c) => c.name !== m.from)?.name ?? m.from;
  return {
    ...m,
    method: tool.method,
    family: tool.family,
    unit: tool.unit,
    touching: touches ? (m.touching ?? other) : null,
    min_length_mm: lengthens ? (m.min_length_mm ?? 2) : null,
  };
}

const SUFFIX: Record<string, string> = {
  skeleton_length: "length",
  component_count: "count",
  touching_count: "touching",
  grown_count: "grown",
  lab_mean: "colour",
  delta_e: "colour_change",
};

/** A new measurement of `concept` with a name no other measurement has. */
export function addMeasurement(recipe: RecipeSpec, tool: Tool, concept: string): RecipeSpec {
  const base = `${concept.trim().replaceAll(" ", "_")}_${SUFFIX[tool.method] ?? tool.method}`;
  const taken = new Set(recipe.measurements.map((m) => m.id));
  let id = base;
  for (let n = 2; taken.has(id); n++) id = `${base}_${n}`;
  const blank: MeasurementSpec = { id, family: tool.family, method: tool.method, from: concept, unit: tool.unit };
  return { ...recipe, measurements: [...recipe.measurements, withMethod(blank, tool, recipe)] };
}
