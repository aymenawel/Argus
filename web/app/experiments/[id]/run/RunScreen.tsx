"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Feed } from "@/components/feed/Feed";
import { VerdictPanel } from "@/components/verdict/VerdictPanel";
import { Readouts } from "@/components/run/Readouts";
import { RunFrame } from "@/components/run/RunFrame";
import { Timeline } from "@/components/run/Timeline";
import { PageHeader } from "@/components/shell/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import { ApiError, apiBase, getExperiment, getRecipes, getRuns, stopRun } from "@/lib/api";
import { playhead } from "@/lib/playhead";
import { runNotice } from "@/lib/run-data";
import { LiveSource, type RunSnapshot } from "@/lib/run-source";
import { formatRunTime } from "@/lib/scale";
import type { Experiment } from "@/lib/types";
import styles from "./page.module.css";

type Load =
  | { state: "loading" }
  | { state: "error"; error: ApiError }
  | { state: "empty"; experiment: Experiment }
  | { state: "ready"; experiment: Experiment; mainMetric: string; runNumber: number; source: LiveSource };

function finding(snapshot: RunSnapshot): string {
  const { view, progress, frames } = snapshot;
  const analyzed = frames.filter((f) => f.analyzed);
  const count = `${analyzed.length} ${analyzed.length === 1 ? "frame" : "frames"} analyzed`;
  const last = analyzed.at(-1)?.t ?? 0;
  if (view.running) {
    if (progress?.stage === "measure" && progress.t != null && progress.t_end != null) {
      return `Analyzing ${formatRunTime(progress.t, progress.t_end)} of ${formatRunTime(progress.t_end)} · ${progress.speed ?? 0}× real time`;
    }
    if (progress?.stage === "segment") return `Segmenting with SAM 3.1 · ${progress.done} of ${progress.total} clips`;
    if (progress?.stage === "scan" && progress.t != null) {
      return `Reading the video · ${formatRunTime(progress.t)} so far · ${progress.speed ?? 0}× real time`;
    }
    return view.run.mode === "live" ? `Watching live · ${count}` : "Starting the import";
  }
  if (view.run.status === "finished") return `Finished · ${count} over ${formatRunTime(last)}`;
  return `Stopped at ${formatRunTime(last)} · ${count}`;
}

export function RunScreen() {
  const { id } = useParams<{ id: string }>();
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [snapshot, setSnapshot] = useState<RunSnapshot | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [stopping, setStopping] = useState(false);

  useEffect(() => {
    let live = true;
    let unsubscribe = () => {};
    Promise.all([getExperiment(id), getRecipes(), getRuns(id)])
      .then(([experiment, recipes, runs]) => {
        if (!live) return;
        if (runs.length === 0) {
          setLoad({ state: "empty", experiment });
          return;
        }
        // A run started later on this experiment (by `argus run`, say) takes over the page when it appears.
        const asked = new Set<string>();
        const shown = runs[0].run.id;
        const onOtherRun = (runId: string) => {
          if (asked.has(runId)) return;
          asked.add(runId);
          getRuns(id)
            .then((latest) => live && latest[0]?.run.id !== shown && setAttempt((a) => a + 1))
            .catch(() => undefined);
        };
        const source = new LiveSource(shown, onOtherRun);
        const mainMetric = recipes.find((r) => r.id === experiment.recipe_id)?.main_measurement ?? "";
        playhead.reset();
        unsubscribe = source.subscribe((next) => live && setSnapshot(next));
        setLoad({ state: "ready", experiment, mainMetric, runNumber: runs.length, source });
        return source.load().then((first) => live && setSnapshot(first));
      })
      .catch((error: unknown) => {
        if (live)
          setLoad({ state: "error", error: error instanceof ApiError ? error : new ApiError(0, String(error)) });
      });
    return () => {
      live = false;
      unsubscribe();
    };
  }, [id, attempt]);

  // Follow the newest frame unless the researcher moved the playhead.
  const newest = useMemo(() => snapshot?.frames.filter((f) => f.analyzed).at(-1)?.t, [snapshot]);
  useEffect(() => {
    if (newest !== undefined) playhead.sync(newest);
  }, [newest]);

  const title = load.state === "ready" || load.state === "empty" ? load.experiment.title : "Run";
  const crumb = (
    <>
      <Link href="/">Experiments</Link>
      <span className={styles.faint}>/</span>
      <span>{title}</span>
      {load.state === "ready" && (
        <>
          <span className={styles.faint}>/</span>
          <span>Run {load.runNumber}</span>
        </>
      )}
    </>
  );

  if (load.state === "error") {
    return (
      <>
        <PageHeader crumb={crumb} title={title} />
        <Panel className={styles.panel}>
          <div className={styles.message} role="alert">
            <p className={styles.messageTitle}>
              {load.error.status === 0
                ? `Couldn't reach the Argus worker at ${apiBase()}.`
                : `The Argus worker answered ${load.error.status}: ${load.error.detail}`}
            </p>
            <Button
              onClick={() => {
                setLoad({ state: "loading" });
                setAttempt((a) => a + 1);
              }}
            >
              Retry
            </Button>
          </div>
        </Panel>
      </>
    );
  }

  if (load.state === "empty") {
    return (
      <>
        <PageHeader crumb={crumb} title={title} />
        <Panel className={styles.panel}>
          <div className={styles.message}>
            <p className={styles.messageTitle}>No run yet</p>
            <p className={styles.messageText}>
              Set up the vessels and lock the plan first, then start the run from the setup.
            </p>
            <Link className={styles.setupLink} href={`/experiments/${id}/setup`}>
              Open the setup
            </Link>
          </div>
        </Panel>
      </>
    );
  }

  const ready = load.state === "ready" && snapshot !== null;
  const view = ready ? snapshot.view : null;
  const problem = ready ? runNotice(snapshot.events, snapshot.view) : null;

  return (
    <>
      <PageHeader
        crumb={crumb}
        title={title}
        finding={ready ? finding(snapshot) : undefined}
        actions={
          view && (
            <>
              <Badge source={view.run.mode} />
              <span className={`${styles.spend} num`}>Spend ${view.spend_usd.toFixed(2)}</span>
              {view.running && (
                <Button
                  variant="primary"
                  disabled={stopping}
                  onClick={() => {
                    setStopping(true);
                    stopRun(view.run.id)
                      .catch(() => undefined)
                      .finally(() => setStopping(false));
                  }}
                >
                  {stopping ? "Stopping…" : "Stop run"}
                </Button>
              )}
            </>
          )
        }
      />
      {problem && (
        <p className={styles.notice} role="status">
          {problem}
        </p>
      )}
      <div className={styles.workspace}>
        <Panel className={styles.panel}>
          {ready && load.state === "ready" ? (
            <>
              <RunFrame snapshot={snapshot} source={load.source} mainMetric={load.mainMetric} />
              <Readouts snapshot={snapshot} mainMetric={load.mainMetric} />
            </>
          ) : (
            <div className={styles.placeholder} aria-busy="true" />
          )}
        </Panel>
        {ready && (
          <Panel title="Notes" className={styles.feedPanel}>
            <Feed snapshot={snapshot} />
          </Panel>
        )}
      </div>
      {ready && load.state === "ready" && (
        <Panel title="Timeline" className={styles.timelinePanel}>
          <Timeline snapshot={snapshot} source={load.source} mainMetric={load.mainMetric} />
        </Panel>
      )}
      {ready && (
        <Panel title="Verdict" className={styles.timelinePanel}>
          <VerdictPanel snapshot={snapshot} />
        </Panel>
      )}
    </>
  );
}
