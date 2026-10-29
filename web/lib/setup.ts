import type { Condition, PlanDraft, Preview, Role, SetupSource } from "./types";

// The setup wizard's steps and what each needs before it can be left (spec §8). Plain TypeScript with type-only
// imports, so Node's test runner can load it as it is.

export type StepId = "describe" | "source" | "vessels" | "roles" | "check" | "plan" | "start";

export const STEPS: StepId[] = ["describe", "source", "vessels", "roles", "check", "plan", "start"];

/** A vessel while the wizard draws it: its role comes a step later. */
export type WizardVessel = { label: string; role: Role | null; condition: Condition | null; roi: [number, number][] };

export type WizardState = {
  source: SetupSource | null;
  vessels: WizardVessel[];
  preview: Preview | null; // the last check of the frame
  plan: PlanDraft | null;
};

const PLAN_NEEDS: [keyof PlanDraft, string][] = [
  ["metric", "Choose the metric the prediction is about."],
  ["direction", "Say whether the treatment should read higher or lower than the controls."],
  ["checkpoint_s", "Set the checkpoint: the run time from which a verdict may be given."],
];

/** Empty when the step can be left; otherwise what to do, in plain words. */
export function stepProblems(step: StepId, state: WizardState): string[] {
  switch (step) {
    case "source": {
      const source = state.source;
      const chosen =
        source !== null && (source.kind === "webcam" ? source.camera_index !== null : source.paths.length > 0);
      return chosen ? [] : ["Choose a camera or a video."];
    }
    case "vessels":
      return state.vessels.length > 0 ? [] : ["Draw at least one vessel."];
    case "roles": {
      const problems = state.vessels.filter((v) => v.role === null).map((v) => `Give vessel ${v.label} a role.`);
      if (problems.length === 0 && !state.vessels.some((v) => v.role === "control")) {
        problems.push("Mark at least one vessel as control.");
      }
      return problems;
    }
    case "check":
      if (state.preview === null) return ["Check the frame first."];
      return state.preview.calibration
        ? []
        : ["No Argus Card or ruler found: put the card in view at the vessels' height, or mark a ruler."];
    case "plan":
      if (state.plan === null) return ["Write the plan."];
      return PLAN_NEEDS.filter(([field]) => state.plan?.[field] == null).map(([, problem]) => problem);
    default:
      return [];
  }
}

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

/** The first letter not in use. */
export function nextLabel(vessels: { label: string }[]): string {
  const used = new Set(vessels.map((v) => v.label));
  return [...LETTERS].find((letter) => !used.has(letter)) ?? `V${vessels.length + 1}`;
}
