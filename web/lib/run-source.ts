import { frameUrl as liveFrameUrl, getDetections, getNotes, getRun, getTimeline, getVerdict } from "./api";
import { subscribe as subscribeEvents } from "./events";
import { type EventData, type RunSnapshot, SnapshotStore } from "./run-snapshot";
import type { DetectionOutline } from "./types";

// Where a Run view gets its data (spec §9.3): the live worker over REST + SSE now; a static bundle for the
// public replay later. Both give the same snapshot shape.

export type { RunSnapshot };

export interface RunSource {
  load(): Promise<RunSnapshot>;
  subscribe(onChange: (snapshot: RunSnapshot) => void): () => void;
  frameUrl(frameId: string, width?: number): string;
  detections(frameId: string): Promise<DetectionOutline[]>;
}

export class LiveSource implements RunSource {
  private onChange: ((snapshot: RunSnapshot) => void) | null = null;
  private readonly store = new SnapshotStore((snapshot) => this.onChange?.(snapshot));
  private outlines = new Map<string, Promise<DetectionOutline[]>>();

  /** `onOtherRun` hears of events from runs other than this one (a new run of the same experiment, say). */
  constructor(
    readonly runId: string,
    private readonly onOtherRun?: (runId: string) => void,
  ) {}

  /** The first load and every resync; events published meanwhile wait in the store and are kept. */
  async load(): Promise<RunSnapshot> {
    this.store.beginLoad();
    try {
      const [view, timeline, notes, verdict] = await Promise.all([
        getRun(this.runId),
        getTimeline(this.runId),
        getNotes(this.runId),
        getVerdict(this.runId),
      ]);
      return this.store.finishLoad(view, timeline, { notes, verdict });
    } catch (error) {
      this.store.failLoad();
      throw error;
    }
  }

  /** Listen before loading, so nothing published in between is lost. */
  subscribe(onChange: (snapshot: RunSnapshot) => void): () => void {
    this.onChange = onChange;
    const stop = subscribeEvents((type, data) => {
      const payload = data as EventData;
      if (type === "resync") {
        this.load().catch(() => undefined); // the next resync tries again
        return;
      }
      if (payload.run_id !== this.runId) {
        if (typeof payload.run_id === "string") this.onOtherRun?.(payload.run_id);
        return;
      }
      if (type === "run_status") {
        // The run ended: fetch its final state (status, end time, spend).
        getRun(this.runId)
          .then((view) => this.store.replaceView(view))
          .catch(() => undefined);
        return;
      }
      this.store.receive(type, payload);
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
}
