"use client";

import { type KeyboardEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { addMeasurement, measurementInWords, renameConcept, stepInWords, withMethod } from "@/lib/recipe";
import type { MeasurementSpec, RecipeDraftResult, RecipeSpec, Tool } from "@/lib/types";
import styles from "./RecipeDraftView.module.css";

type Props = {
  draft: RecipeDraftResult;
  toolbox: Tool[];
  onChange: (draft: RecipeDraftResult) => void;
};

const STEP_UNITS = [
  { label: "s", seconds: 1 },
  { label: "min", seconds: 60 },
  { label: "h", seconds: 3600 },
];

const unitFor = (seconds: number) => (seconds >= 3600 ? 2 : seconds >= 60 ? 1 : 0);

// Enter applies an inline edit; it must not submit the dialog's form (which would create the experiment).
const applyOnEnter = (e: KeyboardEvent<HTMLInputElement>) => {
  if (e.key !== "Enter") return;
  e.preventDefault();
  e.currentTarget.blur();
};

// A concept's name is applied when the field is left, and only if it is new and not empty: renaming as you type
// would merge two concepts the moment one name passes through the other.
function ConceptName({ name, taken, onRename }: { name: string; taken: string[]; onRename: (to: string) => void }) {
  const [text, setText] = useState(name);
  const next = text.trim();
  const invalid = next === "" || (next !== name && taken.includes(next));
  return (
    <input
      className={styles.concept}
      value={text}
      size={Math.max(4, text.length)}
      aria-label={`Concept ${name}`}
      aria-invalid={invalid || undefined}
      onChange={(e) => setText(e.target.value)}
      onBlur={() => (invalid ? setText(name) : next !== name && onRename(next))}
      onKeyDown={applyOnEnter}
    />
  );
}

function NumberField({ value, label, onValue }: { value: number; label: string; onValue: (n: number) => void }) {
  const [text, setText] = useState(String(value));
  const n = Number(text);
  return (
    <input
      className={styles.number}
      inputMode="decimal"
      value={text}
      aria-label={label}
      aria-invalid={!(n > 0) || undefined}
      onChange={(e) => {
        setText(e.target.value);
        const next = Number(e.target.value);
        if (next > 0) onValue(next);
      }}
      onBlur={() => !(n > 0) && setText(String(value))}
      onKeyDown={applyOnEnter}
    />
  );
}

function MeasurementRow({
  m,
  recipe,
  toolbox,
  locked,
  onChange,
  onRemove,
}: {
  m: MeasurementSpec;
  recipe: RecipeSpec;
  toolbox: Tool[];
  locked: string | null;
  onChange: (m: MeasurementSpec) => void;
  onRemove: () => void;
}) {
  const concepts = recipe.concepts.map((c) => c.name);
  const tools = toolbox.some((t) => t.method === m.method)
    ? toolbox
    : [{ method: m.method, family: m.family, unit: m.unit, words: "" }, ...toolbox];
  return (
    <li className={styles.measurement}>
      <span className={styles.measureName}>
        {measurementInWords(m)} <span className={styles.unit}>({m.unit})</span>
        {m.id === recipe.main_measurement && <span className={styles.tag}>main</span>}
      </span>
      <span className={styles.measureEdit}>
        <select
          className={styles.select}
          value={m.method}
          aria-label={`How ${measurementInWords(m)} is measured`}
          onChange={(e) => {
            const tool = tools.find((t) => t.method === e.target.value);
            if (tool) onChange(withMethod(m, tool, recipe));
          }}
        >
          {tools.map((t) => (
            <option key={t.method} value={t.method} title={t.words}>
              {t.method.replaceAll("_", " ")}
            </option>
          ))}
        </select>
        <span className={styles.joiner}>of</span>
        <select
          className={styles.select}
          value={m.from}
          aria-label={`What ${measurementInWords(m)} reads from`}
          onChange={(e) => onChange({ ...m, from: e.target.value })}
        >
          {concepts.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
        {m.method === "touching_count" && (
          <>
            <span className={styles.joiner}>touching a</span>
            <select
              className={styles.select}
              value={m.touching ?? ""}
              aria-label={`What a ${m.from} must touch`}
              onChange={(e) => onChange({ ...m, touching: e.target.value })}
            >
              {concepts.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
            <span className={styles.joiner}>at least</span>
            <NumberField
              value={m.min_length_mm ?? 2}
              label={`Shortest ${m.touching ?? "part"} that counts, in mm`}
              onValue={(n) => onChange({ ...m, min_length_mm: n })}
            />
            <span className={styles.joiner}>mm</span>
          </>
        )}
        {m.method === "grown_count" && (
          <>
            <span className={styles.joiner}>grown at least</span>
            <NumberField
              value={m.min_length_mm ?? 2}
              label={`How much longer a ${m.from} must grow to count, in mm`}
              onValue={(n) => onChange({ ...m, min_length_mm: n })}
            />
            <span className={styles.joiner}>mm</span>
          </>
        )}
        <button
          type="button"
          className={styles.remove}
          onClick={onRemove}
          disabled={locked !== null}
          title={locked ?? "Remove this measurement"}
          aria-label={`Remove ${measurementInWords(m)}`}
        >
          ×
        </button>
      </span>
    </li>
  );
}

/** Argus's draft in words, every line editable: what it looks for, what it measures, how often; the plan below. */
export function RecipeDraftView({ draft, toolbox, onChange }: Props) {
  const { recipe, plan } = draft;
  const setRecipe = (next: RecipeSpec) => onChange({ ...draft, recipe: next });
  const concepts = recipe.concepts.map((c) => c.name);
  const [stepUnit, setStepUnit] = useState(unitFor(recipe.analysis_step_s));
  const metric = recipe.measurements.find((m) => m.id === plan.metric);

  const used = (name: string) => recipe.measurements.some((m) => m.from === name || m.touching === name);

  return (
    <section className={styles.draft} aria-label="Argus's draft">
      <p className={styles.title}>{recipe.title}</p>

      {draft.safety_notes.length > 0 && (
        <div className={styles.safety} role="note">
          {draft.safety_notes.map((note) => (
            <p key={note}>{note}</p>
          ))}
        </div>
      )}

      <dl className={styles.lines}>
        <div className={styles.line}>
          <dt>Looks for</dt>
          <dd className={styles.concepts}>
            {recipe.concepts.map((c) => (
              <span key={c.name} className={styles.conceptChip}>
                <ConceptName
                  name={c.name}
                  taken={concepts}
                  onRename={(to) => {
                    const next = renameConcept(recipe, c.name, to);
                    onChange({ ...draft, recipe: next });
                  }}
                />
                {!used(c.name) && concepts.length > 1 && (
                  <button
                    type="button"
                    className={styles.remove}
                    aria-label={`Remove ${c.name}`}
                    onClick={() => setRecipe({ ...recipe, concepts: recipe.concepts.filter((x) => x !== c) })}
                  >
                    ×
                  </button>
                )}
              </span>
            ))}
            {concepts.length < 4 && (
              <Button
                variant="text"
                onClick={() => {
                  let name = "object";
                  for (let n = 2; concepts.includes(name); n++) name = `object ${n}`;
                  setRecipe({ ...recipe, concepts: [...recipe.concepts, { name }] });
                }}
              >
                Add a concept
              </Button>
            )}
          </dd>
        </div>

        <div className={styles.line}>
          <dt>Measures</dt>
          <dd>
            <ul className={styles.measurements}>
              {recipe.measurements.map((m, i) => (
                <MeasurementRow
                  key={m.id}
                  m={m}
                  recipe={recipe}
                  toolbox={toolbox}
                  locked={
                    m.id === recipe.main_measurement
                      ? "The main measurement stays"
                      : m.id === plan.metric
                        ? "The plan is judged on this one"
                        : null
                  }
                  onChange={(next) =>
                    setRecipe({ ...recipe, measurements: recipe.measurements.map((x, j) => (j === i ? next : x)) })
                  }
                  onRemove={() => setRecipe({ ...recipe, measurements: recipe.measurements.filter((_, j) => j !== i) })}
                />
              ))}
            </ul>
            {toolbox.length > 0 && (
              <Button variant="text" onClick={() => setRecipe(addMeasurement(recipe, toolbox[0], concepts[0]))}>
                Add a measurement
              </Button>
            )}
          </dd>
        </div>

        <div className={styles.line}>
          <dt>Every</dt>
          <dd className={styles.step}>
            <NumberField
              key={stepUnit}
              value={Number((recipe.analysis_step_s / STEP_UNITS[stepUnit].seconds).toFixed(3))}
              label="How often Argus measures"
              onValue={(n) => setRecipe({ ...recipe, analysis_step_s: n * STEP_UNITS[stepUnit].seconds })}
            />
            <select
              className={styles.select}
              value={stepUnit}
              aria-label="Unit"
              onChange={(e) => setStepUnit(Number(e.target.value))}
            >
              {STEP_UNITS.map((u, i) => (
                <option key={u.label} value={i}>
                  {u.label}
                </option>
              ))}
            </select>
          </dd>
        </div>
      </dl>

      <div className={styles.plan}>
        <p>
          <span className={styles.planLabel}>Hypothesis</span> {plan.hypothesis}
        </p>
        <p>
          <span className={styles.planLabel}>Prediction</span> {plan.prediction}
        </p>
        {metric && (
          <p>
            <span className={styles.planLabel}>Judged on</span> {measurementInWords(metric)},{" "}
            {plan.direction === "lower" ? "lower" : "higher"} in {plan.treatment || "the treatment"} by at least{" "}
            {plan.min_effect} {metric.unit} <span className={styles.suggested}>suggested</span>, from{" "}
            {plan.checkpoint_s != null ? stepInWords(plan.checkpoint_s) : "—"}{" "}
            <span className={styles.suggested}>suggested</span>
          </p>
        )}
        {draft.setup_hints.conditions.length > 0 && (
          <p>
            <span className={styles.planLabel}>Conditions</span>{" "}
            {draft.setup_hints.conditions.map((c) => `${c.value} (${c.role})`).join(", ")}
          </p>
        )}
        {draft.question && (
          <p>
            <span className={styles.planLabel}>Argus asks</span> {draft.question}
          </p>
        )}
      </div>
      <p className={styles.help}>You check the plan, the dishes and the conditions in the setup steps next.</p>
    </section>
  );
}
