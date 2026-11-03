"use client";

import { useSyncExternalStore } from "react";
import { readTheme, setTheme, subscribeTheme, type ThemeChoice } from "@/lib/theme";
import styles from "./ThemeSwitch.module.css";

const OPTIONS: { value: ThemeChoice; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "System" },
];

// The server always renders "Light", the default; React swaps in the saved choice right after hydration.
const serverChoice = (): ThemeChoice => "light";

export function ThemeSwitch() {
  const choice = useSyncExternalStore(subscribeTheme, readTheme, serverChoice);
  return (
    <div className={styles.switch} role="group" aria-label="Theme">
      {OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          className={`${styles.option} ${choice === option.value ? styles.on : ""}`}
          aria-pressed={choice === option.value}
          onClick={() => setTheme(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
