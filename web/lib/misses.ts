// What Results and the timeline say about misses (D-90): how often SAM found each vessel's object, and how far a
// missed stretch is drawn; and which outlines code drew from the change since the start, not SAM (D-93). The counts
// come from the worker; this only words them.
import { formatRunTime } from "./scale.ts";
import type { Coverage, DetectionOutline, RunEvent } from "./types";

/** The backend of an outline code drew from the change since the start, because SAM found nothing there. */
export const CODE_OUTLINE = "change-map";

export function outlinedByCode(d: DetectionOutline): boolean {
  return d.backend === CODE_OUTLINE;
}

/** Under a frame: SAM's objects, and the outlines code drew, which are dashed. */
export function outlineCaption(items: DetectionOutline[]): string {
  const coded = items.filter(outlinedByCode).length;
  const sam = items.length - coded;
  const caption = `SAM 3.1 · ${sam} ${sam === 1 ? "object" : "objects"}`;
  return coded ? `${caption} · ${coded} outlined by code (dashed)` : caption;
}

/** "14 of 145 pictures"; when some were found by pointing SAM at the change or by code, how ("55 by name · 30
 *  pointed · 12 by code"); and, when the object was lost after it was found, "not found in 131 since 11:12". A run
 *  from before SAM's answers were kept, or a bundle published before then, has no coverage: "—". */
export function coverageLines(c: Coverage | null | undefined, span: number): [string, string | null, string | null] {
  if (!c) return ["—", null, null];
  const found = `${c.found} of ${c.asked} pictures`;
  const [byName, pointed, byCode] = [c.by_name ?? 0, c.pointed ?? 0, c.by_code ?? 0];
  const how = pointed + byCode > 0 ? `${byName} by name · ${pointed} pointed · ${byCode} by code` : null;
  if (c.first_found_t === null) return [found, how, "never found"];
  if (c.missed_after === 0) return [found, how, null];
  return [found, how, `not found in ${c.missed_after} since ${formatRunTime(c.first_found_t, span)}`];
}

/** Where an event's mark ends on a lane: its end, or the end of the run for a miss still open (never found again);
 *  any other open event is a mark at its start. */
export function markEnd(e: RunEvent, tEnd: number): number {
  return e.t_end ?? (e.kind === "missed" ? tEnd : e.t_start);
}
