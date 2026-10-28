import styles from "./Mark.module.css";

export type MarkState = "resting" | "watching" | "locked";

const LABELS: Record<MarkState, string> = {
  resting: "Argus",
  watching: "Argus, watching",
  locked: "Argus, measurement locked",
};

const EYE = "M5 32 C 17 11, 47 11, 59 32 C 47 53, 17 53, 5 32 Z";

// The brand mark (brand/argus-mark.svg) drawn in theme colours: ink follows currentColor, the ring is the accent.
export function Mark({ state = "resting", size = 34 }: { state?: MarkState; size?: number }) {
  return (
    <svg className={styles.mark} viewBox="0 0 64 64" width={size} height={size} role="img" aria-label={LABELS[state]}>
      <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth={3.4}>
        <path d={EYE} stroke="currentColor" />
        {state === "resting" && (
          <circle
            cx="32"
            cy="32"
            r="11"
            stroke="var(--accent)"
            strokeDasharray="53.12 16"
            transform="rotate(-3.33 32 32)"
          />
        )}
        {state === "watching" && (
          <g className={styles.orbit}>
            <circle cx="32" cy="32" r="11" stroke="var(--accent)" strokeDasharray="53.12 16" />
            <circle cx="39.78" cy="24.22" r="2.7" fill="var(--accent)" stroke="none" />
          </g>
        )}
        {state === "locked" && (
          <circle className={styles.close} cx="32" cy="32" r="11" stroke="var(--accent)" strokeDasharray="53.12 16" />
        )}
      </g>
      <circle cx="32" cy="32" r="3.8" fill="currentColor" />
      {state === "resting" && <circle cx="39.78" cy="24.22" r="2.7" fill="var(--accent)" />}
    </svg>
  );
}
