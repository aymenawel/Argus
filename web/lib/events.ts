import { apiBase } from "./api";

// Server-sent event types the UI listens for. EventSource only delivers named events to listeners
// registered by name, so each new type the worker publishes is added here.
export const EVENT_TYPES = [
  "experiment",
  "resync",
  "measurement",
  "frame_analyzed",
  "event",
  "run_progress",
  "run_status",
  "spend",
] as const;

/**
 * Listen to the worker's event stream. On a dropped connection the browser reconnects by itself
 * and sends Last-Event-ID, and the worker replays what was missed. When it can't (the worker restarted,
 * or too much was missed) it sends `resync`, and the listener should reload what it shows.
 */
export function subscribe(onEvent: (type: string, data: unknown) => void): () => void {
  const source = new EventSource(`${apiBase()}/api/events`);
  const handle = (event: MessageEvent<string>) => {
    let data: unknown;
    try {
      data = JSON.parse(event.data);
    } catch {
      return; // not ours to guess at
    }
    onEvent(event.type, data);
  };
  for (const type of EVENT_TYPES) source.addEventListener(type, handle);
  return () => source.close();
}
