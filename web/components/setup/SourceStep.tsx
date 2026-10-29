"use client";

import { useEffect, useState } from "react";
import { cameraStreamUrl, getCameras } from "@/lib/api";
import type { Setup, SetupSource } from "@/lib/types";
import styles from "./Step.module.css";

type Props = {
  setup: Setup;
  onChange: (setup: Setup) => void;
  videoS: number; // where in the video to set up
  onVideoS: (s: number) => void;
};

const NONE: SetupSource = { kind: "webcam", camera_index: null, paths: [] };

// A camera left running, or a recording to import (spec §4.2). Argus is built for dedicated cameras.
export function SourceStep({ setup, onChange, videoS, onVideoS }: Props) {
  const source = setup.source ?? NONE;
  const [cameras, setCameras] = useState<number[] | null>(null);
  const [paths, setPaths] = useState(source.paths.join("\n"));

  useEffect(() => {
    if (source.kind !== "webcam") return;
    getCameras()
      .then((found) => setCameras(found.map((c) => c.index)))
      .catch(() => setCameras([]));
  }, [source.kind]);

  const set = (next: Partial<SetupSource>) => onChange({ ...setup, source: { ...source, ...next } });

  return (
    <div className={styles.step}>
      <fieldset className={styles.choices}>
        <legend className={styles.hidden}>Where the frames come from</legend>
        <label className={styles.choice}>
          <input
            type="radio"
            name="source-kind"
            checked={source.kind === "webcam"}
            onChange={() => set({ kind: "webcam", paths: [] })}
          />
          A camera, live
        </label>
        <label className={styles.choice}>
          <input
            type="radio"
            name="source-kind"
            checked={source.kind === "video"}
            onChange={() => set({ kind: "video", camera_index: null })}
          />
          A recorded video
        </label>
      </fieldset>

      {source.kind === "webcam" ? (
        <>
          {cameras === null ? (
            <p className={styles.help}>Looking for cameras…</p>
          ) : cameras.length === 0 ? (
            <p className={styles.error}>No camera found. Plug one in, then come back to this step.</p>
          ) : (
            <fieldset className={styles.choices}>
              <legend className={styles.label}>Camera</legend>
              {cameras.map((index) => (
                <label key={index} className={styles.choice}>
                  <input
                    type="radio"
                    name="camera"
                    checked={source.camera_index === index}
                    onChange={() => set({ camera_index: index })}
                  />
                  Camera {index}
                </label>
              ))}
            </fieldset>
          )}
          {source.camera_index !== null && (
            // The worker's MJPEG preview of the camera; next/image doesn't stream.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              className={styles.camera}
              src={cameraStreamUrl(source.camera_index)}
              alt={`Live view of camera ${source.camera_index}`}
            />
          )}
        </>
      ) : (
        <>
          <label className={styles.field}>
            <span className={styles.label}>Video files</span>
            <textarea
              className={styles.textarea}
              value={paths}
              onChange={(e) => {
                setPaths(e.target.value);
                set({
                  paths: e.target.value
                    .split("\n")
                    .map((p) => p.trim().replace(/^"|"$/g, ""))
                    .filter(Boolean),
                });
              }}
              placeholder={"C:\\Recordings\\run 1.mp4"}
              spellCheck={false}
            />
            <span className={styles.help}>One path per line, in order: they are read as one run.</span>
          </label>
          <div className={styles.grid}>
            <label className={styles.field}>
              <span className={styles.label}>Time scale</span>
              <input
                className={`${styles.input} num`}
                type="number"
                min={0.01}
                step="any"
                value={setup.time_scale}
                onChange={(e) => onChange({ ...setup, time_scale: Number(e.target.value) || 1 })}
              />
              <span className={styles.help}>1 for real time; 60 when each video second is a minute (a timelapse).</span>
            </label>
            <label className={styles.field}>
              <span className={styles.label}>Recording started (optional)</span>
              <input
                className={styles.input}
                type="datetime-local"
                value={source.start_time ? source.start_time.slice(0, 16) : ""}
                onChange={(e) => set({ start_time: e.target.value ? new Date(e.target.value).toISOString() : null })}
              />
            </label>
            <label className={styles.field}>
              <span className={styles.label}>Set up on the frame at</span>
              <input
                className={`${styles.input} num`}
                type="number"
                min={0}
                step="any"
                value={videoS}
                onChange={(e) => onVideoS(Math.max(0, Number(e.target.value) || 0))}
              />
              <span className={styles.help}>Seconds into the video: pick a moment where every vessel is in view.</span>
            </label>
          </div>
        </>
      )}
    </div>
  );
}
