"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { CheckStep } from "@/components/setup/CheckStep";
import { DescribeStep } from "@/components/setup/DescribeStep";
import { PlanStep } from "@/components/setup/PlanStep";
import { RolesStep } from "@/components/setup/RolesStep";
import { SourceStep } from "@/components/setup/SourceStep";
import { StartStep } from "@/components/setup/StartStep";
import { STEP_NAMES, Stepper } from "@/components/setup/Stepper";
import { VesselsStep } from "@/components/setup/VesselsStep";
import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import {
  ApiError,
  apiBase,
  getExperiment,
  getExperimentRecipeDetail,
  getPlans,
  getRuns,
  getSetup,
  putPlan,
  putSetup,
} from "@/lib/api";
import { STEPS, stepProblems, type StepId, type WizardState } from "@/lib/setup";
import type { Experiment, FrameRequest, Plan, PlanDraft, Preview, RecipeDetail, RecipeDraft, Setup } from "@/lib/types";
import styles from "./page.module.css";

const EMPTY_PLAN: PlanDraft = {
  hypothesis: "",
  prediction: "",
  threshold: "",
  rivals: [],
  metric: null,
  direction: null,
  min_effect: null,
  checkpoint_s: null,
  treatment: null,
};

const SAVE_AFTER_MS = 500;

type Load =
  | { state: "loading" }
  | { state: "error"; error: ApiError }
  | { state: "ready"; experiment: Experiment; recipe: RecipeDetail; frozen: boolean };

function asDraft(plan: Plan): PlanDraft {
  const { hypothesis, prediction, threshold, rivals, metric, direction, min_effect, checkpoint_s, treatment } = plan;
  return { hypothesis, prediction, threshold, rivals, metric, direction, min_effect, checkpoint_s, treatment };
}

/** Saves `value` a moment after the researcher stops changing it; markChanged() tells an edit from a load. */
function useAutosave<T>(value: T | null, save: (value: T) => Promise<unknown>) {
  const changed = useRef(false);
  const latest = useRef(save);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    latest.current = save;
  });
  useEffect(() => {
    if (value === null || !changed.current) return;
    const timer = setTimeout(() => {
      changed.current = false;
      latest
        .current(value)
        .then(() => setError(null))
        .catch((e: unknown) => setError(e instanceof ApiError ? e.detail : "Not saved"))
        .finally(() => setSaving(false));
    }, SAVE_AFTER_MS);
    return () => clearTimeout(timer);
  }, [value]);
  const markChanged = useCallback(() => {
    changed.current = true;
    setSaving(true);
  }, []);
  return { markChanged, saving, error };
}

