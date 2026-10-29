"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { ApiError, lockPlan, startRun } from "@/lib/api";
import type { Plan, PlanDraft, Setup } from "@/lib/types";
import styles from "./Step.module.css";

type Props = {
  experimentId: string;
  setup: Setup;
  plan: PlanDraft;
  locked: Plan | null;
  saving: boolean; // the last edits are still being saved
  unit: string; // the plan metric's unit
  onLocked: (plan: Plan) => void;
  onStarted: () => void;
};

const locale = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

/** Run time in words: "10 min", "2 h 30 min" (a bare "0:10" reads as seconds). */
function inWords(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.round((s % 3600) / 60);
  return h ? `${h} h${m ? ` ${m} min` : ""}` : `${m} min`;
}

// Lock the plan, then start: the plan is fixed before any data comes in, so the run can test it (KB 08).
export function StartStep({ experimentId, setup, plan, locked, saving, unit, onLocked, onStarted }: Props) {
  const [busy, setBusy] = useState<"lock" | "start" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const source = setup.source;
  const fail = (e: unknown) => setError(e instanceof ApiError ? e.detail : "That didn't work.");

  return (
    <div className={styles.step}>
      <ul className={styles.list} aria-label="Summary">
        <li className={styles.item}>
          <strong>Source</strong>
          {source?.kind === "webcam"
            ? `Camera ${source.camera_index}, live`
            : `${source?.paths.length ?? 0} video file(s) · time ×${setup.time_scale}`}
        </li>
        <li className={styles.item}>
          <strong>Vessels</strong>
          {setup.vessels
            .map((v) => `${v.label} ${v.role ?? "?"}${v.condition ? ` (${v.condition.value})` : ""}`)
            .join(" · ")}
        </li>
        <li className={styles.item}>
          <strong>Prediction</strong>
          {plan.treatment ?? "every treatment vessel"} reads {plan.direction} than the controls on {plan.metric}
          {plan.min_effect !== null ? `, by at least ${plan.min_effect} ${unit}` : ""}, from{" "}
          {plan.checkpoint_s !== null ? `${inWords(plan.checkpoint_s)} of run time` : "?"}
        </li>
      </ul>

      {locked ? (
        <p className={styles.note}>
          Plan version {locked.version} locked {locked.locked_at ? locale.format(new Date(locked.locked_at)) : ""} ·
          fingerprint <code className="num">{locked.sha256?.slice(0, 12)}</code>. Later edits make a new version that
          the verdict ignores.
        </p>
      ) : (
        <div className={styles.row}>
          <Button
            variant="primary"
            disabled={busy !== null || saving}
            onClick={() => {
              setBusy("lock");
              setError(null);
              lockPlan(experimentId)
                .then(onLocked)
                .catch(fail)
                .finally(() => setBusy(null));
            }}
          >
            {busy === "lock" ? "Locking…" : "Lock the plan"}
          </Button>
          <span className={styles.help}>Once locked it can&apos;t change: the verdict is judged against it.</span>
        </div>
      )}

      {locked && (
        <div className={styles.row}>
          <Button
            variant="primary"
            disabled={busy !== null || !source}
            onClick={() => {
              if (!source) return;
              setBusy("start");
              setError(null);
              const body =
                source.kind === "webcam"
                  ? { mode: "live" as const, camera_index: source.camera_index ?? 0 }
                  : {
                      mode: "imported" as const,
                      paths: source.paths,
                      time_scale: setup.time_scale,
                      ...(source.start_time ? { start_time: source.start_time } : {}),
                    };
              startRun(experimentId, body)
                .then(onStarted)
                .catch(fail)
                .finally(() => setBusy(null));
            }}
          >
            {busy === "start" ? "Starting…" : "Start the run"}
          </Button>
        </div>
      )}
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
