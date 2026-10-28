"use client";

import { Fragment, type KeyboardEvent, type PointerEvent, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { playhead, usePlayhead } from "@/lib/playhead";
import { byVessel } from "@/lib/run-data";
import type { RunSnapshot, RunSource } from "@/lib/run-source";
import { formatRunTime, linearScale } from "@/lib/scale";
import type { FrameRow, MeasurementRow, RunEvent } from "@/lib/types";
import { useReadings } from "./RunFrame";
import styles from "./Timeline.module.css";

type Props = { snapshot: RunSnapshot; source: RunSource; mainMetric: string };

// Tick steps in seconds; the first that fits the ruler (at most 8 ticks) is used.
const STEPS = [10, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200, 10800, 21600, 43200, 86400];
const MARKED = new Set<RunEvent["kind"]>(["change", "intervention", "camera_moved", "segment_failed"]);
const LANE_W = 1000;
const LANE_H = 40;

function nearest(frames: FrameRow[], t: number): FrameRow | null {
  let best: FrameRow | null = null;
  for (const frame of frames) {
    if (best === null || Math.abs(frame.t - t) < Math.abs(best.t - t)) best = frame;
  }
  return best;
}

function lanePoints(rows: MeasurementRow[], tEnd: number): string {
  if (rows.length === 0) return "";
  const values = rows.map((r) => r.value);
  const low = Math.min(...values);
  const high = Math.max(...values);
  const x = linearScale([0, tEnd], [0, LANE_W]);
  const y = linearScale([low, high === low ? low + 1 : high], [LANE_H - 6, 6]);
  return rows.map((r) => `${x(r.t).toFixed(1)},${y(r.value).toFixed(1)}`).join(" ");
}

export function Timeline({ snapshot, source, mainMetric }: Props) {
  const t = usePlayhead((p) => p.t);
  const follow = usePlayhead((p) => p.follow);
  const selected = usePlayhead((p) => p.selectedVesselId);
  const reading = useReadings(snapshot, mainMetric, t);
  const track = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  const dragging = useRef(false);

  const analyzed = useMemo(() => snapshot.frames.filter((f) => f.analyzed), [snapshot.frames]);
  const newest = analyzed.at(-1)?.t ?? 0;
  const tEnd = Math.max(newest, snapshot.progress?.t_end ?? 0, 1);
  const percent = linearScale([0, tEnd], [0, 100]);
  const laneX = linearScale([0, tEnd], [0, LANE_W]);
  const maxTicks = Math.max(2, Math.min(8, Math.floor(width / 64))); // labels need about 64 px each
  const step = STEPS.find((s) => tEnd / s <= maxTicks) ?? STEPS[STEPS.length - 1];
  const ticks = Array.from({ length: Math.floor(tEnd / step) + 1 }, (_, i) => i * step);

  useEffect(() => {
    const element = track.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const thumbs = useMemo(() => {
    const count = Math.max(1, Math.min(analyzed.length, Math.floor(width / 56)));
    if (analyzed.length === 0) return [];
    return Array.from(
      { length: count },
      (_, i) => analyzed[Math.round((i * (analyzed.length - 1)) / Math.max(count - 1, 1))],
    );
  }, [analyzed, width]);

  const series = useMemo(
    () => byVessel(snapshot.measurements, new Set([mainMetric, `${mainMetric}_l`])),
    [snapshot.measurements, mainMetric],
  );

  const marks = snapshot.events.filter((e) => MARKED.has(e.kind));

  function scrubTo(clientX: number) {
    const rect = track.current?.getBoundingClientRect();
    if (!rect || rect.width === 0) return;
    const wanted = Math.min(Math.max(((clientX - rect.left) / rect.width) * tEnd, 0), tEnd);
    const frame = nearest(analyzed, wanted);
    playhead.setT(frame ? frame.t : wanted);
  }

  function onPointerDown(e: PointerEvent<HTMLElement>) {
    dragging.current = true;
    e.currentTarget.setPointerCapture(e.pointerId);
    scrubTo(e.clientX);
  }

  function onPointerMove(e: PointerEvent<HTMLElement>) {
    if (dragging.current) scrubTo(e.clientX);
  }

  function onKeyDown(e: KeyboardEvent<HTMLElement>) {
    if (analyzed.length === 0) return;
    const index = analyzed.findIndex((f) => f.t >= t - 1e-6);
    const at = index === -1 ? analyzed.length - 1 : index;
    const moves: Record<string, number> = {
      ArrowLeft: Math.max(at - 1, 0),
      ArrowRight: Math.min(analyzed[at].t > t + 1e-6 ? at : at + 1, analyzed.length - 1),
      Home: 0,
      End: analyzed.length - 1,
    };
    if (!(e.key in moves)) return;
    e.preventDefault();
    playhead.setT(analyzed[moves[e.key]].t);
  }

  return (
    <div className={styles.timeline}>
      <div className={styles.controls}>
        <span className={`${styles.clock} num`}>
          {formatRunTime(t, tEnd)} <span className={styles.faint}>/ {formatRunTime(tEnd)}</span>
        </span>
        {snapshot.view.running && !follow && (
          <Button variant="text" onClick={playhead.followLive}>
            Follow live
          </Button>
        )}
      </div>

      <div className={styles.grid}>
        <div className={styles.label} />
        <div
          ref={track}
          className={styles.ruler}
          role="slider"
          tabIndex={0}
          aria-label="Playhead"
          aria-valuemin={0}
          aria-valuemax={Math.round(tEnd)}
          aria-valuenow={Math.round(t)}
          aria-valuetext={formatRunTime(t, tEnd)}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={() => (dragging.current = false)}
          onKeyDown={onKeyDown}
        >
          {ticks.map((tick) => (
            <span key={tick} className={`${styles.tick} num`} style={{ left: `${percent(tick)}%` }}>
              {formatRunTime(tick, tEnd)}
            </span>
          ))}
        </div>

        <div className={styles.label}>Frames</div>
        <div className={styles.film}>
          {thumbs.map((frame) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              key={frame.id}
              src={source.frameUrl(frame.id, 160)}
              alt=""
              loading="lazy"
              className={styles.thumb}
              onClick={() => playhead.setT(frame.t)}
            />
          ))}
        </div>

        {snapshot.view.vessels.map((v) => {
          const on = v.id === selected;
          const own = marks.filter((e) => e.vessel_id === v.id || e.vessel_id === null);
          return (
            <Fragment key={v.id}>
              <div className={styles.label}>
                <b>{v.label}</b>
                <span className="num">{reading(v)?.display ?? "—"}</span>
              </div>
              <button
                type="button"
                className={`${styles.lane} ${on ? styles.selected : ""}`}
                aria-pressed={on}
                aria-label={`Vessel ${v.label} over time`}
                onClick={() => playhead.selectVessel(on ? null : v.id)}
              >
                <svg viewBox={`0 0 ${LANE_W} ${LANE_H}`} preserveAspectRatio="none" aria-hidden="true">
                  {own.map((e) => (
                    <rect
                      key={e.id}
                      className={`${styles.mark} ${styles[e.kind] ?? ""}`}
                      x={laneX(e.t_start)}
                      y={4}
                      width={Math.max(4, laneX(e.t_end ?? e.t_start) - laneX(e.t_start))}
                      height={LANE_H - 8}
                    />
                  ))}
                  <polyline className={styles.line} points={lanePoints(series.get(v.id) ?? [], tEnd)} />
                </svg>
              </button>
            </Fragment>
          );
        })}

        <div className={styles.playheadLayer} aria-hidden="true">
          <div className={styles.playhead} style={{ left: `${percent(Math.min(t, tEnd))}%` }}>
            <span
              className={`${styles.knob} num`}
              onPointerDown={onPointerDown}
              onPointerMove={onPointerMove}
              onPointerUp={() => (dragging.current = false)}
            >
              {formatRunTime(t, tEnd)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
