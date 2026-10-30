"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { CurveChart } from "@/components/results/CurveChart";
import { FitTable } from "@/components/results/FitTable";
import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import { VerdictChip } from "@/components/ui/VerdictChip";
import { AgreementTable } from "@/components/verdict/AgreementTable";
import { VerdictChecks, judgedPlan } from "@/components/verdict/VerdictPanel";
import {
  ApiError,
  apiBase,
  getExperiment,
  getExperimentRecipeDetail,
  getFits,
  getPlans,
  getRuns,
  getVerdict,
} from "@/lib/api";
import type { Experiment, FitsView, Plan, RecipeDetail, RunView, Verdict } from "@/lib/types";
import styles from "./page.module.css";

type Load =
  | { state: "loading" }
  | { state: "error"; error: ApiError }
  | { state: "empty"; experiment: Experiment }
  | { state: "ready"; experiment: Experiment; recipe: RecipeDetail; runs: RunView[]; plans: Plan[] };

const JUDGED_ON: Record<FitsView["quantity"], string> = {
  level: "the level at the checkpoint",
  half_time: "the half-way time",
  rate: "the rate",
};

const words = (id: string) => id.replaceAll("_", " ");
const sentence = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

const asApiError = (error: unknown) => (error instanceof ApiError ? error : new ApiError(0, String(error)));

function runLabel(view: RunView, number: number): string {
  const day = new Date(view.run.started_at).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  return `Run ${number} · ${day}${view.run.source.provenance ? " · published data" : ""}`;
}

function finding(fits: FitsView): string {
  const fitted = fits.vessels.filter((v) => v.fit?.ok).length;
  return `${fitted} of ${fits.vessels.length} vessels follow a ${fits.curve} curve · judged on ${JUDGED_ON[fits.quantity]}`;
}

