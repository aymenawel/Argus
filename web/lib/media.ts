import type { MediaState } from "./types";

// What the Videos card says about each video (spec §10): the worker's state, put into words.

export function formatBytes(bytes: number): string {
  return `${(bytes / 1_000_000).toFixed(1)} MB`;
}

export type VideoRow = { status: string; action: "make" | "again" | null; download: boolean };

/** In a replay (readOnly) nothing can be made: only a video the bundle carries can be downloaded. */
export function videoRow(state: MediaState, readOnly: boolean): VideoRow {
  switch (state.state) {
    case "none":
      return readOnly
        ? { status: "Not made for this run", action: null, download: false }
        : { status: "Not made yet", action: "make", download: false };
    case "running":
      return { status: `Making… ${Math.round(state.progress * 100)} %`, action: null, download: false };
    case "ready":
      return { status: formatBytes(state.size_bytes), action: readOnly ? null : "again", download: true };
    case "failed":
      return { status: `Failed: ${state.reason}`, action: readOnly ? null : "again", download: false };
  }
}
