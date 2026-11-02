"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { quantityUnit } from "@/lib/recipe";
import type { Plan, PlanDraft, RecipeDetail, Setup } from "@/lib/types";
import styles from "./Step.module.css";
import { metricWords, sentence, unitLabel } from "@/lib/plain";

type Props = {
  plan: PlanDraft;
  locked: Plan | null; // the first locked version, if any
  recipe: RecipeDetail;
  setup: Setup;
  onChange: (plan: PlanDraft) => void;
};

function toClock(s: number | null): string {
  if (s === null) return "";
  return `${Math.floor(s / 3600)}:${String(Math.floor((s % 3600) / 60)).padStart(2, "0")}`;
}

function fromClock(text: string): number | null {
  const match = /^(\d+):([0-5]?\d)$/.exec(text.trim());
  return match ? Number(match[1]) * 3600 + Number(match[2]) * 60 : null;
}

// The hypothesis in words, then the structured prediction the verdict is judged against (spec §7.3).
export function PlanStep({ plan, locked, recipe, setup, onChange }: Props) {
  const [checkpoint, setCheckpoint] = useState(toClock(plan.checkpoint_s));
  const [rival, setRival] = useState("");
  const set = (next: Partial<PlanDraft>) => onChange({ ...plan, ...next });
  const unit = quantityUnit(plan.quantity, recipe.metrics.find((m) => m.id === plan.metric)?.unit ?? "");
  const treatments = [
    ...new Set(
      setup.vessels.filter((v) => v.role === "treatment" && v.condition).map((v) => String(v.condition!.value)),
    ),
  ];
  const rivals = [...new Set([...recipe.rivals, ...plan.rivals])];

  return (
    <div className={styles.step}>
      {locked && (
        <p className={styles.note}>
          Version {locked.version} was locked; edits here make a new version, and the verdict keeps judging against
          version {locked.version}.
        </p>
      )}
      <label className={styles.field}>
        <span className={styles.label}>Your idea (hypothesis)</span>
        <textarea
          className={styles.textarea}
          value={plan.hypothesis}
          onChange={(e) => set({ hypothesis: e.target.value })}
          placeholder="Food colouring spreads faster in warm water than in cold water."
        />
      </label>
      <div className={styles.grid}>
        <label className={styles.field}>
          <span className={styles.label}>What you expect to see (prediction)</span>
          <input
            className={styles.input}
            value={plan.prediction}
            onChange={(e) => set({ prediction: e.target.value })}
          />
        </label>
        <label className={styles.field}>
          <span className={styles.label}>What counts as success</span>
          <input className={styles.input} value={plan.threshold} onChange={(e) => set({ threshold: e.target.value })} />
        </label>
      </div>

      <h3 className={styles.label}>How Argus will check it</h3>
      <div className={styles.grid}>
        <label className={styles.field}>
          <span className={styles.label}>What to measure</span>
          <select
            className={styles.select}
            value={plan.metric ?? ""}
            onChange={(e) => set({ metric: e.target.value || null })}
          >
            <option value="">Choose…</option>
            {recipe.metrics.map((m) => (
              <option key={m.id} value={m.id}>
                {sentence(metricWords(m.id))} ({unitLabel(m.unit)})
              </option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          <span className={styles.label}>Compare</span>
          <select
            className={styles.select}
            value={plan.quantity ?? "level"}
            onChange={(e) =>
              set({ quantity: e.target.value === "level" ? null : (e.target.value as PlanDraft["quantity"]) })
            }
          >
            <option value="level">How much it changed by the check time</option>
            <option value="half_time">How fast: time to get half-way to its final value</option>
            <option value="rate">Its speed of change</option>
          </select>
          <span className={styles.help}>
            Speed comes from a curve drawn through each sample&apos;s readings, with its ±. Faster means it gets
            half-way sooner.
          </span>
        </label>
        <label className={styles.field}>
          <span className={styles.label}>Which way</span>
          <select
            className={styles.select}
            value={plan.direction ?? ""}
            onChange={(e) => set({ direction: (e.target.value || null) as PlanDraft["direction"] })}
          >
            <option value="">Choose…</option>
            <option value="higher">Test sample higher than the control</option>
            <option value="lower">Test sample lower than the control</option>
          </select>
        </label>
        <label className={styles.field}>
          <span className={styles.label}>Which test samples</span>
          <select
            className={styles.select}
            value={plan.treatment ?? ""}
            onChange={(e) => set({ treatment: e.target.value || null })}
          >
            <option value="">Every test sample</option>
            {treatments.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          <span className={styles.label}>Smallest difference that counts</span>
          <input
            className={`${styles.input} num`}
            type="number"
            min={0}
            step="any"
            value={plan.min_effect ?? ""}
            onChange={(e) => set({ min_effect: e.target.value === "" ? null : Math.max(0, Number(e.target.value)) })}
          />
          <span className={styles.help}>
            In {unit || "the measurement's unit"}: anything smaller is treated as no real difference.
          </span>
        </label>
        <label className={styles.field}>
          <span className={styles.label}>Check time (h:mm into the run)</span>
          <input
            className={`${styles.input} num`}
            value={checkpoint}
            placeholder="0:05"
            onChange={(e) => {
              setCheckpoint(e.target.value);
              set({ checkpoint_s: fromClock(e.target.value) });
            }}
          />
          <span className={styles.help}>
            Argus won&apos;t judge before then: judging too early finds differences that aren&apos;t real.
          </span>
        </label>
      </div>

      <fieldset className={styles.choices}>
        <legend className={styles.label}>Other things that could cause a change</legend>
        {rivals.map((r) => (
          <label key={r} className={styles.choice}>
            <input
              type="checkbox"
              checked={plan.rivals.includes(r)}
              onChange={(e) =>
                set({ rivals: e.target.checked ? [...plan.rivals, r] : plan.rivals.filter((x) => x !== r) })
              }
            />
            {r}
          </label>
        ))}
      </fieldset>
      <form
        className={styles.row}
        onSubmit={(e) => {
          e.preventDefault();
          if (!rival.trim() || plan.rivals.includes(rival.trim())) return;
          set({ rivals: [...plan.rivals, rival.trim()] });
          setRival("");
        }}
      >
        <label className={styles.field}>
          <span className={styles.hidden}>Another possible cause</span>
          <input
            className={styles.input}
            value={rival}
            onChange={(e) => setRival(e.target.value)}
            placeholder="Another possible cause"
          />
        </label>
        <Button type="submit" disabled={!rival.trim()}>
          Add
        </Button>
      </form>
    </div>
  );
}