// One run's results in one place (phase 4): each vessel's readings with its fitted curve, the half-way times and
// rates with ±, and the verdict. Every number is the worker's; the page only draws and rounds.
export function ResultsScreen() {
  const { id } = useParams<{ id: string }>();
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [runId, setRunId] = useState<string | null>(null);
  const [metric, setMetric] = useState<string | null>(null); // null: the plan's metric
  // Each answer is kept with what it answered, so a stale one never shows for the run or metric picked since.
  const [fitsLoad, setFitsLoad] = useState<{ key: string; fits?: FitsView; error?: string } | null>(null);
  const [verdictLoad, setVerdictLoad] = useState<{ runId: string; verdict: Verdict | null } | null>(null);
  const fitsKey = `${runId}|${metric ?? ""}`;
  const fits = fitsLoad?.key === fitsKey ? (fitsLoad.fits ?? null) : null;
  const fitsError = fitsLoad?.key === fitsKey ? (fitsLoad.error ?? null) : null;
  const verdict = verdictLoad?.runId === runId ? verdictLoad.verdict : undefined;

  useEffect(() => {
    let live = true;
    Promise.all([getExperiment(id), getExperimentRecipeDetail(id), getRuns(id), getPlans(id)])
      .then(([experiment, recipe, runs, plans]) => {
        if (!live) return;
        if (runs.length === 0) {
          setLoad({ state: "empty", experiment });
          return;
        }
        setRunId(runs[0].run.id);
        setLoad({ state: "ready", experiment, recipe, runs, plans });
      })
      .catch((error: unknown) => live && setLoad({ state: "error", error: asApiError(error) }));
    return () => {
      live = false;
    };
  }, [id, attempt]);

  useEffect(() => {
    if (!runId) return;
    let live = true;
    const key = `${runId}|${metric ?? ""}`;
    getFits(runId, metric ?? undefined)
      .then((f) => live && setFitsLoad({ key, fits: f }))
      .catch((error: unknown) => live && setFitsLoad({ key, error: asApiError(error).detail }));
    return () => {
      live = false;
    };
  }, [runId, metric]);

  useEffect(() => {
    if (!runId) return;
    let live = true;
    getVerdict(runId)
      .then((v) => live && setVerdictLoad({ runId, verdict: v }))
      .catch(() => live && setVerdictLoad({ runId, verdict: null }));
    return () => {
      live = false;
    };
  }, [runId]);

  const title = load.state === "ready" || load.state === "empty" ? load.experiment.title : "Results";
  const crumb = (
    <>
      <Link href="/">Experiments</Link>
      <span className={styles.faint}>/</span>
      <Link href={`/experiments/${id}/run`}>{title}</Link>
      <span className={styles.faint}>/</span>
      <span>Results</span>
    </>
  );

  if (load.state === "loading") {
    return (
      <>
        <PageHeader crumb={crumb} title={title} />
        <div className={styles.placeholder} aria-busy="true" />
      </>
    );
  }

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
            <p className={styles.messageTitle}>No results yet</p>
            <p className={styles.messageText}>
              Results appear once a run has readings. Set up the vessels, lock the plan and start a run first.
            </p>
            <Link className={styles.setupLink} href={`/experiments/${id}/setup`}>
              Open the setup
            </Link>
          </div>
        </Panel>
      </>
    );
  }

  const { runs, plans, recipe } = load;
  const index = Math.max(
    0,
    runs.findIndex((r) => r.run.id === runId),
  );
  const view = runs[index];
  const plan = judgedPlan(plans, view.run.started_at);
  const anyFit = fits?.vessels.some((v) => v.fit?.ok) ?? false;
  const reasons = [...new Set(fits?.vessels.map((v) => v.fit?.reason).filter((r): r is string => !!r) ?? [])];

  const pickers = (
    <span className={styles.pickers}>
      {runs.length > 1 && (
        <select
          className={styles.picker}
          aria-label="Run"
          value={view.run.id}
          onChange={(e) => setRunId(e.target.value)}
        >
          {runs.map((r, i) => (
            <option key={r.run.id} value={r.run.id}>
              {runLabel(r, runs.length - i)}
            </option>
          ))}
        </select>
      )}
      {recipe.metrics.length > 1 && (
        <select
          className={styles.picker}
          aria-label="Measurement"
          value={fits?.metric ?? metric ?? ""}
          onChange={(e) => setMetric(e.target.value)}
        >
          {recipe.metrics.map((m) => (
            <option key={m.id} value={m.id}>
              {words(m.id)}
            </option>
          ))}
        </select>
      )}
    </span>
  );

  return (
    <>
      <PageHeader crumb={crumb} title={title} finding={fits ? finding(fits) : runLabel(view, runs.length - index)} />

      <Panel title="Curves" meta={pickers} className={styles.panel}>
        {fitsError ? (
          <p className={styles.refused} role="alert">
            {fitsError}
          </p>
        ) : !fits ? (
          <div className={styles.placeholder} aria-busy="true" />
        ) : (
          <>
            <p className={styles.lead}>
              {sentence(fits.unit === "count" ? words(fits.metric) : `${words(fits.metric)} in ${fits.unit}`)} per
              vessel, with each vessel&apos;s fitted {fits.curve} curve. Only this run&apos;s readings are shown: runs
              are never pooled.
            </p>
            {!anyFit && fits.vessels.some((v) => v.readings.length > 0) && (
              <p className={styles.refused} role="status">
                No vessel&apos;s readings follow a {fits.curve} curve yet
                {reasons.length > 0 ? ` (${reasons.join("; ")})` : ""}, so there is no half-way time or rate to compare.
              </p>
            )}
            <CurveChart fits={fits} checkpointS={plan?.checkpoint_s} />
          </>
        )}
      </Panel>

      {fits && (
        <Panel title="Fitted values" className={styles.panel}>
          <FitTable fits={fits} />
        </Panel>
      )}

      <Panel title="Verdict" className={styles.panel}>
        {verdict === undefined ? (
          <p className={styles.none}>Reading the verdict…</p>
        ) : verdict === null ? (
          <p className={styles.none}>
            No verdict on this run yet.{" "}
            <Link className={styles.inlineLink} href={`/experiments/${id}/run`}>
              Ask for one on the run page
            </Link>
            {plan ? "." : ", after locking a plan before the run."}
          </p>
        ) : (
          <>
            <div className={styles.verdictTop}>
              <VerdictChip
                level={verdict.verdict}
                provisional={verdict.provisional}
                retrospective={verdict.body.retrospective ?? false}
              />
            </div>
            <VerdictChecks verdict={verdict} />
            {verdict.body.explanation && <p className={styles.explanation}>{verdict.body.explanation}</p>}
          </>
        )}
        {view.run.source.provenance && plan?.metric && (
          <AgreementTable runId={view.run.id} metric={plan.metric} refresh={view.run.id} />
        )}
      </Panel>
    </>
  );
}
