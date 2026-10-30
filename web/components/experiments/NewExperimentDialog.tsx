"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ApiError, createExperiment, draftRecipe, getSetup, getToolbox, putSetup } from "@/lib/api";
import type { Experiment, RecipeDraftResult, RecipeSummary, Tool } from "@/lib/types";
import { RecipeDraftView } from "./RecipeDraftView";
import styles from "./NewExperimentDialog.module.css";

type Props = {
  open: boolean;
  recipes: RecipeSummary[];
  onClose: () => void;
  onCreated: (experiment: Experiment) => void;
};

type Problem = { message: string; onTitle?: boolean; refused?: boolean };

const measured = (r: RecipeSummary) => r.main_measurement.replaceAll("_", " ");

const EXAMPLE = "I'll compare how fast rye and pearl millet seeds germinate in petri dishes";

// A native modal <dialog>: the browser traps focus, closes on Escape and hands focus back on close.
// The researcher says what they will do and Argus drafts the recipe (D-73); the templates are one click away.
export function NewExperimentDialog({ open, recipes, onClose, onCreated }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [mode, setMode] = useState<"words" | "template">("words");
  const [title, setTitle] = useState("");
  const [words, setWords] = useState("");
  const [draft, setDraft] = useState<RecipeDraftResult | null>(null);
  const [toolbox, setToolbox] = useState<Tool[]>([]);
  const [drafting, setDrafting] = useState(false);
  const [pending, setPending] = useState(false);
  const [problem, setProblem] = useState<Problem | null>(null);

  useEffect(() => {
    const el = dialog.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);

  useEffect(() => {
    if (open && toolbox.length === 0) getToolbox().then(setToolbox, () => undefined);
  }, [open, toolbox.length]);

  function reset() {
    setMode("words");
    setTitle("");
    setWords("");
    setDraft(null);
    setProblem(null);
  }

  async function draftIt() {
    setDrafting(true);
    setProblem(null);
    try {
      const result = await draftRecipe(words.trim());
      setDraft(result);
      if (!title.trim()) setTitle(result.recipe.title);
    } catch (e) {
      const refused = e instanceof ApiError && e.status === 422;
      const message =
        e instanceof ApiError
          ? refused
            ? `Argus couldn't turn that into a recipe it can run: ${e.detail}`
            : e.detail
          : "No draft this time. Try again.";
      setProblem({ message, refused: refused || (e instanceof ApiError && e.status === 503) });
    } finally {
      setDrafting(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = title.trim();
    const recipeId = String(new FormData(event.currentTarget).get("recipe") ?? "");
    if (!name) {
      setProblem({ message: "Give the experiment a name.", onTitle: true });
      return;
    }
    if (mode === "words" && !draft) {
      if (words.trim()) return draftIt();
      return setProblem({ message: "Say what you will do, and Argus drafts the recipe." });
    }
    setPending(true);
    setProblem(null);
    try {
      const experiment = await createExperiment(
        name,
        mode === "words" && draft ? { recipe: draft.recipe, plan: draft.plan } : recipeId,
      );
      if (mode === "words" && draft?.setup_hints.factor) {
        // The factor Argus drafted goes to the setup; the researcher assigns conditions to dishes in the wizard.
        const setup = await getSetup(experiment.id);
        const { factor, factor_unit } = draft.setup_hints;
        await putSetup(experiment.id, { ...setup, factor, factor_unit: factor_unit || null }).catch(() => undefined);
      }
      onCreated(experiment);
      reset();
      onClose();
    } catch (e) {
      setProblem({ message: e instanceof ApiError ? e.detail : "Something went wrong. Try again." });
    } finally {
      setPending(false);
    }
  }

  const wide = mode === "words" && draft !== null;

  return (
    <dialog
      ref={dialog}
      className={`${styles.dialog} ${wide ? styles.wide : ""}`}
      aria-labelledby="new-experiment-title"
      onClose={() => {
        setProblem(null);
        onClose();
      }}
    >
      <form className={styles.form} onSubmit={submit} noValidate>
        <h2 id="new-experiment-title" className={styles.heading}>
          New experiment
        </h2>
        <p className={styles.lead}>
          {mode === "words"
            ? "Say what you will do. Argus drafts what to look for, what to measure and how often; you can change any of it."
            : "Name it and pick the recipe closest to what you will watch."}
        </p>

        <label className={styles.field}>
          <span className={styles.label}>Name</span>
          <input
            className={styles.input}
            name="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={200}
            autoComplete="off"
            placeholder={mode === "words" ? "Rye vs pearl millet germination" : "Iodine clock timing"}
            aria-invalid={problem?.onTitle || undefined}
          />
        </label>

        {mode === "words" ? (
          <>
            <label className={styles.field}>
              <span className={styles.label}>What will you do?</span>
              <textarea
                className={styles.textarea}
                value={words}
                onChange={(e) => {
                  setWords(e.target.value);
                  if (draft) setDraft(null); // a draft belongs to the words it was made from
                }}
                maxLength={4000}
                placeholder={EXAMPLE}
              />
            </label>
            {draft && <RecipeDraftView draft={draft} toolbox={toolbox} onChange={setDraft} />}
          </>
        ) : (
          <label className={styles.field}>
            <span className={styles.label}>Recipe</span>
            <select className={styles.input} name="recipe" required>
              {recipes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.title} · measures {measured(r)}
                </option>
              ))}
            </select>
          </label>
        )}

        {problem && (
          <div className={styles.error} role="alert">
            <p>{problem.message}</p>
            {problem.refused && mode === "words" && (
              <Button
                variant="secondary"
                onClick={() => {
                  setMode("template");
                  setProblem(null);
                }}
              >
                Pick a template instead
              </Button>
            )}
          </div>
        )}

        <div className={styles.actions}>
          {!(problem?.refused && mode === "words") && (
            <Button
              variant="text"
              className={styles.switch}
              onClick={() => {
                setMode(mode === "words" ? "template" : "words");
                setProblem(null);
              }}
            >
              {mode === "words" ? "Pick a template instead" : "Describe it instead"}
            </Button>
          )}
          <Button variant="text" onClick={onClose}>
            Cancel
          </Button>
          {mode === "words" && draft && (
            <Button variant="secondary" onClick={draftIt} disabled={drafting || pending}>
              {drafting ? "Drafting…" : "Draft again"}
            </Button>
          )}
          {mode === "words" && !draft ? (
            <Button variant="primary" onClick={draftIt} disabled={drafting || !words.trim()}>
              {drafting ? "Drafting… (up to a minute)" : "Draft it"}
            </Button>
          ) : (
            <Button variant="primary" type="submit" disabled={pending || drafting}>
              {pending ? "Creating…" : "Create"}
            </Button>
          )}
        </div>
      </form>
    </dialog>
  );
}
