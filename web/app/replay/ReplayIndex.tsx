"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ReplayBanner } from "@/components/replay/ReplayBanner";
import { PageHeader } from "@/components/shell/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { VerdictChip } from "@/components/ui/VerdictChip";
import { type BundleIndex, getReplayIndex } from "@/lib/replay";
import type { VerdictLevel } from "@/lib/types";
import styles from "./page.module.css";

const day = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });

const sentence = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

// The public replay's front page (D-83): one card per bundled run, each opening its Run view and Results.
export function ReplayIndex() {
  const [index, setIndex] = useState<BundleIndex | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    getReplayIndex()
      .then((found) => live && setIndex(found))
      .catch((e: unknown) => live && setError(e instanceof Error ? e.message : String(e)));
    return () => {
      live = false;
    };
  }, []);

  return (
    <>
      <ReplayBanner manifest={null} />
      <PageHeader title="Replays" finding="Finished runs, recorded and replayed read-only." />
      {error ? (
        <Panel className={styles.panel}>
          <div className={styles.message} role="alert">
            <p className={styles.messageTitle}>The replay couldn&apos;t load: {error}.</p>
          </div>
        </Panel>
      ) : index === null ? (
        <div className={styles.placeholder} aria-busy="true" />
      ) : index.runs.length === 0 ? (
        <Panel className={styles.panel}>
          <div className={styles.message}>
            <p className={styles.messageTitle}>No runs are bundled yet.</p>
          </div>
        </Panel>
      ) : (
        <ul className={styles.cards}>
          {index.runs.map((run) => (
            <li key={run.run_id}>
              <Panel>
                <div className={styles.card}>
                  <h2 className={styles.cardTitle}>{run.title}</h2>
                  <p className={styles.meta}>
                    {sentence(run.source_label)} · recorded {day(run.recorded)}
                  </p>
                  {run.verdict && <VerdictChip level={run.verdict as VerdictLevel} />}
                  <div className={styles.links}>
                    <Link href={`/replay/${run.run_id}`}>Run view</Link>
                    <Link href={`/replay/${run.run_id}/results`}>Results</Link>
                  </div>
                </div>
              </Panel>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
