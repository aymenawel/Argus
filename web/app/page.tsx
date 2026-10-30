"use client";

import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";
import { ExperimentsTable, ExperimentsTableSkeleton } from "@/components/experiments/ExperimentsTable";
import { NewExperimentDialog } from "@/components/experiments/NewExperimentDialog";
import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import { ApiError, apiBase, getExperiments, getRecipes } from "@/lib/api";
import { subscribe } from "@/lib/events";
import type { Experiment, ExperimentStatus, RecipeSummary } from "@/lib/types";
import styles from "./page.module.css";

type Load = { state: "loading" } | { state: "ready" } | { state: "error"; error: ApiError };

const newestFirst = (a: Experiment, b: Experiment) => b.created_at.localeCompare(a.created_at);

// Rows can arrive from the list, from the event stream and from our own POST; the id decides.
function merge(current: Experiment[], incoming: Experiment[]): Experiment[] {
  const byId = new Map(current.map((e) => [e.id, e]));
  for (const e of incoming) byId.set(e.id, e);
  return [...byId.values()].sort(newestFirst);
}

const STATUS_WORDS: [ExperimentStatus, string][] = [
  ["running", "running"],
  ["draft", "being set up"],
  ["locked", "locked and ready"],
  ["finished", "finished"],
];

function finding(experiments: Experiment[]): ReactNode {
  const n = experiments.length;
  const parts = STATUS_WORDS.flatMap(([status, words]) => {
    const count = experiments.filter((e) => e.status === status).length;
    return count ? [`${count} ${words}`] : [];
  });
  return (
    <>
      {n} {n === 1 ? "experiment" : "experiments"}: {parts.join(", ")}. Newest is <b>{experiments[0].title}</b>.
    </>
  );
}

export default function ExperimentsPage() {
  const router = useRouter();
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [recipes, setRecipes] = useState<RecipeSummary[]>([]);
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    let live = true;
    // Listen before fetching, so a row created in between is not lost.
    const unsubscribe = subscribe((type, data) => {
      if (type === "experiment") setExperiments((current) => merge(current, [data as Experiment]));
      if (type === "resync") {
        // The worker restarted or we missed too much: reload the list (if that fails, it stays as shown).
        getExperiments()
          .then((list) => live && setExperiments((current) => merge(current, list)))
          .catch(() => undefined);
      }
    });
    Promise.all([getExperiments(), getRecipes()])
      .then(([list, recipeList]) => {
        if (!live) return;
        setExperiments((current) => merge(current, list));
        setRecipes(recipeList);
        setLoad({ state: "ready" });
      })
      .catch((error: unknown) => {
        unsubscribe();
        if (!live) return;
        setLoad({ state: "error", error: error instanceof ApiError ? error : new ApiError(0, String(error)) });
      });
    return () => {
      live = false;
      unsubscribe();
    };
  }, [attempt]);

  const retry = () => {
    setLoad({ state: "loading" });
    setAttempt((a) => a + 1);
  };

  const ready = load.state === "ready";
  const empty = ready && experiments.length === 0;
  const newButton = (
    <Button variant="primary" onClick={() => setDialogOpen(true)}>
      New experiment
    </Button>
  );

  return (
    <>
      <PageHeader
        crumb="Argus Labs"
        title="Experiments"
        finding={ready && !empty ? finding(experiments) : undefined}
        actions={ready && !empty ? newButton : undefined}
      />

      <Panel className={styles.panel}>
        {load.state === "loading" && <ExperimentsTableSkeleton />}

        {load.state === "error" && (
          <div className={styles.message} role="alert">
            <p className={styles.messageTitle}>
              {load.error.status === 0
                ? `Couldn't reach the Argus worker at ${apiBase()}.`
                : `The Argus worker answered ${load.error.status}: ${load.error.detail}`}
            </p>
            {load.error.status === 0 && (
              <p className={styles.messageText}>
                Start it with <code className={styles.code}>uv run python -m argus dev</code>
              </p>
            )}
            <Button onClick={retry}>Retry</Button>
          </div>
        )}

        {empty && (
          <div className={styles.message}>
            <p className={styles.messageTitle}>No experiments yet</p>
            <p className={styles.messageText}>
              Say what you will do and Argus drafts the recipe, or start from a template.
            </p>
            {newButton}
          </div>
        )}

        {ready && !empty && <ExperimentsTable experiments={experiments} recipes={recipes} />}
      </Panel>

      <NewExperimentDialog
        open={dialogOpen}
        recipes={recipes}
        onClose={() => setDialogOpen(false)}
        onCreated={(experiment) => {
          setExperiments((current) => merge(current, [experiment]));
          router.push(`/experiments/${experiment.id}/setup`); // a new experiment starts with its setup
        }}
      />
    </>
  );
}
