// Scales and ticks for the Results page's plain SVG charts (no chart library, spec phase 4 §5).

/** Maps [d0, d1] onto [r0, r1] (r0 > r1 for a y axis that grows upward); an empty domain maps to r0. */
export function linearScale(domain: [number, number], range: [number, number]): (x: number) => number {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  const span = d1 - d0;
  return (x) => (span === 0 ? r0 : r0 + ((x - d0) / span) * (r1 - r0));
}

/** About `count` round ticks (steps of 1, 2 or 5 × 10^k) from at or below min to at or above max. */
export function niceTicks(min: number, max: number, count: number): number[] {
  if (max <= min) return [min];
  const raw = (max - min) / Math.max(count, 1);
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 5, 10].map((m) => m * magnitude).find((s) => s >= raw) ?? 10 * magnitude;
  const first = Math.floor(min / step) * step;
  const ticks: number[] = [];
  for (let t = first; t <= max + step * 1e-9; t += step) ticks.push(Number(t.toFixed(10)));
  if (ticks.at(-1)! < max) ticks.push(Number((ticks.at(-1)! + step).toFixed(10)));
  return ticks;
}

/** "21.4 ± 0.6 h": the ± rounded to one significant digit (two when it starts with 1), the value to the same place
 * (KB 08); a ± of 0 shows the value as given. */
export function formatPair([value, uncertainty]: [number, number], unit: string): string {
  if (!(uncertainty > 0)) return `${Number(value.toPrecision(6))} ${unit}`;
  const exponent = Math.floor(Math.log10(uncertainty));
  const leading = uncertainty / 10 ** exponent;
  const place = leading < 2 ? exponent - 1 : exponent; // the decimal position to round both numbers to
  const round = (x: number) => Math.round(x / 10 ** place) * 10 ** place;
  const decimals = Math.max(0, -place);
  return `${round(value).toFixed(decimals)} ± ${round(uncertainty).toFixed(decimals)} ${unit}`;
}

export type Marker = "circle" | "square" | "diamond";
export type SeriesGroup = { label: string; control: boolean; dash?: string; marker: Marker };
type Grouped = { role: "control" | "treatment"; condition: { value: number | string } | null };

// Up to three treatment conditions stay apart by dash and dot shape; the control is always grey, solid and round.
const DASHES = [undefined, "7 4", "2 4"];
const MARKERS: Marker[] = ["circle", "square", "diamond"];

export const groupKey = (v: Grouped) => `${v.role}:${v.condition?.value ?? ""}`;

/** One group per condition, controls first. The dots carry the shape too: a vessel with no fitted curve still shows
 * which condition its readings belong to. */
export function conditionGroups(vessels: Grouped[]): Map<string, SeriesGroup> {
  const groups = new Map<string, SeriesGroup>();
  for (const v of [...vessels].sort((a, b) => Number(b.role === "control") - Number(a.role === "control"))) {
    const key = groupKey(v);
    if (groups.has(key)) continue;
    const control = v.role === "control";
    const treatments = [...groups.values()].filter((g) => !g.control).length;
    const name = control ? "Control" : "Treatment";
    groups.set(key, {
      label: v.condition ? `${name}: ${v.condition.value}` : name,
      control,
      dash: control ? undefined : DASHES[treatments % DASHES.length],
      marker: control ? "circle" : MARKERS[treatments % MARKERS.length],
    });
  }
  return groups;
}
