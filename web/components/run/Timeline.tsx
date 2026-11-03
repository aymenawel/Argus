"use client";

import { type KeyboardEvent, type PointerEvent, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { playhead, usePlayhead } from "@/lib/playhead";
import type { RunSnapshot, RunSource } from "@/lib/run-source";
import { formatRunTime, linearScale } from "@/lib/scale";
import type { FrameRow, RunEvent } from "@/lib/types";
import styles from "./Timeline.module.css";

type Props = { snapshot: RunSnapshot; source: RunSource };

// Tick steps in seconds; the first that fits the ruler (at most 8 ticks) is used.
const STEPS = [10, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200, 10800, 21600, 43200, 86400];
// The events worth a dot on the track, in the page's words (D-95); a watcher's "change" is too frequent to mark.
const MARKED: Partial<Record<RunEvent["kind"], string>> = {
  intervention: "A hand or object at the samples",
  rule: "A set threshold was crossed",
  camera_moved: "The camera moved",
  segment_failed: "SAM couldn't outline a picture",
  missed: "SAM lost sight of something",
};
const PLAY_STEPS = 200; // a run plays through in about 20 seconds, whatever its length

function nearest(frames: FrameRow[], t: number): FrameRow | null {
  let best: FrameRow | null = null;
  for (const frame of frames) {
    if (best === null || Math.abs(frame.t - t) < Math.abs(best.t - t)) best = frame;
  }
  return best;
}

export function Timeline({ snapshot, source }: Props) {
  const t = usePlayhead((p) => p.t);
  const follow = usePlayhead((p) => p.follow);
  const track = useRef<HTMLDivElement>(null);
  const [playing, setPlaying] = useState(false);
  const [width, setWidth] = useState(0);
  const dragging = useRef(false);

  const analyzed = useMemo(() => snapshot.frames.filter((f) => f.analyzed), [snapshot.frames]);
  const newest = analyzed.at(-1)?.t ?? 0;
  const tEnd = Math.max(newest, snapshot.progress?.t_end ?? 0, 1);
  const percent = linearScale([0, tEnd], [0, 100]);
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

  const marks = snapshot.events.filter((e) => e.kind in MARKED);

  // Rewatching like a video: each step moves the playhead to the next measured picture a little further on.
  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      const next = analyzed.find((f) => f.t >= playhead.get().t + tEnd / PLAY_STEPS);
      if (next) playhead.setT(next.t);
      else setPlaying(false);
    }, 100);
    return () => window.clearInterval(id);
  }, [playing, analyzed, tEnd]);

  function togglePlay() {
    if (!playing && t >= newest - 1e-6 && analyzed.length > 0) playhead.setT(analyzed[0].t);
    setPlaying((on) => !on);
  }

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
        <span className={styles.play}>
          <button
            type="button"
            className={styles.playButton}
            onClick={togglePlay}
            aria-label={playing ? "Pause" : "Play the run"}
            disabled={analyzed.length < 2}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              {playing ? <path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" /> : <path d="M8 5.5v13l10.5-6.5z" />}
            </svg>
          </button>
          <span className={`${styles.clock} num`}>
            {formatRunTime(t, tEnd)} <span className={styles.faint}>/ {formatRunTime(tEnd)}</span>
          </span>
        </span>
        {snapshot.view.running && !follow && (
          <Button variant="text" onClick={playhead.followLive}>
            Follow live
          </Button>
        )}
      </div>

      <div className={styles.grid}>
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

        <div className={styles.events}>
          {marks.map((e) => (
            <button
              key={e.id}
              type="button"
              className={`${styles.dot} ${styles[e.kind] ?? ""}`}
              style={{ left: `${percent(e.t_start)}%` }}
              title={`${MARKED[e.kind]} · ${formatRunTime(e.t_start, tEnd)}`}
              aria-label={`${MARKED[e.kind]} at ${formatRunTime(e.t_start, tEnd)}`}
              onClick={() => playhead.setT(e.t_start)}
            />
          ))}
        </div>
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
