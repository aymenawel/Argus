"use client";

import { useSyncExternalStore } from "react";

// One playhead for the Run view (spec §9.3): the time everything shows, whether it follows the newest frame,
// and the selected vessel. Components read slices of it with usePlayhead(selector).

export type Playhead = { t: number; follow: boolean; selectedVesselId: string | null };

const initial: Playhead = { t: 0, follow: true, selectedVesselId: null };
let state: Playhead = initial;
const listeners = new Set<() => void>();

function set(next: Partial<Playhead>) {
  state = { ...state, ...next };
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Selectors must return a primitive or a stable value, so React can compare snapshots. */
export function usePlayhead<T>(selector: (playhead: Playhead) => T): T {
  return useSyncExternalStore(
    subscribe,
    () => selector(state),
    () => selector(initial),
  );
}

export const playhead = {
  get: () => state,
  /** Looking at a moment: stop following the newest frame. */
  setT: (t: number) => set({ t, follow: false }),
  followLive: () => set({ follow: true }),
  /** Called when a newer frame arrives; moves the playhead only while following. */
  sync: (newestT: number) => {
    if (state.follow && state.t !== newestT) set({ t: newestT });
  },
  selectVessel: (id: string | null) => set({ selectedVesselId: id }),
  reset: () => set(initial),
};
