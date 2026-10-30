import type { Provenance, RunMode } from "@/lib/types";
import styles from "./Badge.module.css";

const COPY: Record<RunMode, { label: string; title: string }> = {
  live: { label: "LIVE", title: "Argus is watching this run now" },
  replay: { label: "REPLAY", title: "A recorded run played back" },
  imported: { label: "IMPORTED", title: "Measured from an imported video" },
};

// Where the pictures and numbers come from. Only LIVE moves; the word carries the meaning, not the motion.
// Published data says so, and whether it is judged after the fact (D-71).
export function Badge({ source, provenance }: { source: RunMode; provenance?: Provenance | null }) {
  const { label, title } = provenance
    ? {
        label: provenance.retrospective ? "PUBLISHED · RETROSPECTIVE" : "PUBLISHED",
        title: `Published data from ${provenance.credit}, measured by Argus${
          provenance.retrospective ? " after the data existed" : ""
        }`,
      }
    : COPY[source];
  return (
    <span className={`${styles.badge} ${source === "live" ? styles.live : ""}`} title={title}>
      <span className={styles.dot} aria-hidden="true" />
      {label}
    </span>
  );
}
