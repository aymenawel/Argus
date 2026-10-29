"use client";

import type { Setup, SetupVessel } from "@/lib/types";
import styles from "./Step.module.css";

type Props = {
  setup: Setup;
  suggestions: string[]; // condition values from the draft, if any
  onChange: (setup: Setup) => void;
};

// What each vessel is: a control or a treatment, and its condition of the factor (water temperature: warm).
export function RolesStep({ setup, suggestions, onChange }: Props) {
  const factor = setup.factor ?? "";
  const unit = setup.factor_unit ?? "";
  const values = [...new Set([...suggestions, ...setup.vessels.map((v) => String(v.condition?.value ?? ""))])].filter(
    Boolean,
  );

  const withCondition = (v: SetupVessel, value: string, f = factor, u = unit): SetupVessel => ({
    ...v,
    condition: value.trim() ? { factor: f.trim() || "condition", value: value.trim(), unit: u.trim() || null } : null,
  });
  const setFactor = (f: string, u: string) =>
    onChange({
      ...setup,
      factor: f || null,
      factor_unit: u || null,
      vessels: setup.vessels.map((v) => withCondition(v, String(v.condition?.value ?? ""), f, u)),
    });
  const setVessel = (label: string, next: (v: SetupVessel) => SetupVessel) =>
    onChange({ ...setup, vessels: setup.vessels.map((v) => (v.label === label ? next(v) : v)) });

  return (
    <div className={styles.step}>
      <p className={styles.lead}>
        Controls show what happens without the treatment. Give each vessel its role and its condition; at least one must
        be a control.
      </p>
      <div className={styles.grid}>
        <label className={styles.field}>
          <span className={styles.label}>Factor</span>
          <input
            className={styles.input}
            value={factor}
            onChange={(e) => setFactor(e.target.value, unit)}
            placeholder="water temperature"
          />
        </label>
        <label className={styles.field}>
          <span className={styles.label}>Unit (optional)</span>
          <input
            className={`${styles.input} ${styles.short}`}
            value={unit}
            onChange={(e) => setFactor(factor, e.target.value)}
            placeholder="°C"
          />
        </label>
      </div>
      <datalist id="condition-values">
        {values.map((v) => (
          <option key={v} value={v} />
        ))}
      </datalist>
      <ul className={styles.list} aria-label="Vessels">
        {setup.vessels.map((v) => (
          <li key={v.label} className={styles.item}>
            <span className={styles.badge}>{v.label}</span>
            <fieldset className={styles.choices}>
              <legend className={styles.hidden}>Role of vessel {v.label}</legend>
              {(["control", "treatment"] as const).map((role) => (
                <label key={role} className={styles.choice}>
                  <input
                    type="radio"
                    name={`role-${v.label}`}
                    checked={v.role === role}
                    onChange={() => setVessel(v.label, (x) => ({ ...x, role }))}
                  />
                  {role === "control" ? "Control" : "Treatment"}
                </label>
              ))}
            </fieldset>
            <label className={styles.field}>
              <span className={styles.hidden}>Condition of vessel {v.label}</span>
              <input
                className={`${styles.input} ${styles.short}`}
                list="condition-values"
                value={String(v.condition?.value ?? "")}
                onChange={(e) => setVessel(v.label, (x) => withCondition(x, e.target.value))}
                placeholder={factor ? `${factor}…` : "condition"}
              />
            </label>
          </li>
        ))}
      </ul>
    </div>
  );
}
