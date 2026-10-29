"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { ApiError, preview as checkSetup } from "@/lib/api";
import type { FrameRequest, Preview, Setup } from "@/lib/types";
import { SetupFrame, type Region } from "./SetupFrame";
import styles from "./Step.module.css";

type Props = {
  experimentId: string;
  setup: Setup;
  frame: FrameRequest;
  preview: Preview | null;
  onPreview: (preview: Preview | null) => void;
  onChange: (setup: Setup) => void;
};

const CARD = { standard: "Standard card", compact: "Compact card", ruler: "Ruler" } as const;

function quality(preview: Preview, label: string): { text: string; ok: boolean } {
  const flags = preview.quality.flags;
  if (flags.includes("blurred")) return { text: "Blurry: focus the camera or hold it still", ok: false };
  if (flags.includes(`occluded:${label}`) || flags.includes("occluded"))
    return { text: "Something is in front of it", ok: false };
  if (flags.includes(`saturated:${label}`)) return { text: "Glare: move the lamp or turn the vessel", ok: false };
  return { text: "Sharp, no glare", ok: true };
}

// The frame as a run would see it: the card or a ruler, sharpness and glare per vessel, and what Argus would
// measure in each, before anything is recorded (spec §8).
export function CheckStep({ experimentId, setup, frame, preview, onPreview, onChange }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [points, setPoints] = useState<[number, number][]>(setup.ruler ? [setup.ruler.p1, setup.ruler.p2] : []);
  const [rulerMm, setRulerMm] = useState(setup.ruler ? String(setup.ruler.distance_mm) : "");
  const src = preview ? `data:image/jpeg;base64,${preview.frame_jpeg_b64}` : null;
  const noCard = preview !== null && preview.calibration === null;

  const check = () => {
    setBusy(true);
    setError(null);
    checkSetup(experimentId, frame)
      .then(onPreview)
      .catch((e: unknown) => setError(e instanceof ApiError ? e.detail : "The check failed."))
      .finally(() => setBusy(false));
  };

  const regions: Region[] = setup.vessels.map((v) => ({ key: v.label, roi: v.roi, label: v.label }));
  const outlines = preview ? preview.vessels.flatMap((v) => v.outlines) : [];

  return (
    <div className={styles.step}>
      <p className={styles.lead}>
        Argus measures in millimetres from the Argus Card in view, at the vessels&apos; height. Check the setup to see
        what it will measure before you start.
      </p>
      <div className={styles.row}>
        <label className={styles.field}>
          <span className={styles.label}>Print check (optional)</span>
          <input
            className={`${styles.input} ${styles.short} num`}
            type="number"
            min={90}
            max={110}
            step={0.1}
            value={setup.print_check_mm ?? ""}
            placeholder="100.0"
            onChange={(e) => {
              const mm = e.target.value === "" ? null : Number(e.target.value);
              onChange({ ...setup, print_check_mm: mm !== null && mm >= 90 && mm <= 110 ? mm : null });
            }}
          />
        </label>
        <Button variant="primary" disabled={busy} onClick={check}>
          {busy ? "Checking…" : preview ? "Check again" : "Check the setup"}
        </Button>
      </div>
      <p className={styles.help}>
        Print check: measure the card&apos;s 100 mm line with a ruler and type what you read, if your printer scaled it.
      </p>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      <div className={styles.split}>
        <SetupFrame
          src={src}
          alt="The frame Argus checked"
          empty="Check the setup to see the frame as Argus sees it."
          regions={regions}
          outlines={outlines}
          ruler={noCard ? points : undefined}
          onPoint={noCard ? (p) => setPoints((current) => (current.length >= 2 ? [p] : [...current, p])) : undefined}
        />
        {preview && (
          <div className={styles.step}>
            {preview.calibration ? (
              <p className={styles.good}>
                {CARD[preview.calibration.card]} · {preview.calibration.px_per_mm.toFixed(2)} px/mm ±{" "}
                {(preview.calibration.rel_uncertainty * 100).toFixed(1)} %
              </p>
            ) : (
              <div className={styles.field}>
                <p className={styles.bad}>No card in view: put it beside the vessels, or mark a ruler.</p>
                <span className={styles.help}>
                  Click the two ends of a known length on the frame ({points.length} of 2), then type its length.
                </span>
                <div className={styles.row}>
                  <input
                    className={`${styles.input} ${styles.short} num`}
                    type="number"
                    min={1}
                    step="any"
                    value={rulerMm}
                    placeholder="mm"
                    aria-label="Ruler length in millimetres"
                    onChange={(e) => setRulerMm(e.target.value)}
                  />
                  <Button
                    disabled={points.length !== 2 || !(Number(rulerMm) > 0)}
                    onClick={() =>
                      onChange({ ...setup, ruler: { p1: points[0], p2: points[1], distance_mm: Number(rulerMm) } })
                    }
                  >
                    Use this ruler
                  </Button>
                </div>
                {setup.ruler && <span className={styles.help}>Ruler set: check again to measure with it.</span>}
              </div>
            )}
            <ul className={styles.list} aria-label="What Argus will measure">
              {preview.vessels.map((v) => {
                const q = quality(preview, v.label);
                return (
                  <li key={v.label} className={styles.item}>
                    <span className={styles.badge}>{v.label}</span>
                    <span className={q.ok ? styles.good : styles.bad}>{q.text}</span>
                    <span className="num">
                      {v.readings.length > 0
                        ? v.readings
                            .filter((r) => !r.metric.endsWith("_a") && !r.metric.endsWith("_b"))
                            .map((r) => `${r.metric} ${r.display}`)
                            .join(" · ")
                        : preview.calibration
                          ? "SAM 3.1 found nothing to measure here"
                          : "Nothing to measure without millimetres"}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
