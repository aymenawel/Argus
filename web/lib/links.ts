import { isReplay } from "./replay.ts";

// Where a run's pages are: under /experiments in the app, under /replay in the public replay (D-83).

export function runHref(experimentId: string, runId: string): string {
  return isReplay() ? `/replay/${runId}` : `/experiments/${experimentId}/run`;
}

export function resultsHref(experimentId: string, runId: string): string {
  return isReplay() ? `/replay/${runId}/results` : `/experiments/${experimentId}/results`;
}

/** The first link of every page's crumb. */
export function homeLink(): { href: string; label: string } {
  return isReplay() ? { href: "/replay", label: "Replays" } : { href: "/", label: "Experiments" };
}
