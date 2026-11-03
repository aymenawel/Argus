"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ArgusLine } from "@/components/run/ArgusLine";
import { Readouts } from "@/components/run/Readouts";
import { RunFrame } from "@/components/run/RunFrame";
import { SidePanel } from "@/components/run/SidePanel";
import { Timeline } from "@/components/run/Timeline";
import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import { ApiError, errorText, getExperiment, getExperimentRecipeDetail, getRuns, stopRun } from "@/lib/api";
import { homeLink, resultsHref } from "@/lib/links";
import { playhead } from "@/lib/playhead";
import { runNotice } from "@/lib/run-data";
import { isReplay, useReadOnly } from "@/lib/replay";
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
  const count = `${analyzed.length} ${analyzed.length === 1 ? "picture" : "pictures"} measured`;
  const last = analyzed.at(-1)?.t ?? 0;
  if (view.running) {
    if (progress?.stage === "measure" && progress.t != null && progress.t_end != null) {
      return `Analyzing ${formatRunTime(progress.t, progress.t_end)} of ${formatRunTime(progress.t_end)} · ${progress.speed ?? 0}× real time`;
    }
    if (progress?.stage === "segment") return `Outlining with SAM 3.1 · ${progress.done} of ${progress.total} clips`;
    if (progress?.stage === "scan" && progress.t != null) {
      return `Reading the video · ${formatRunTime(progress.t)} so far · ${progress.speed ?? 0}× real time`;
    }
    return view.run.mode === "live" ? `Watching live · ${count}` : "Starting the import";
  }
  const source =
    view.run.mode === "live" ? "live camera" : view.run.source.provenance ? "published data" : "imported video";
  const samples = `${view.vessels.length} ${view.vessels.length === 1 ? "sample" : "samples"}`;
  const state = view.run.status === "finished" ? "Finished" : "Stopped";
  const recorded = isReplay() ? "Recorded run · nothing here is live · " : ""; // the demo says what it is (D-98)
  return `${recorded}${state} · ${source} · ${formatRunTime(last)} · ${samples}`;
}

/** `experimentId` is given by the replay's routes, whose URL names the run instead. */
export function RunScreen({ experimentId }: { experimentId?: string } = {}) {
  const params = useParams<{ id: string }>();
  const id = experimentId ?? params.id;
  const readOnly = useReadOnly();
  const home = homeLink();
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [snapshot, setSnapshot] = useState<RunSnapshot | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [stopping, setStopping] = useState(false);

  useEffect(() => {
    let live = true;
    let unsubscribe = () => {};
    Promise.all([getExperiment(id), getExperimentRecipeDetail(id), getRuns(id)])
      .then(([experiment, recipe, runs]) => {
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
        const mainMetric = recipe.main_measurement;
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
      <Link href={home.href}>{home.label}</Link>
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
            <p className={styles.messageTitle}>{errorText(load.error)}</p>
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
              Set up the samples and lock the plan first, then start the run from the setup.
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
              <Link className={styles.resultsLink} href={resultsHref(id, view.run.id)}>
                See results <span aria-hidden="true">→</span>
              </Link>
              {view.running && !readOnly && (
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
      {ready && load.state === "ready" && (
        <div className={styles.argus}>
          <ArgusLine snapshot={snapshot} mainMetric={load.mainMetric} />
        </div>
      )}
      <div className={styles.workspace}>
        <div className={styles.stage}>
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
          {ready && load.state === "ready" && (
            <Panel className={styles.panel}>
              <Timeline snapshot={snapshot} source={load.source} />
            </Panel>
          )}
        </div>
        {ready && (
          <Panel className={styles.feedPanel}>
            <SidePanel snapshot={snapshot} />
          </Panel>
        )}
      </div>
    </>
  );
}
