"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ApiError, createExperiment } from "@/lib/api";
import type { Experiment, RecipeSummary } from "@/lib/types";
import styles from "./NewExperimentDialog.module.css";

type Props = {
  open: boolean;
  recipes: RecipeSummary[];
  onClose: () => void;
  onCreated: (experiment: Experiment) => void;
};

const measured = (r: RecipeSummary) => r.main_measurement.replaceAll("_", " ");

// A native modal <dialog>: the browser traps focus, closes on Escape and hands focus back on close.
export function NewExperimentDialog({ open, recipes, onClose, onCreated }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const form = useRef<HTMLFormElement>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<{ message: string; onTitle?: boolean } | null>(null);

  useEffect(() => {
    const el = dialog.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const title = String(data.get("title") ?? "").trim();
    const recipeId = String(data.get("recipe") ?? "");
    if (!title) {
      setError({ message: "Give the experiment a name.", onTitle: true });
      return;
    }
    setPending(true);
    setError(null);
    try {
      onCreated(await createExperiment(title, recipeId));
      form.current?.reset();
      onClose();
    } catch (e) {
      setError({ message: e instanceof ApiError ? e.detail : "Something went wrong. Try again." });
    } finally {
      setPending(false);
    }
  }

  return (
    <dialog
      ref={dialog}
      className={styles.dialog}
      aria-labelledby="new-experiment-title"
      onClose={() => {
        setError(null);
        onClose();
      }}
    >
      <form ref={form} className={styles.form} onSubmit={submit} noValidate>
        <h2 id="new-experiment-title" className={styles.heading}>
          New experiment
        </h2>
        <p className={styles.lead}>Name it and pick the recipe closest to what you will watch.</p>

        <label className={styles.field}>
          <span className={styles.label}>Name</span>
          <input
            className={styles.input}
            name="title"
            maxLength={200}
            autoComplete="off"
            placeholder="Iodine clock timing"
            aria-invalid={error?.onTitle || undefined}
          />
        </label>

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

        {error && (
          <p className={styles.error} role="alert">
            {error.message}
          </p>
        )}

        <div className={styles.actions}>
          <Button variant="text" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" type="submit" disabled={pending}>
            {pending ? "Creating…" : "Create"}
          </Button>
        </div>
      </form>
    </dialog>
  );
}
