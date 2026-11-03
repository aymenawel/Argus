// The Argus line (D-98): what a run shows, in one or two sentences built by code from the stored readings and the
// verdict. No model writes it, so every number in it is a measurement with its ±.
import { formatPair } from "./chart.ts";
import { metricWords, roleWord } from "./plain.ts";
import type { VerdictLevel } from "./types.ts";

export type LineSample = {
  label: string;
  role: "control" | "treatment";
  condition: string | null;
  first: number | null; // the sample's first reading of the main measurement
  latest: [number, number] | null; // its latest reading, with its ±
};

export type LineInput = {
  samples: LineSample[];
  metric: string;
  unit: string;
  verdict: { level: VerdictLevel; sentence: string } | null;
  checkTime: string | null; // the plan's check time as the run's clock reads it, when there is a plan
};

export type ArgusLine = { lead: string; detail: string | null; level: VerdictLevel | null };

/** A reading as a sentence says it: "25.12 ± 0.06 ΔE", or "9 sprouted seeds" for a count. */
function reading(value: [number, number], metric: string, unit: string): string {
  return unit === "count" ? `${Number(value[0].toPrecision(6))} ${metricWords(metric)}` : formatPair(value, unit);
}

const named = (s: LineSample) => `Sample ${s.label} (${roleWord(s.role)}${s.condition ? `, ${s.condition}` : ""})`;

export function argusLine({ samples, metric, unit, verdict, checkTime }: LineInput): ArgusLine {
  const measured = samples.filter((s): s is LineSample & { latest: [number, number] } => s.latest !== null);
  const detail = verdict?.sentence ?? (checkTime ? `Argus judges your idea from ${checkTime}.` : null);
  const level = verdict?.level ?? null;
  if (measured.length === 0) return { lead: "Argus is watching. Nothing measured yet.", detail, level };

  const change = (s: (typeof measured)[number]) => s.latest[0] - (s.first ?? s.latest[0]);
  const most = measured.reduce((best, s) => (change(s) > change(best) ? s : best));
  const control = most.role === "control" ? undefined : measured.find((s) => s.role === "control");
  const against = control
    ? `, against ${reading(control.latest, metric, unit)} for the control (${control.label})`
    : "";
  return { lead: `${named(most)} changed the most: ${reading(most.latest, metric, unit)}${against}.`, detail, level };
}

/** The verdict's checks counted in words: "1 passed · 1 not settled · 1 failed", empty groups left out. */
export function checkCounts(checks: { ok: boolean | null }[]): string {
  const groups: [string, number][] = [
    ["passed", checks.filter((c) => c.ok === true).length],
    ["not settled", checks.filter((c) => c.ok === null).length],
    ["failed", checks.filter((c) => c.ok === false).length],
  ];
  const said = groups.filter(([, n]) => n > 0).map(([word, n]) => `${n} ${word}`);
  return said.length > 0 ? said.join(" · ") : "No checks yet";
}
