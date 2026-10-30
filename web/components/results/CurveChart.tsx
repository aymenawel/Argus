"use client";

import { useEffect, useRef, useState } from "react";
import { linearScale, niceTicks } from "@/lib/chart";
import type { FitsView } from "@/lib/types";
import styles from "./CurveChart.module.css";

type Props = { fits: FitsView; checkpointS?: number | null };

// Up to three treatment conditions stay apart by dash pattern; the control is always grey and solid.
const DASHES = [undefined, "7 4", "2 4"];

const PAD = { left: 44, right: 16, top: 26, bottom: 34 };

// Each vessel's readings as dots and its fitted curve as a line, coloured by condition (controls grey, treatments
// teal, told apart by dash); the plan's checkpoint dashed; each half-way point marked. Plain SVG drawn from the worker's numbers (nothing computed here
// but positions).
export function CurveChart({ fits, checkpointS }: Props) {
  // Drawn at the figure's own width, so the labels keep their size from a phone to a wide screen.
  const figure = useRef<HTMLElement>(null);
  const [W, setW] = useState(720);
  useEffect(() => {
    const el = figure.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setW(Math.max(280, Math.round(entry.contentRect.width))));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  const H = W < 560 ? 240 : 320;
  const all = fits.vessels.flatMap((v) => [...v.readings, ...(v.fit?.samples ?? [])]);
  if (all.length === 0) return <p className={styles.empty}>No readings of {fits.metric} yet.</p>;
  const tMax = Math.max(...all.map(([t]) => t), checkpointS ?? 0) / 3600;
  const yMin = Math.min(0, ...all.map(([, y]) => y));
  const yMax = Math.max(...all.map(([, y]) => y));
  const xTicks = niceTicks(0, tMax, Math.max(3, Math.floor(W / 90)));
  const yTicks = niceTicks(yMin, yMax > yMin ? yMax : yMin + 1, 5); // a flat series still gets an axis
  const x = linearScale([0, xTicks.at(-1)!], [PAD.left, W - PAD.right]);
  const y = linearScale([yTicks[0], yTicks.at(-1)!], [H - PAD.bottom, PAD.top]);
  const path = (points: [number, number][]) =>
    points.map(([t, v], i) => `${i ? "L" : "M"}${x(t / 3600).toFixed(1)},${y(v).toFixed(1)}`).join("");
  // One group per condition, controls first.
  const groupOf = (v: FitsView["vessels"][number]) => `${v.role}:${v.condition?.value ?? ""}`;
  const groups = new Map<string, { label: string; control: boolean; dash?: string }>();
  for (const v of [...fits.vessels].sort((a, b) => Number(b.role === "control") - Number(a.role === "control"))) {
    const key = groupOf(v);
    if (groups.has(key)) continue;
    const control = v.role === "control";
    const treatments = [...groups.values()].filter((g) => !g.control).length;
    const name = control ? "Control" : "Treatment";
    groups.set(key, {
      label: v.condition ? `${name}: ${v.condition.value}` : name,
      control,
      dash: control ? undefined : DASHES[treatments % DASHES.length],
    });
  }

  return (
    <figure ref={figure} className={styles.figure}>
      <svg
        className={styles.chart}
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`${fits.metric} over time for ${fits.vessels.length} vessels, with each vessel's fitted ${fits.curve} curve`}
      >
        {yTicks.map((tick) => (
          <g key={`y${tick}`}>
            <line className={styles.grid} x1={PAD.left} x2={W - PAD.right} y1={y(tick)} y2={y(tick)} />
            <text className={styles.tick} x={PAD.left - 6} y={y(tick)} textAnchor="end" dominantBaseline="middle">
              {tick}
            </text>
          </g>
        ))}
        {xTicks.map((tick) => (
          <text key={`x${tick}`} className={styles.tick} x={x(tick)} y={H - PAD.bottom + 16} textAnchor="middle">
            {tick}
          </text>
        ))}
        <text className={styles.axis} x={W - PAD.right} y={H - 4} textAnchor="end">
          hours
        </text>
        <text className={styles.axis} x={PAD.left - 6} y={PAD.top - 14} textAnchor="end">
          {fits.unit}
        </text>
        {checkpointS != null && checkpointS > 0 && (
          <g>
            <line
              className={styles.checkpoint}
              x1={x(checkpointS / 3600)}
              x2={x(checkpointS / 3600)}
              y1={PAD.top}
              y2={H - PAD.bottom}
            />
            <text className={styles.tick} x={x(checkpointS / 3600) + 4} y={PAD.top + 10}>
              checkpoint
            </text>
          </g>
        )}
        {fits.vessels.map((v) => (
          <g key={v.vessel_id} className={v.role === "control" ? styles.control : styles.treatment}>
            {v.readings.map(([t, value], i) => (
              <circle key={i} className={styles.dot} cx={x(t / 3600)} cy={y(value)} r={2} />
            ))}
            {v.fit?.ok && v.fit.samples.length > 0 && (
              <path className={styles.curve} d={path(v.fit.samples)} strokeDasharray={groups.get(groupOf(v))?.dash} />
            )}
            {v.fit?.ok && v.fit.half_time_h && v.fit.plateau && (
              <circle className={styles.half} cx={x(v.fit.half_time_h[0])} cy={y(v.fit.plateau[0] / 2)} r={4}>
                <title>
                  {v.label}: half-way at {v.fit.half_time_h[0].toFixed(1)} h
                </title>
              </circle>
            )}
          </g>
        ))}
      </svg>
      <figcaption className={styles.legend}>
        {[...groups.entries()].map(([key, g]) => (
          <span key={key} className={`${styles.key} ${g.control ? styles.control : styles.treatment}`}>
            <svg className={styles.swatch} viewBox="0 0 18 4" aria-hidden="true">
              <line x1="0" x2="18" y1="2" y2="2" strokeDasharray={g.dash} />
            </svg>
            {g.label}
          </span>
        ))}
        <span className={styles.key}>
          <span className={styles.ring} aria-hidden="true" />
          half-way point
        </span>
      </figcaption>
    </figure>
  );
}
