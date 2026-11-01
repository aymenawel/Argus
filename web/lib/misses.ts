// What Results and the timeline say about misses (D-90): how often SAM found each vessel's object, and how far a
// missed stretch is drawn. The counts come from the worker; this only words them.
import { formatRunTime } from "./scale.ts";
import type { Coverage, RunEvent } from "./types";

/** "14 of 145 pictures" and, when SAM lost the object after finding it, "not found in 131 since 11:12". A run
 *  from before SAM's answers were kept, or a bundle published before then, has no coverage: "—". */
export function coverageLines(c: Coverage | null | undefined, span: number): [string, string | null] {
  if (!c) return ["—", null];
  const found = `${c.found} of ${c.asked} pictures`;
  if (c.first_found_t === null) return [found, "never found"];
  if (c.missed_after === 0) return [found, null];
  return [found, `not found in ${c.missed_after} since ${formatRunTime(c.first_found_t, span)}`];
}

/** Where an event's mark ends on a lane: its end, or the end of the run for a miss still open (never found again);
 *  any other open event is a mark at its start. */
export function markEnd(e: RunEvent, tEnd: number): number {
  return e.t_end ?? (e.kind === "missed" ? tEnd : e.t_start);
}
