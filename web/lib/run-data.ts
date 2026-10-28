import type { MeasurementRow, RunEvent, RunView, Vessel } from "./types";

// What the Run view derives from a snapshot. Plain TypeScript with type-only imports (Node's test runner loads it).

/** Rows of the given metrics per vessel, in the rows' order (one pass; rows are appended, never copied). */
export function byVessel(rows: MeasurementRow[], metrics: Set<string>): Map<string, MeasurementRow[]> {
  const groups = new Map<string, MeasurementRow[]>();
  for (const row of rows) {
    if (!metrics.has(row.metric)) continue;
    const list = groups.get(row.vessel_id);
    if (list) list.push(row);
    else groups.set(row.vessel_id, [row]);
  }
  return groups;
}

/** The vessel's region in force at t: as drawn, or where the last camera move before t carried it. */
export function regionAt(vessel: Vessel, events: RunEvent[], t: number): [number, number][] {
  let region = vessel.roi;
  let since = -Infinity;
  for (const e of events) {
    if (e.kind !== "camera_moved" || e.t_start > t + 1e-6 || e.t_start < since) continue;
    const moved = (e.detail.rois as Record<string, [number, number][]> | undefined)?.[vessel.id];
    if (moved) {
      region = moved;
      since = e.t_start;
    }
  }
  return region;
}

const STOPPED_BY_WORKER = "This run stopped early: the worker stopped while it was running. What it measured is kept.";
const NO_CARD = "No Argus Card or ruler in view: frames are recorded, but nothing is measured in millimetres.";
const SPEND_CAP =
  "The spend cap was reached: segmentation paused. Frames are still recorded and colour still measured.";

function interrupted(detail: Record<string, unknown>): string {
  if (detail.reason === "camera_lost") {
    return "This run stopped: the camera stopped sending frames. What it measured is kept.";
  }
  if (typeof detail.error === "string") {
    return `This run stopped early on an error (${detail.error}). What it measured is kept.`;
  }
  return STOPPED_BY_WORKER;
}

/** The one notice worth a line under the header, from the newest event that calls for one. */
export function runNotice(events: RunEvent[], view: RunView): string | null {
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i];
    if (e.kind === "interrupted") return interrupted(e.detail);
    if (e.kind === "spend") return SPEND_CAP;
    if (e.kind === "no_calibration" && view.calibration === null) return NO_CARD;
  }
  return null;
}
