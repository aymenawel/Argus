"use client";

import { Mark } from "@/components/brand/Mark";
import { VerdictChip } from "@/components/ui/VerdictChip";
import { byVessel } from "@/lib/run-data";
import type { RunSnapshot } from "@/lib/run-source";
import { argusLine } from "@/lib/summary";
import styles from "./ArgusLine.module.css";

type Props = { snapshot: RunSnapshot; mainMetric: string; checkTime?: string | null };

const firstSentence = (text: string) => {
  const end = text.search(/\.\s/);
  return end === -1 ? text : text.slice(0, end + 1);
};

// What the run shows, first on the page (D-98): built by code from the stored readings and the verdict, so every
// number is a measurement. The mark watches while the run is live.
export function ArgusLine({ snapshot, mainMetric, checkTime = null }: Props) {
  const series = byVessel(snapshot.measurements, new Set([mainMetric, `${mainMetric}_l`]));
  const rows = snapshot.view.vessels.map((v) => series.get(v.id) ?? []);
  const unit = rows.find((r) => r.length > 0)?.[0].unit ?? "";
  const { verdict } = snapshot;
  const said = argusLine({
    samples: snapshot.view.vessels.map((v, i) => {
      const own = rows[i];
      const last = own.at(-1);
      return {
        label: v.label,
        role: v.role,
        condition: v.condition ? `${v.condition.value}${v.condition.unit ? ` ${v.condition.unit}` : ""}` : null,
        first: own[0]?.value ?? null,
        latest: last ? [last.value, last.uncertainty] : null,
      };
    }),
    metric: mainMetric,
    unit,
    verdict: verdict?.body.explanation
      ? { level: verdict.verdict, sentence: firstSentence(verdict.body.explanation) }
      : null,
    checkTime,
  });

  return (
    <section className={styles.line} aria-label="What Argus sees">
      <span className={styles.mark}>
        <Mark state={snapshot.view.running ? "watching" : "resting"} size={30} />
      </span>
      <div className={styles.words}>
        <p className={styles.lead}>{said.lead}</p>
        {said.detail && <p className={styles.detail}>{said.detail}</p>}
      </div>
      {said.level && verdict && (
        <VerdictChip
          level={said.level}
          provisional={verdict.provisional}
          retrospective={Boolean(verdict.body.retrospective)}
        />
      )}
    </section>
  );
}
