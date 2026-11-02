// What the Results page says in its own words, apart from the numbers the worker formats.
import type { Verdict } from "./types.ts";

/** The verdict's explanation, or null when it only repeats a check (a code-written Too early explains itself). */
export function explanationToShow(verdict: Verdict): string | null {
  const text = verdict.body.explanation;
  if (!text || verdict.checks.some((c) => c.text === text)) return null;
  return text;
}

/** A suggested run length: minutes under an hour, so a dye run judged at 2 minutes doesn't read "0.0 h". */
export function runLength(hours: number): string {
  if (hours < 1) return `${(hours * 60).toFixed(0)} min`;
  return `${hours >= 10 ? hours.toFixed(0) : hours.toFixed(1)} h`;
}
