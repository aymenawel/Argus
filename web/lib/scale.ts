// A tiny linear scale (d3-scale waits for approval) and run-time formatting.

export type LinearScale = ((x: number) => number) & { invert: (y: number) => number };

export function linearScale(domain: [number, number], range: [number, number]): LinearScale {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  const span = d1 - d0 || 1;
  const scale = ((x: number) => r0 + ((x - d0) / span) * (r1 - r0)) as LinearScale;
  scale.invert = (y: number) => d0 + ((y - r0) / (r1 - r0 || 1)) * span;
  return scale;
}

const pad = (n: number) => String(Math.floor(n)).padStart(2, "0");

/** Run time t (seconds): "41:20" (hours:minutes) from an hour on, "3:05" (minutes:seconds) below. */
export function formatRunTime(t: number): string {
  const s = Math.max(0, t);
  if (s >= 3600) return `${Math.floor(s / 3600)}:${pad((s % 3600) / 60)}`;
  return `${Math.floor(s / 60)}:${pad(s % 60)}`;
}

/** The item with the largest `t` not after `t`, from a list sorted by t; null before the first. */
export function atOrBefore<T extends { t: number }>(sorted: T[], t: number): T | null {
  let lo = 0;
  let hi = sorted.length - 1;
  let found: T | null = null;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (sorted[mid].t <= t + 1e-6) {
      found = sorted[mid];
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  return found;
}
