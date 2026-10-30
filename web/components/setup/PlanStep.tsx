"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { quantityUnit } from "@/lib/recipe";
import type { Plan, PlanDraft, RecipeDetail, Setup } from "@/lib/types";
import styles from "./Step.module.css";

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
        <span className={styles.label}>Hypothesis</span>
        <textarea
          className={styles.textarea}
          value={plan.hypothesis}
          onChange={(e) => set({ hypothesis: e.target.value })}
          placeholder="Food colouring spreads faster in warm water than in cold water."
        />
      </label>
      <div className={styles.grid}>
        <label className={styles.field}>
          <span className={styles.label}>Prediction</span>
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

      <h3 className={styles.label}>The prediction Argus will judge</h3>
      <div className={styles.grid}>
        <label className={styles.field}>
          <span className={styles.label}>Measurement</span>
          <select
            className={styles.select}
            value={plan.metric ?? ""}
            onChange={(e) => set({ metric: e.target.value || null })}
          >
            <option value="">Choose…</option>
            {recipe.metrics.map((m) => (
              <option key={m.id} value={m.id}>
                {m.id} ({m.unit})
              </option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          <span className={styles.label}>Judged on</span>
          <select
            className={styles.select}
            value={plan.quantity ?? "level"}
            onChange={(e) =>
              set({ quantity: e.target.value === "level" ? null : (e.target.value as PlanDraft["quantity"]) })
            }
          >
            <option value="level">Its level by the checkpoint</option>
            <option value="half_time">How fast: time to half its final value</option>
            <option value="rate">Its rate of change</option>
          </select>
          <span className={styles.help}>
            Speed is read off a curve fitted to each vessel, with its ±. Faster means a lower half-way time.
          </span>
        </label>
        <label className={styles.field}>
          <span className={styles.label}>Direction</span>
          <select
            className={styles.select}
            value={plan.direction ?? ""}
            onChange={(e) => set({ direction: (e.target.value || null) as PlanDraft["direction"] })}
          >
            <option value="">Choose…</option>
            <option value="higher">Treatment higher than control</option>
            <option value="lower">Treatment lower than control</option>
          </select>
        </label>
        <label className={styles.field}>
          <span className={styles.label}>Which treatment</span>
          <select
            className={styles.select}
            value={plan.treatment ?? ""}
            onChange={(e) => set({ treatment: e.target.value || null })}
          >
            <option value="">Every treatment vessel</option>
            {treatments.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          <span className={styles.label}>Smallest effect that matters</span>
          <input
            className={`${styles.input} num`}
            type="number"
            min={0}
            step="any"
            value={plan.min_effect ?? ""}
            onChange={(e) => set({ min_effect: e.target.value === "" ? null : Math.max(0, Number(e.target.value)) })}
          />
          <span className={styles.help}>
            In {unit || "the measurement's unit"}: smaller differences don&apos;t count.
          </span>
        </label>
        <label className={styles.field}>
          <span className={styles.label}>Checkpoint (h:mm of run time)</span>
          <input
            className={`${styles.input} num`}
            value={checkpoint}
            placeholder="0:05"
            onChange={(e) => {
              setCheckpoint(e.target.value);
              set({ checkpoint_s: fromClock(e.target.value) });
            }}
          />
          <span className={styles.help}>No verdict before it: judging early finds effects that aren&apos;t there.</span>
        </label>
      </div>

      <fieldset className={styles.choices}>
        <legend className={styles.label}>Rival explanations to rule out</legend>
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
          <span className={styles.hidden}>Another rival explanation</span>
          <input
            className={styles.input}
            value={rival}
            onChange={(e) => setRival(e.target.value)}
            placeholder="Another rival explanation"
          />
        </label>
        <Button type="submit" disabled={!rival.trim()}>
          Add
        </Button>
      </form>
    </div>
  );
}
