"use client";

import { useEffect, useState } from "react";
import { ApiError, apiBase, getReasoningPreference, putReasoningPreference } from "@/lib/api";
import { modelName } from "@/lib/models";
import type { ReasoningOption, ReasoningPreference } from "@/lib/types";
import styles from "./ModelChoice.module.css";

const MISSING_KEY: Record<ReasoningOption["id"], string> = {
  meta: "Add MODEL_API_KEY to .env and restart the worker.",
  baseten: "Add BASETEN_API_KEY to .env and restart the worker.",
};

// Where Argus's everyday model calls run (D-77). The next call follows the choice; verdicts and segmentation stay
// on Meta's API whatever is chosen. Keys stay in the worker's .env: this only picks which one is used.
export function ModelChoice() {
  const [pref, setPref] = useState<ReasoningPreference | null>(null);
  const [saving, setSaving] = useState<ReasoningOption["id"] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    getReasoningPreference()
      .then((p) => live && setPref(p))
      .catch((e: unknown) =>
        setError(e instanceof ApiError && e.status ? e.detail : `Couldn't reach the Argus worker at ${apiBase()}.`),
      );
    return () => {
      live = false;
    };
  }, []);

  const choose = (id: ReasoningOption["id"]) => {
    if (!pref || id === pref.provider) return;
    setSaving(id);
    setError(null);
    putReasoningPreference(id)
      .then(setPref)
      .catch((e: unknown) => setError(e instanceof ApiError ? e.detail : "The choice wasn't saved."))
      .finally(() => setSaving(null));
  };

  if (!pref) {
    return error ? (
      <p className={styles.error} role="alert">
        {error}
      </p>
    ) : (
      <div className={styles.skeleton} aria-busy="true" />
    );
  }

  return (
    <div className={styles.choice}>
      <div className={styles.options} role="radiogroup" aria-label="Everyday model">
        {pref.options.map((option) => {
          const on = option.id === pref.provider;
          return (
            <button
              key={option.id}
              type="button"
              role="radio"
              aria-checked={on}
              aria-label={`${modelName(option.model)} on ${option.label}${option.open_weight ? " (open weights)" : ""}`}
              disabled={!option.available || saving !== null}
              className={`${styles.option} ${on ? styles.on : ""}`}
              onClick={() => choose(option.id)}
            >
              <span className={styles.row}>
                <span className={styles.radio} aria-hidden="true" />
                <span className={styles.name}>{modelName(option.model)}</span>
                {option.open_weight && <span className={styles.tag}>Open weights</span>}
              </span>
              <span className={styles.where}>
                {option.label} · <code>{option.model}</code>
              </span>
              {!option.available && <span className={styles.missing}>{MISSING_KEY[option.id]}</span>}
              {saving === option.id && <span className={styles.where}>Switching…</span>}
            </button>
          );
        })}
      </div>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      <p className={styles.note}>
        Used for drafting a recipe from your words, the notes during a run and plan drafts. The next call follows your
        choice, with no restart. If Baseten fails, that call falls back to {modelName(pref.options[0].model)} on
        Meta&apos;s API, and every note says which model wrote it.
      </p>
      <p className={styles.note}>
        Always on Meta&apos;s API: verdicts with {modelName(pref.fixed.verdicts)}, segmentation with{" "}
        {modelName(pref.fixed.segmentation)}.
      </p>
    </div>
  );
}