export function SetupScreen() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [setup, setSetup] = useState<Setup | null>(null);
  const [plan, setPlan] = useState<PlanDraft | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [draft, setDraft] = useState<RecipeDraft | null>(null);
  const [videoS, setVideoS] = useState(0);
  const [step, setStep] = useState<StepId>("describe");

  const setupSave = useAutosave(setup, (s: Setup) => putSetup(id, s));
  const planSave = useAutosave(plan, (p: PlanDraft) =>
    putPlan(id, p).then((saved) => setPlans((all) => [...all.filter((x) => x.version !== saved.version), saved])),
  );

  useEffect(() => {
    let live = true;
    Promise.all([getExperiment(id), getSetup(id), getPlans(id), getRuns(id)])
      .then(async ([experiment, saved, versions, runs]) => {
        const recipe = await getExperimentRecipeDetail(experiment.id); // its own recipe or a template
        if (!live) return;
        const firstLocked = versions.find((p) => p.locked_at !== null);
        setSetup(saved);
        setPlans(versions);
        setPlan(versions.length ? asDraft(versions[versions.length - 1]) : EMPTY_PLAN);
        const state: WizardState = {
          source: saved.source,
          vessels: saved.vessels,
          preview: null,
          plan: versions.length ? versions[versions.length - 1] : null,
        };
        // Resume at the first step that still needs something (the check is redone after a reload).
        const resume = saved.source === null ? "describe" : STEPS.slice(1).find((s) => stepProblems(s, state).length);
        setStep(resume ?? "start");
        setLoad({ state: "ready", experiment, recipe, frozen: firstLocked !== undefined && runs.length > 0 });
      })
      .catch((error: unknown) => {
        if (live)
          setLoad({ state: "error", error: error instanceof ApiError ? error : new ApiError(0, String(error)) });
      });
    return () => {
      live = false;
    };
  }, [id, attempt]);

  const title = load.state === "ready" ? load.experiment.title : "Set up";
  const crumb = (
    <>
      <Link href="/">Experiments</Link>
      <span className={styles.faint}>/</span>
      <span>{title}</span>
      <span className={styles.faint}>/</span>
      <span>Setup</span>
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

  if (load.state === "loading" || setup === null || plan === null) {
    return (
      <>
        <PageHeader crumb={crumb} title={title} />
        <Panel className={styles.panel}>
          <div className={styles.placeholder} aria-busy="true" />
        </Panel>
      </>
    );
  }

  const { experiment, recipe, frozen } = load;
  if (frozen) {
    return (
      <>
        <PageHeader crumb={crumb} title={title} />
        <Panel className={styles.panel}>
          <div className={styles.message}>
            <p className={styles.messageTitle}>This experiment&apos;s plan is locked and a run has started</p>
            <p className={styles.messageText}>The setup is fixed now, so the run can be judged against it.</p>
            <Button variant="primary" onClick={() => router.push(`/experiments/${id}/run`)}>
              Open the run
            </Button>
          </div>
        </Panel>
      </>
    );
  }

  const locked = plans.find((p) => p.locked_at !== null) ?? null;
  const state: WizardState = { source: setup.source, vessels: setup.vessels, preview, plan };
  const index = STEPS.indexOf(step);
  const problems = stepProblems(step, state);
  const firstBlocked = STEPS.findIndex((s) => stepProblems(s, state).length > 0);
  const reachable = (s: StepId) => firstBlocked < 0 || STEPS.indexOf(s) <= firstBlocked;
  const frame: FrameRequest =
    setup.source?.kind === "video"
      ? { path: setup.source.paths[0] ?? "", video_s: videoS }
      : { camera_index: setup.source?.camera_index ?? 0 };

  const changeSetup = (next: Setup) => {
    setupSave.markChanged();
    setSetup(next);
    if (next.vessels !== setup.vessels || next.ruler !== setup.ruler || next.print_check_mm !== setup.print_check_mm) {
      setPreview(null); // the check no longer shows this setup
    }
  };
  const changePlan = (next: PlanDraft) => {
    planSave.markChanged();
    setPlan(next);
  };
  const saving = setupSave.saving || planSave.saving;
  const saveError = setupSave.error ?? planSave.error;

  return (
    <>
      <PageHeader
        crumb={crumb}
        title={title}
        finding={`${recipe.title} · ${saveError ? `Not saved: ${saveError}` : saving ? "Saving…" : "Saved"}`}
      />
      <div className={styles.stepper}>
        <Stepper
          steps={STEPS}
          current={step}
          reachable={reachable}
          done={(s) => stepProblems(s, state).length === 0}
          onPick={setStep}
        />
      </div>
      <Panel title={STEP_NAMES[step]} className={styles.panel}>
        {step === "describe" && (
          <DescribeStep
            experimentId={experiment.id}
            recipe={recipe}
            draft={draft}
            onDraft={(d) => {
              setDraft(d);
              changePlan({
                hypothesis: d.hypothesis,
                prediction: d.prediction,
                threshold: d.threshold,
                rivals: d.rivals,
                metric: d.metric,
                direction: d.direction,
                min_effect: d.min_effect,
                checkpoint_s: d.checkpoint_s,
                treatment: d.treatment || null,
              });
              changeSetup({ ...setup, factor: d.factor || null, factor_unit: d.factor_unit || null });
            }}
          />
        )}
        {step === "source" && <SourceStep setup={setup} onChange={changeSetup} videoS={videoS} onVideoS={setVideoS} />}
        {step === "vessels" && (
          <VesselsStep
            experimentId={experiment.id}
            recipe={recipe}
            frame={frame}
            vessels={setup.vessels}
            onChange={(vessels) => changeSetup({ ...setup, vessels })}
          />
        )}
        {step === "roles" && (
          <RolesStep setup={setup} suggestions={draft?.conditions.map((c) => c.value) ?? []} onChange={changeSetup} />
        )}
        {step === "check" && (
          <CheckStep
            experimentId={experiment.id}
            setup={setup}
            frame={frame}
            preview={preview}
            onPreview={setPreview}
            onChange={changeSetup}
          />
        )}
        {step === "plan" && (
          <PlanStep plan={plan} locked={locked} recipe={recipe} setup={setup} onChange={changePlan} />
        )}
        {step === "start" && (
          <StartStep
            experimentId={experiment.id}
            setup={setup}
            plan={plan}
            locked={locked}
            saving={saving}
            unit={recipe.metrics.find((m) => m.id === plan.metric)?.unit ?? ""}
            onLocked={(p) => setPlans((all) => all.map((x) => (x.version === p.version ? p : x)))}
            onStarted={() => router.push(`/experiments/${id}/run`)}
          />
        )}

        <div className={styles.nav}>
          <Button disabled={index === 0} onClick={() => setStep(STEPS[index - 1])}>
            Back
          </Button>
          {step !== "start" && (
            <Button
              variant="primary"
              disabled={problems.length > 0}
              onClick={() => setStep(STEPS[index + 1])}
              aria-describedby={problems.length ? "step-problems" : undefined}
            >
              {step === "describe" && plan.hypothesis === "" ? "Skip" : "Next"}
            </Button>
          )}
          {problems.length > 0 && (
            <ul id="step-problems" className={styles.problems}>
              {problems.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          )}
        </div>
      </Panel>
    </>
  );
}
