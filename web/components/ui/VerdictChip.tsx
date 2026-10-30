import type { VerdictLevel } from "@/lib/types";
import styles from "./VerdictChip.module.css";

const WORDS: Record<VerdictLevel, string> = {
  SUPPORTED: "Supported",
  NOT_SUPPORTED: "Not supported",
  INCONCLUSIVE: "Inconclusive",
  TOO_EARLY: "Too early",
};

const TONE: Record<VerdictLevel, string> = {
  SUPPORTED: styles.supported,
  NOT_SUPPORTED: styles.notSupported,
  INCONCLUSIVE: styles.inconclusive,
  TOO_EARLY: styles.tooEarly,
};

// A provisional verdict (the run is still going, or no one has reviewed it) is drawn dashed and says so in words.
// A verdict on published data, judged after it existed, says "retrospective" (D-71).
export function VerdictChip({
  level,
  provisional = false,
  retrospective = false,
}: {
  level: VerdictLevel;
  provisional?: boolean;
  retrospective?: boolean;
}) {
  return (
    <span className={`${styles.chip} ${TONE[level]} ${provisional ? styles.provisional : ""}`}>
      {WORDS[level]}
      {retrospective && " · retrospective"}
      {provisional && " · provisional"}
    </span>
  );
}
