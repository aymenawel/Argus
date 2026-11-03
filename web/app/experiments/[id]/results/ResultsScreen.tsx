"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { CurveChart } from "@/components/results/CurveChart";
import { FitTable } from "@/components/results/FitTable";
import { NextRunCard } from "@/components/results/NextRunCard";
import { VideosCard } from "@/components/results/VideosCard";
import { ArgusSays, firstSentence } from "@/components/run/ArgusLine";
import { Credit } from "@/components/run/RunFrame";
import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import { AgreementTable } from "@/components/verdict/AgreementTable";
import { VerdictChecks, judgedPlan } from "@/components/verdict/VerdictPanel";
import {
  ApiError,
  errorText,
  getExperiment,
  getExperimentRecipeDetail,
  getFits,
  getPlans,
  getRuns,
  getVerdict,
} from "@/lib/api";
import { homeLink, runHref } from "@/lib/links";
import { isReplay, useReadOnly } from "@/lib/replay";
import { explanationToShow } from "@/lib/results";
import { checkCounts } from "@/lib/summary";
import type { Experiment, FitsView, Plan, RecipeDetail, RunView, Verdict } from "@/lib/types";
import styles from "./page.module.css";
import { curveWords, metricWords, sentence, unitKey, unitLabel } from "@/lib/plain";

type Load =
  | { state: "loading" }
  | { state: "error"; error: ApiError }
  | { state: "empty"; experiment: Experiment }
  | { state: "ready"; experiment: Experiment; recipe: RecipeDetail; runs: RunView[]; plans: Plan[] };

const JUDGED_ON: Record<FitsView["quantity"], string> = {
  level: "how much it changed by the check time",
  half_time: "how long it took to get half-way",
  rate: "how fast it changed",
};

const words = metricWords;

const asApiError = (error: unknown) => (error instanceof ApiError ? error : new ApiError(0, String(error)));

function runLabel(view: RunView, number: number): string {
  const day = new Date(view.run.started_at).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  return `Run ${number} · ${day}${view.run.source.provenance ? " · published data" : ""}`;
}

function finding(fits: FitsView): string {
  const fitted = fits.vessels.filter((v) => v.fit?.ok).length;
  return `${fitted} of ${fits.vessels.length} samples follow an ${curveWords(fits.curve)} curve · judged on ${JUDGED_ON[fits.quantity]}`;
}

// One run's results in one place (phase 4): each vessel's readings with its fitted curve, the half-way times and
// rates with ±, and the verdict. Every number is the worker's; the page only draws and rounds.
/** `experimentId` is given by the replay's routes, whose URL names the run instead. */
export function ResultsScreen({ experimentId }: { experimentId?: string } = {}) {
  const params = useParams<{ id: string }>();
  const id = experimentId ?? params.id;
  const readOnly = useReadOnly();
  const home = homeLink();
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
      <Link href={home.href}>{home.label}</Link>
      <span className={styles.faint}>/</span>
      <Link href={runId ? runHref(id, runId) : `/experiments/${id}/run`}>{title}</Link>
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

  const status = `${isReplay() ? "Recorded run · nothing here is live · " : ""}${runLabel(view, runs.length - index)}`;
  const says = verdict
    ? firstSentence(verdict.body.explanation || verdict.checks.find((c) => c.ok === false)?.text || "")
    : verdict === null
      ? "No verdict on this run yet."
      : "Reading the verdict…";

  return (
    <>
      <PageHeader
        crumb={crumb}
        title={title}
        finding={status}
        actions={
          <Link className={styles.backLink} href={runHref(id, view.run.id)}>
            <span aria-hidden="true">←</span> Back to the run
          </Link>
        }
      />

      <div className={styles.argus}>
        <ArgusSays
          lead={says}
          detail={fits ? finding(fits) : null}
          level={verdict?.verdict ?? null}
          provisional={verdict?.provisional}
          retrospective={Boolean(verdict?.body.retrospective)}
        />
        {view.run.source.provenance && <Credit provenance={view.run.source.provenance} />}
      </div>

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
              {sentence(fits.unit === "count" ? words(fits.metric) : `${words(fits.metric)} (${unitLabel(fits.unit)})`)}{" "}
              for each sample, with the {curveWords(fits.curve)} curve that best fits its readings.
              {unitKey(fits.unit) && <> {unitKey(fits.unit)}</>}
            </p>
            {!anyFit && fits.vessels.some((v) => v.readings.length > 0) && (
              <p className={styles.refused} role="status">
                No sample&apos;s readings follow an {curveWords(fits.curve)} curve yet
                {reasons.length > 0 ? ` (${reasons.join("; ")})` : ""}, so there is no half-way time or speed to
                compare.
              </p>
            )}
            <CurveChart fits={fits} checkpointS={plan?.checkpoint_s} />
          </>
        )}
      </Panel>

      <div className={styles.pair}>
        <Panel title="What Argus checked" className={styles.panel}>
          {verdict === undefined ? (
            <p className={styles.none}>Reading the verdict…</p>
          ) : verdict === null && readOnly ? (
            <p className={styles.none}>No verdict was asked for this run.</p>
          ) : verdict === null ? (
            <p className={styles.none}>
              No verdict on this run yet.{" "}
              <Link className={styles.inlineLink} href={`/experiments/${id}/run`}>
                Ask for one on the run page
              </Link>
              {plan ? "." : ", after locking a plan before the run."}
            </p>
          ) : (
            // A few checks read at once; a long list folds to its count (D-98).
            <details className={styles.fold} open={verdict.checks.length <= 3}>
              <summary>
                <span className="num">{checkCounts(verdict.checks)}</span>
                <span className={styles.foldHint}>Show the checks</span>
              </summary>
              <div className={styles.foldBody}>
                <VerdictChecks verdict={verdict} />
                {explanationToShow(verdict) && <p className={styles.explanation}>{verdict.body.explanation}</p>}
              </div>
            </details>
          )}
        </Panel>

        <Panel title="Next run" className={styles.panel}>
          <NextRunCard runId={view.run.id} running={view.running} />
        </Panel>
      </div>

      {fits && (
        <Panel title="Numbers" className={styles.panel}>
          <details className={styles.fold}>
            <summary>
              <span>Each sample&apos;s fitted curve, with its ±</span>
              <span className={styles.foldHint}>Show the numbers</span>
            </summary>
            <div className={styles.foldBody}>
              <FitTable fits={fits} />
              {view.run.source.provenance && plan?.metric && (
                <AgreementTable runId={view.run.id} metric={plan.metric} refresh={view.run.id} />
              )}
            </div>
          </details>
        </Panel>
      )}

      <Panel title="Videos" className={styles.panel}>
        <VideosCard runId={view.run.id} />
      </Panel>
    </>
  );
}
