"use client";

import type { StepId } from "@/lib/setup";
import styles from "./Stepper.module.css";

export const STEP_NAMES: Record<StepId, string> = {
  describe: "Describe",
  source: "Source",
  vessels: "Vessels",
  roles: "Roles",
  check: "Check",
  plan: "Plan",
  start: "Lock and start",
};

type Props = {
  steps: StepId[];
  current: StepId;
  reachable: (step: StepId) => boolean; // every step before it can be left
  done: (step: StepId) => boolean;
  onPick: (step: StepId) => void;
};

// The wizard's steps across the top: done, current, or locked until the steps before it are.
export function Stepper({ steps, current, reachable, done, onPick }: Props) {
  return (
    <ol className={styles.stepper} aria-label="Setup steps">
      {steps.map((step, i) => {
        const open = reachable(step);
        const state = step === current ? styles.current : done(step) && open ? styles.done : open ? "" : styles.locked;
        return (
          <li key={step}>
            <button
              type="button"
              className={`${styles.step} ${state}`}
              disabled={!open}
              aria-current={step === current ? "step" : undefined}
              onClick={() => onPick(step)}
            >
              <span className={`${styles.index} num`}>{done(step) && open && step !== current ? "✓" : i + 1}</span>
              <span className={styles.name}>{STEP_NAMES[step]}</span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
