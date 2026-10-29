"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { ApiError, describe } from "@/lib/api";
import type { RecipeDetail, RecipeDraft } from "@/lib/types";
import styles from "./Step.module.css";

type Props = {
  experimentId: string;
  recipe: RecipeDetail;
  draft: RecipeDraft | null; // the last draft taken, if any
  onDraft: (draft: RecipeDraft) => void;
};

// "What are you testing?": Muse Spark drafts the plan, the factor and its conditions from the researcher's words.
// Nothing is saved until the later steps, where every field can be changed.
export function DescribeStep({ experimentId, recipe, draft, onDraft }: Props) {
  const [words, setWords] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <div className={styles.step}>
      <p className={styles.lead}>
        Say what you want to find out, in your own words. Argus drafts the hypothesis, the prediction and the conditions
        for a {recipe.title.toLowerCase()} experiment; you check every field in the later steps. You can also skip this
        and fill them in yourself.
      </p>
      <label className={styles.field}>
        <span className={styles.label}>What are you testing?</span>
        <textarea
          className={styles.textarea}
          value={words}
          onChange={(e) => setWords(e.target.value)}
          placeholder="Does food colouring spread faster in warm water than in cold water?"
          maxLength={4000}
        />
      </label>
      <div className={styles.row}>
        <Button
          variant="primary"
          disabled={busy || !words.trim()}
          onClick={() => {
            setBusy(true);
            setError(null);
            describe(experimentId, words.trim())
              .then(onDraft)
              .catch((e: unknown) => setError(e instanceof ApiError ? e.detail : "No draft this time."))
              .finally(() => setBusy(false));
          }}
        >
          {busy ? "Drafting…" : "Draft the plan"}
        </Button>
      </div>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      {draft && (
        <div className={styles.note} role="status">
          <p>
            <strong>Drafted:</strong> {draft.hypothesis}
          </p>
          <p>
            Factor: {draft.factor}
            {draft.factor_unit ? ` (${draft.factor_unit})` : ""} · conditions:{" "}
            {draft.conditions.map((c) => `${c.value} (${c.role})`).join(", ")} · metric {draft.metric}
          </p>
          {draft.question_for_researcher && <p>Argus asks: {draft.question_for_researcher}</p>}
        </div>
      )}
    </div>
  );
}
