"use client";

import { playhead } from "@/lib/playhead";
import styles from "./EvidenceChip.module.css";

type Props = {
  text: string; // what the chip reads: a measured value, or an event and its time
  title: string; // what the number is, in full
  t: number | null;
  vesselId: string | null;
};

// One number or event a note rests on. Clicking it shows that moment and selects its vessel.
export function EvidenceChip({ text, title, t, vesselId }: Props) {
  return (
    <button
      type="button"
      className={`${styles.chip} num`}
      title={title}
      aria-label={`${title}: ${text}. Show this moment`}
      onClick={() => {
        if (t !== null) playhead.setT(t);
        if (vesselId !== null) playhead.selectVessel(vesselId);
      }}
    >
      {text}
    </button>
  );
}
