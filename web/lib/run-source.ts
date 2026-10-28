import { frameUrl as liveFrameUrl, getDetections, getRun, getTimeline } from "./api";
import { subscribe as subscribeEvents } from "./events";
import type { DetectionOutline, FrameRow, MeasurementRow, RunEvent, RunProgress, RunView } from "./types";

// Where a Run view gets its data (spec §9.3): the live worker over REST + SSE now; a static bundle for the
// public replay later. Both give the same snapshot shape.

export type RunSnapshot = {
  view: RunView;
  frames: FrameRow[]; // sorted by t
  measurements: MeasurementRow[]; // sorted by t
  events: RunEvent[];
  progress: RunProgress | null;
};

export interface RunSource {
  load(): Promise<RunSnapshot>;
  subscribe(onChange: (snapshot: RunSnapshot) => void): () => void;
  frameUrl(frameId: string, width?: number): string;
  detections(frameId: string): Promise<DetectionOutline[]>;
}

const byT = <T extends { t: number }>(a: T, b: T) => a.t - b.t;

type Data = Record<string, unknown> & { run_id?: string };

export class LiveSource implements RunSource {
  private snapshot: RunSnapshot | null = null;
  private pending: [string, Data][] = [];
  private onChange: ((snapshot: RunSnapshot) => void) | null = null;
  private outlines = new Map<string, Promise<DetectionOutline[]>>();

  constructor(readonly runId: string) {}

  async load(): Promise<RunSnapshot> {
    const [view, timeline] = await Promise.all([getRun(this.runId), getTimeline(this.runId)]);
    this.snapshot = {
      view,
      frames: [...timeline.frames].sort(byT),
      measurements: [...timeline.measurements].sort(byT),
      events: timeline.events,
      progress: null,
    };
    const waiting = this.pending; // events that arrived while loading
    this.pending = [];
    waiting.forEach(([type, data]) => this.apply(type, data));
    return this.snapshot;
  }

  /** Listen before loading, so nothing published in between is lost. */
  subscribe(onChange: (snapshot: RunSnapshot) => void): () => void {
    this.onChange = onChange;
    const stop = subscribeEvents((type, data) => {
      const payload = data as Data;
      if (type === "resync") {
        void this.load().then((s) => this.onChange?.(s));
        return;
      }
      if (payload.run_id !== this.runId) return;
      if (this.snapshot === null) this.pending.push([type, payload]);
      else this.apply(type, payload);
    });
    return () => {
      this.onChange = null;
      stop();
    };
  }

  frameUrl(frameId: string, width?: number): string {
    return liveFrameUrl(this.runId, frameId, width);
  }

  detections(frameId: string): Promise<DetectionOutline[]> {
    let found = this.outlines.get(frameId);
    if (!found) {
      found = getDetections(this.runId, frameId);
      found.catch(() => this.outlines.delete(frameId)); // try again next time
      this.outlines.set(frameId, found);
    }
    return found;
  }

  private apply(type: string, data: Data) {
    const s = this.snapshot;
    if (s === null) return;
    let next: RunSnapshot = s;
    if (type === "measurement") {
      const row = data as unknown as MeasurementRow;
      if (s.measurements.some((m) => m.id === row.id)) return;
      next = { ...s, measurements: [...s.measurements, row].sort(byT) };
    } else if (type === "frame_analyzed") {
      const frame: FrameRow = {
        id: String(data.frame_id),
        t: Number(data.t),
        analyzed: true,
        quality_flags: (data.quality_flags as string[]) ?? [],
      };
      next = { ...s, frames: [...s.frames.filter((f) => f.id !== frame.id), frame].sort(byT) };
    } else if (type === "event") {
      const event: RunEvent = {
        id: String(data.id),
        vessel_id: (data.vessel_id as string | null) ?? null,
        t_start: Number(data.t),
        t_end: null,
        kind: data.kind as RunEvent["kind"],
        source: "",
        detail: (data.detail as Record<string, unknown>) ?? {},
      };
      if (s.events.some((e) => e.id === event.id)) return;
      next = { ...s, events: [...s.events, event] };
    } else if (type === "run_progress") {
      next = { ...s, progress: data as unknown as RunProgress };
    } else if (type === "spend") {
      next = { ...s, view: { ...s.view, spend_usd: Number(data.spent_usd) } };
    } else if (type === "run_status") {
      // The run ended: fetch its final state (status, end time, spend).
      void getRun(this.runId).then((view) => {
        if (this.snapshot) {
          this.snapshot = { ...this.snapshot, view, progress: null };
          this.onChange?.(this.snapshot);
        }
      });
      return;
    } else {
      return;
    }
    this.snapshot = next;
    this.onChange?.(next);
  }
}
