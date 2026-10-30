"use client";

import { useEffect, useRef, useState } from "react";
import { conditionGroups, groupKey, linearScale, type Marker, niceTicks } from "@/lib/chart";
import type { FitsView } from "@/lib/types";
import styles from "./CurveChart.module.css";

type Props = { fits: FitsView; checkpointS?: number | null };

const PAD = { left: 44, right: 16, top: 26, bottom: 34 };

// A reading's dot in its condition's shape, centred on (cx, cy).
function Dot({
  marker,
  cx,
  cy,
  r,
  className,
}: {
  marker: Marker;
  cx: number;
  cy: number;
  r: number;
  className?: string;
}) {
  if (marker === "square") return <rect className={className} x={cx - r} y={cy - r} width={2 * r} height={2 * r} />;
  if (marker === "diamond") {
    const d = r * 1.35;
    return <polygon className={className} points={`${cx},${cy - d} ${cx + d},${cy} ${cx},${cy + d} ${cx - d},${cy}`} />;
  }
  return <circle className={className} cx={cx} cy={cy} r={r} />;
}

// Each vessel's readings as dots and its fitted curve as a line, coloured by condition (controls grey, treatments
// teal, told apart by dash and dot shape); the plan's checkpoint dashed; each half-way point marked. Plain SVG drawn
// from the worker's numbers (nothing computed here but positions).
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
  const groups = conditionGroups(fits.vessels);

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
              <Dot
                key={i}
                className={styles.dot}
                marker={groups.get(groupKey(v))?.marker ?? "circle"}
                cx={x(t / 3600)}
                cy={y(value)}
                r={2}
              />
            ))}
            {v.fit?.ok && v.fit.samples.length > 0 && (
              <path className={styles.curve} d={path(v.fit.samples)} strokeDasharray={groups.get(groupKey(v))?.dash} />
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
            <svg className={styles.swatch} viewBox="0 0 22 10" aria-hidden="true">
              <line x1="0" x2="22" y1="5" y2="5" strokeDasharray={g.dash} />
              <Dot className={styles.swatchDot} marker={g.marker} cx={11} cy={5} r={2.6} />
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
