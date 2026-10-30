"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ApiError, getNextRun, suggestNextRun } from "@/lib/api";
import type { NextRun } from "@/lib/types";
import styles from "./NextRunCard.module.css";

type Props = { runId: string; running: boolean };

const hours = (h: number) => `${h >= 10 ? h.toFixed(0) : h.toFixed(1)} h`;

// The next run (D-80): replicates and run length computed in code from this run, the reasons written by Muse Wonder
// through the claim checker (or by code). A suggestion, never a measurement: Argus doesn't start runs.
export function NextRunCard({ runId, running }: Props) {
  const [loaded, setLoaded] = useState<{ runId: string; next: NextRun | null } | null>(null);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    getNextRun(runId)
      .then((next) => live && setLoaded({ runId, next }))
      .catch(() => live && setLoaded({ runId, next: null }));
    return () => {
      live = false;
    };
  }, [runId]);

  const next = loaded?.runId === runId ? loaded.next : null;
  const ask = () => {
    setAsking(true);
    setError(null);
    suggestNextRun(runId)
      .then((made) => setLoaded({ runId, next: made }))
      .catch((e: unknown) => setError(e instanceof ApiError ? e.detail : "No suggestion this time."))
      .finally(() => setAsking(false));
  };

  const button = (
    <Button variant={next ? "secondary" : "primary"} disabled={running || asking} onClick={ask}>
      {asking ? "Suggesting… (about a minute)" : next ? "Suggest again" : "Suggest the next run"}
    </Button>
  );

  if (!next) {
    return (
      <div className={styles.card}>
        <p className={styles.none}>
          {running
            ? "The run is still going: the next run is suggested once it has ended."
            : "No suggestion yet. Argus works out the replicates and run length from this run's spread and curves."}
        </p>
        <div className={styles.actions}>{button}</div>
        {error && (
          <p className={styles.error} role="alert">
            {error}
          </p>
        )}
      </div>
    );
  }

  const { numbers, body } = next;
  return (
    <div className={styles.card}>
      <p className={styles.label}>Suggested, not measured</p>
      <dl className={styles.numbers}>
        <div>
          <dt>Vessels per condition</dt>
          <dd className="num">{numbers.replicates ?? "Unknown"}</dd>
          <dd className={styles.reason}>{numbers.replicates_reason}</dd>
        </div>
        <div>
          <dt>Run length</dt>
          <dd className="num">{numbers.hours !== null ? hours(numbers.hours) : "Unknown"}</dd>
          <dd className={styles.reason}>{numbers.hours_reason}</dd>
        </div>
        <div>
          <dt>Levels to try</dt>
          <dd className="num">{numbers.levels.length > 0 ? numbers.levels.join(", ") : "None"}</dd>
          <dd className={styles.reason}>{numbers.levels_reason}</dd>
        </div>
      </dl>
      {body.safety.map((warning) => (
        <p key={warning} className={styles.safety} role="note">
          {warning}
        </p>
      ))}
      <div className={styles.text}>
        <p>{body.why}</p>
        {body.change && (
          <p>
            <strong>Change: </strong>
            {body.change}
          </p>
        )}
        {body.watch_for && (
          <p>
            <strong>Watch for: </strong>
            {body.watch_for}
          </p>
        )}
      </div>
      <div className={styles.actions}>
        {button}
        {body.written_by === "code" && <span className={styles.tag}>{body.code_reason ?? "Written by code"}</span>}
        {next.fell_back && <span className={styles.tag}>Fell back to Muse Spark</span>}
      </div>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
