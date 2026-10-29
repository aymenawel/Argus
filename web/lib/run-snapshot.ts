import type {
  FrameRow,
  MeasurementRow,
  Note,
  NotesView,
  RunEvent,
  RunProgress,
  RunView,
  Timeline,
  Verdict,
} from "./types";

// One run's data as the Run view sees it, kept current from REST loads and SSE events. Plain TypeScript with
// type-only imports, so Node's test runner can load it as it is.

export type RunSnapshot = {
  view: RunView;
  frames: FrameRow[]; // sorted by t
  measurements: MeasurementRow[]; // sorted by t
  events: RunEvent[];
  progress: RunProgress | null;
  notes: Note[]; // sorted by t
  rejected: number; // AI answers the claim checker turned back
  verdict: Verdict | null; // the latest
};

/** What a load brings besides the view and the timeline. */
export type RunExtras = { notes: NotesView; verdict: Verdict | null };

const NO_EXTRAS: RunExtras = { notes: { notes: [], rejected: 0 }, verdict: null };

export type EventData = Record<string, unknown> & { run_id?: string };

type Schedule = (flush: () => void) => void;

const byT = <T extends { t: number }>(a: T, b: T) => a.t - b.t;

const nextFrame: Schedule = (flush) => {
  if (typeof requestAnimationFrame === "function") requestAnimationFrame(() => flush());
  else setTimeout(flush, 16);
};

/** Events that arrive while a load is in flight (the first one, or a resync's) wait and go on top of it, so
 *  nothing published meanwhile is lost. Updates are batched: a burst of events in one animation frame makes
 *  one new snapshot, built by appending (one sort only if something arrived out of order). */
export class SnapshotStore {
  private snapshot: RunSnapshot | null = null;
  private loads = 0;
  private waiting: [string, EventData][] = [];
  private queue: [string, EventData][] = [];
  private scheduled = false;
  private measurementIds = new Set<string>();
  private readonly onChange: (snapshot: RunSnapshot) => void;
  private readonly schedule: Schedule;

  constructor(onChange: (snapshot: RunSnapshot) => void, schedule: Schedule = nextFrame) {
    this.onChange = onChange;
    this.schedule = schedule;
  }

  current(): RunSnapshot | null {
    return this.snapshot;
  }

  beginLoad(): void {
    this.loads += 1;
  }

  failLoad(): void {
    this.loads = Math.max(0, this.loads - 1);
  }

  finishLoad(view: RunView, timeline: Timeline, extras: RunExtras = NO_EXTRAS): RunSnapshot {
    this.loads = Math.max(0, this.loads - 1);
    const measurements = [...timeline.measurements].sort(byT);
    this.measurementIds = new Set(measurements.map((m) => m.id));
    this.snapshot = {
      view,
      frames: [...timeline.frames].sort(byT),
      measurements,
      events: [...timeline.events],
      progress: null,
      notes: [...extras.notes.notes].sort(byT),
      rejected: extras.notes.rejected,
      verdict: extras.verdict,
    };
    if (this.loads === 0 && this.waiting.length > 0) {
      const waiting = this.waiting;
      this.waiting = [];
      this.snapshot = this.applyAll(this.snapshot, waiting);
    }
    this.onChange(this.snapshot);
    return this.snapshot;
  }

  /** The run's final state after it ended (status, end time, spend). */
  replaceView(view: RunView): void {
    if (this.snapshot === null) return;
    this.snapshot = { ...this.snapshot, view, progress: null };
    this.onChange(this.snapshot);
  }

  receive(type: string, data: EventData): void {
    if (this.snapshot === null || this.loads > 0) {
      this.waiting.push([type, data]);
      return;
    }
    this.queue.push([type, data]);
    if (!this.scheduled) {
      this.scheduled = true;
      this.schedule(() => this.flush());
    }
  }

  private flush(): void {
    this.scheduled = false;
    const queued = this.queue;
    this.queue = [];
    if (this.snapshot === null || queued.length === 0) return;
    const next = this.applyAll(this.snapshot, queued);
    if (next === this.snapshot) return;
    this.snapshot = next;
    this.onChange(next);
  }

  private applyAll(s: RunSnapshot, items: [string, EventData][]): RunSnapshot {
    let measurements: MeasurementRow[] | null = null;
    let measurementsSorted = true;
    let frames: FrameRow[] | null = null;
    let events: RunEvent[] | null = null;
    let notes: Note[] | null = null;
    let rejected = s.rejected;
    let verdict = s.verdict;
    let progress = s.progress;
    let view = s.view;

    for (const [type, data] of items) {
      if (type === "measurement") {
        const row = data as unknown as MeasurementRow;
        if (this.measurementIds.has(row.id)) continue;
        this.measurementIds.add(row.id);
        measurements ??= s.measurements.slice();
        const last = measurements.at(-1);
        if (last && row.t < last.t) measurementsSorted = false;
        measurements.push(row);
      } else if (type === "frame_analyzed") {
        const frame: FrameRow = {
          id: String(data.frame_id),
          t: Number(data.t),
          analyzed: true,
          quality_flags: (data.quality_flags as string[]) ?? [],
        };
        frames ??= s.frames.slice();
        const at = frames.findLastIndex((f) => f.id === frame.id);
        if (at >= 0) frames[at] = frame;
        else if (frames.length === 0 || frames[frames.length - 1].t <= frame.t) frames.push(frame);
        else frames = [...frames, frame].sort(byT);
      } else if (type === "event") {
        events ??= s.events.slice();
        const at = events.findIndex((e) => e.id === String(data.id));
        if (at >= 0) {
          const end = data.t_end == null ? events[at].t_end : Number(data.t_end);
          events[at] = { ...events[at], t_end: end }; // an open event closing
        } else {
          events.push({
            id: String(data.id),
            vessel_id: (data.vessel_id as string | null) ?? null,
            t_start: Number(data.t),
            t_end: data.t_end == null ? null : Number(data.t_end),
            kind: data.kind as RunEvent["kind"],
            source: "",
            detail: (data.detail as Record<string, unknown>) ?? {},
          });
        }
      } else if (type === "run_progress") {
        progress = data as unknown as RunProgress;
      } else if (type === "spend") {
        view = { ...view, spend_usd: Number(data.spent_usd) };
      } else if (type === "note") {
        // A quiet note that goes on comes again with a later end time: it replaces itself.
        const note = data.note as Note;
        notes ??= s.notes.slice();
        const at = notes.findIndex((n) => n.id === note.id);
        if (at >= 0) notes[at] = note;
        else if (notes.length === 0 || notes[notes.length - 1].t <= note.t) notes.push(note);
        else notes = [...notes, note].sort(byT);
      } else if (type === "note_rejected") {
        rejected += 1;
      } else if (type === "verdict") {
        verdict = data.verdict as Verdict;
      }
    }

    if (measurements && !measurementsSorted) measurements.sort(byT);
    const same = progress === s.progress && view === s.view && rejected === s.rejected && verdict === s.verdict;
    if (!measurements && !frames && !events && !notes && same) return s;
    return {
      view,
      progress,
      rejected,
      verdict,
      notes: notes ?? s.notes,
      measurements: measurements ?? s.measurements,
      frames: frames ?? s.frames,
      events: events ?? s.events,
    };
  }
}
