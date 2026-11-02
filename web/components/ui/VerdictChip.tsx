import type { VerdictLevel } from "@/lib/types";
import styles from "./VerdictChip.module.css";
import { VERDICT_WORDS } from "@/lib/plain";

const WORDS = VERDICT_WORDS;

const TONE: Record<VerdictLevel, string> = {
  SUPPORTED: styles.supported,
  NOT_SUPPORTED: styles.notSupported,
  INCONCLUSIVE: styles.inconclusive,
  TOO_EARLY: styles.tooEarly,
};

// A provisional verdict (the run is still going, or no one has reviewed it) is drawn dashed and says so in words.
// A verdict on published data, judged after it existed, says "looking back" (D-71, D-95).
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
      {retrospective && " · looking back"}
      {provisional && " · not final"}
    </span>
  );
}
