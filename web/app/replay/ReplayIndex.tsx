"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/shell/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { VerdictChip } from "@/components/ui/VerdictChip";
import { type BundleIndex, type BundleIndexEntry, getCover, getReplayIndex } from "@/lib/replay";
import type { VerdictLevel } from "@/lib/types";
import styles from "./page.module.css";

const day = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });

const sentence = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

// The demo's front page (D-83, D-98): the same Experiments list as the app, one card per bundled run with its last
// measured picture, opening the run itself. It says once what the demo is and when it was built.
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
      <PageHeader
        crumb="Argus Labs · demo"
        title="Experiments"
        finding="Recorded runs, open read-only. Nothing here is live; everything shown was built Oct 27 – Nov 4, 2026."
        actions={
          <a className={styles.source} href="https://github.com/aymenawel/Argus" target="_blank" rel="noreferrer">
            Source and how it works
          </a>
        }
      />
      <p className={styles.intro}>
        Argus is an AI lab partner. It watches an experiment through a camera, measures what changes in real units with
        SAM 3.1, writes checked notes, judges the idea with Muse Wonder and suggests the next run.
      </p>
      {error ? (
        <Panel className={styles.panel}>
          <div className={styles.message} role="alert">
            <p className={styles.messageTitle}>The demo couldn&apos;t load: {error}.</p>
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
              <RunCard run={run} />
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function RunCard({ run }: { run: BundleIndexEntry }) {
  const [cover, setCover] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    getCover(run.run_id)
      .then((url) => live && setCover(url))
      .catch(() => undefined); // the card reads without its picture
    return () => {
      live = false;
    };
  }, [run.run_id]);

  return (
    <Link className={styles.card} href={`/replay/${run.run_id}`}>
      <span className={styles.cover}>
        {cover && (
          // A bundled frame, served as it is (next/image would only add a resizing hop), loaded at once: the covers
          // are the first thing on the page.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={cover} alt="" />
        )}
      </span>
      <span className={styles.cardText}>
        <span className={styles.cardTitle}>{run.title}</span>
        <span className={styles.meta}>
          {sentence(run.source_label)} · {run.source_label === "published data" ? "analysed" : "recorded"}{" "}
          {day(run.recorded)}
        </span>
      </span>
      {run.verdict && (
        <span className={styles.verdict}>
          <VerdictChip level={run.verdict as VerdictLevel} retrospective={run.source_label === "published data"} />
        </span>
      )}
    </Link>
  );
}
