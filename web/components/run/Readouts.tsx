"use client";

import { useMemo } from "react";
import { playhead, usePlayhead } from "@/lib/playhead";
import { byVessel } from "@/lib/run-data";
import type { RunSnapshot } from "@/lib/run-source";
import { linearScale } from "@/lib/scale";
import type { MeasurementRow, Vessel } from "@/lib/types";
import { useReadings } from "./RunFrame";
import styles from "./Readouts.module.css";

type Props = { snapshot: RunSnapshot; mainMetric: string };

function condition(v: Vessel): string {
  if (!v.condition) return v.role === "control" ? "Control" : "Treatment";
  const { factor, value, unit } = v.condition;
  return `${factor} ${value}${unit ? ` ${unit}` : ""}`;
}

/** The main measurement's course up to t, as a tiny line (the shape, not a number). */
function Spark({ rows, t }: { rows: MeasurementRow[]; t: number }) {
  const seen = rows.filter((r) => r.t <= t + 1e-6);
  if (seen.length < 2) return <svg className={styles.spark} viewBox="0 0 100 24" aria-hidden="true" />;
  const values = seen.map((r) => r.value);
  const low = Math.min(...values);
  const high = Math.max(...values);
  const x = linearScale([seen[0].t, seen[seen.length - 1].t], [1, 99]);
  const y = linearScale([low, high === low ? low + 1 : high], [22, 2]);
  const points = seen.map((r) => `${x(r.t).toFixed(1)},${y(r.value).toFixed(1)}`).join(" ");
  return (
    <svg className={styles.spark} viewBox="0 0 100 24" preserveAspectRatio="none" aria-hidden="true">
      <polyline points={points} />
    </svg>
  );
}

export function Readouts({ snapshot, mainMetric }: Props) {
  const t = usePlayhead((p) => p.t);
  const selected = usePlayhead((p) => p.selectedVesselId);
  const reading = useReadings(snapshot, mainMetric, t);
  const series = useMemo(
    () => byVessel(snapshot.measurements, new Set([mainMetric, `${mainMetric}_l`])),
    [snapshot.measurements, mainMetric],
  );

  return (
    <div className={styles.strip} role="group" aria-label="Readouts at the playhead">
      {snapshot.view.vessels.map((v) => {
        const value = reading(v);
        const on = v.id === selected;
        return (
          <button
            key={v.id}
            type="button"
            className={`${styles.cell} ${on ? styles.selected : ""}`}
            aria-pressed={on}
            onClick={() => playhead.selectVessel(on ? null : v.id)}
          >
            <span className={styles.key}>
              <span>Vessel {v.label}</span>
              <span className={styles.condition}>{condition(v)}</span>
            </span>
            <span className={`${styles.value} num`}>{value ? value.display : "—"}</span>
            <Spark rows={series.get(v.id) ?? []} t={t} />
          </button>
        );
      })}
    </div>
  );
}
