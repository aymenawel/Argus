"use client";

import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { playhead, usePlayhead } from "@/lib/playhead";
import { byVessel, regionAt } from "@/lib/run-data";
import type { RunSnapshot, RunSource } from "@/lib/run-source";
import { atOrBefore, formatRunTime } from "@/lib/scale";
import type { DetectionOutline, Provenance, Vessel } from "@/lib/types";
import styles from "./RunFrame.module.css";

type Props = { snapshot: RunSnapshot; source: RunSource; mainMetric: string };

const points = (polygon: [number, number][]) => polygon.map(([x, y]) => `${x},${y}`).join(" ");

/** The newest reading of the main measurement per vessel at or before t (lab_mean mains show their L*). */
export function useReadings(snapshot: RunSnapshot, mainMetric: string, t: number) {
  const groups = useMemo(
    () => byVessel(snapshot.measurements, new Set([mainMetric, `${mainMetric}_l`])),
    [snapshot.measurements, mainMetric],
  );
  return (vessel: Vessel) => atOrBefore(groups.get(vessel.id) ?? [], t);
}

function calibrationText(snapshot: RunSnapshot): string {
  const cal = snapshot.view.calibration;
  if (!cal) return "No calibration";
  const name = cal.card === "ruler" ? "Ruler" : "Card";
  return `${name} · ${(1 / cal.mm_per_px).toFixed(2)} px/mm ± ${(cal.rel_uncertainty * 100).toFixed(1)}%`;
}

export function RunFrame({ snapshot, source, mainMetric }: Props) {
  const t = usePlayhead((p) => p.t);
  const selected = usePlayhead((p) => p.selectedVesselId);
  const analyzed = useMemo(() => snapshot.frames.filter((f) => f.analyzed), [snapshot.frames]);
  const frame = atOrBefore(analyzed, t) ?? analyzed[0] ?? null;
  const span = Math.max(analyzed.at(-1)?.t ?? 0, snapshot.progress?.t_end ?? 0);
  const [size, setSize] = useState<{ w: number; h: number } | null>(null);
  const [outlines, setOutlines] = useState<{ frameId: string; items: DetectionOutline[] } | null>(null);
  const reading = useReadings(snapshot, mainMetric, t);
  const { run } = snapshot.view;
  // Regions as drawn, or where a camera move carried them, at the frame shown.
  const shownAt = frame?.t ?? t;
  const vessels = snapshot.view.vessels.map((v) => ({ ...v, roi: regionAt(v, snapshot.events, shownAt) }));

  useEffect(() => {
    if (!frame) return;
    let live = true;
    source
      .detections(frame.id)
      .then((items) => live && setOutlines({ frameId: frame.id, items }))
      .catch(() => undefined); // the frame still shows; outlines come with the next one
    return () => {
      live = false;
    };
  }, [frame, source]);

  const shown = outlines && frame && outlines.frameId === frame.id ? outlines.items : [];
  const scaleNote = run.time_scale !== 1 ? ` · ×${run.time_scale}` : "";
  const provenance = run.source.provenance ?? null;
  const sourceNote =
    run.mode === "live"
      ? `Camera ${run.source.camera_index ?? 0}`
      : provenance
        ? provenance.dataset
        : `Imported${scaleNote}`;

  return (
    <>
      <div className={styles.frame} style={{ aspectRatio: size ? `${size.w} / ${size.h}` : "16 / 9" }}>
        {frame ? (
          // Frames come from the local worker; next/image would only add a resizing hop.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            className={styles.image}
            src={source.frameUrl(frame.id)}
            alt={`Frame at ${formatRunTime(frame.t, span)}`}
            onLoad={(e) => setSize({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })}
          />
        ) : (
          <p className={styles.empty}>No analyzed frame yet</p>
        )}

        {size && (
          <svg className={styles.overlay} viewBox={`0 0 ${size.w} ${size.h}`} aria-hidden="true">
            {vessels.map((v) => (
              <polygon
                key={v.id}
                points={points(v.roi)}
                className={`${styles.roi} ${v.id === selected ? styles.selectedRoi : ""}`}
                onClick={() => playhead.selectVessel(v.id === selected ? null : v.id)}
              />
            ))}
            {shown.flatMap((d, i) =>
              d.outline.map((polygon, j) => (
                <polygon
                  key={`${i}-${j}`}
                  points={points(polygon)}
                  className={`${styles.outline} ${d.vessel_id === selected ? styles.selectedOutline : ""}`}
                />
              )),
            )}
          </svg>
        )}

        {size &&
          vessels.map((v) => {
            const xs = v.roi.map(([x]) => x);
            const ys = v.roi.map(([, y]) => y);
            const left = ((Math.min(...xs) + Math.max(...xs)) / 2 / size.w) * 100;
            const top = (Math.min(...ys) / size.h) * 100;
            const value = reading(v);
            const on = v.id === selected;
            return (
              <button
                key={v.id}
                type="button"
                className={`${styles.tag} ${on ? styles.selectedTag : ""}`}
                style={{ left: `${left}%`, top: `max(8px, calc(${top}% - 34px))` }}
                aria-pressed={on}
                aria-label={`Vessel ${v.label}${value ? `, ${value.display}` : ""}`}
                onClick={() => playhead.selectVessel(on ? null : v.id)}
              >
                <b>{v.label}</b>
                {value && <span className="num">{value.display}</span>}
              </button>
            );
          })}

        <div className={`${styles.hud} ${styles.topLeft}`}>
          <Badge source={run.mode} provenance={provenance} />
          <span className={styles.hudText}>{sourceNote}</span>
        </div>
        <div className={`${styles.hud} ${styles.topRight}`}>
          <span className={`${styles.hudText} num`}>{calibrationText(snapshot)}</span>
        </div>
        <div className={`${styles.hud} ${styles.bottomLeft}`}>
          <span className={`${styles.hudText} num`}>{formatRunTime(frame?.t ?? t, span)}</span>
        </div>
        <div className={`${styles.hud} ${styles.bottomRight}`}>
          <span className={`${styles.hudText} num`}>
            SAM 3.1 · {shown.length} {shown.length === 1 ? "object" : "objects"}
          </span>
        </div>
      </div>
      {provenance && <Credit provenance={provenance} />}
    </>
  );
}

// Published data is credited under every frame of it, with its licence and DOI (D-70).
function Credit({ provenance: p }: { provenance: Provenance }) {
  return (
    <p className={styles.credit}>
      Published data: {p.credit},{" "}
      <a href={p.url} target="_blank" rel="noreferrer">
        {p.dataset}
      </a>{" "}
      (doi:{p.doi}), {p.licence}.{p.assembled && " Argus assembled these frames from the published dishes."}
    </p>
  );
}
