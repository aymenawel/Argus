import type { RunMode } from "@/lib/types";
import styles from "./Badge.module.css";

const COPY: Record<RunMode, { label: string; title: string }> = {
  live: { label: "LIVE", title: "Argus is watching this run now" },
  replay: { label: "REPLAY", title: "A recorded run played back" },
  imported: { label: "IMPORTED", title: "Measured from an imported video" },
};

// Where the pictures and numbers come from. Only LIVE moves; the word carries the meaning, not the motion.
export function Badge({ source }: { source: RunMode }) {
  const { label, title } = COPY[source];
  return (
    <span className={`${styles.badge} ${source === "live" ? styles.live : ""}`} title={title}>
      <span className={styles.dot} aria-hidden="true" />
      {label}
    </span>
  );
}
