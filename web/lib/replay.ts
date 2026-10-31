// The public replay (D-83): the same app, built with NEXT_PUBLIC_ARGUS_REPLAY=1, reads a run bundle the worker
// recorded (`python -m argus export-bundle`) instead of asking the worker. Nothing here imports api.ts.

export type BundleManifest = {
  run_id: string;
  experiment_id: string;
  experiment_title: string;
  source_label: "live recording" | "imported recording" | "published data";
  credit: string | null;
  licence: string | null;
  dataset_url: string | null;
  recorded: string;
  exported_at: string;
  commit: string | null;
  frames: { total: number; shown: number; note: string | null; scale: number }; // scale: original / shown size
  frame_map: Record<string, string>;
  media: string[];
  verdict: string | null;
};

export type BundleIndexEntry = {
  run_id: string;
  experiment_id: string;
  title: string;
  source_label: BundleManifest["source_label"];
  recorded: string;
  verdict: string | null;
};

export type BundleIndex = { runs: BundleIndexEntry[] };

/** Read at call time: Next inlines the value into the build, and the tests set it per case. */
export function isReplay(): boolean {
  return process.env.NEXT_PUBLIC_ARGUS_REPLAY === "1";
}

/** True in replay mode: every control that writes (stop, notes, verdicts, reviews, suggestions, video exports) hides. */
export function useReadOnly(): boolean {
  return isReplay();
}

const SAFE = /^[A-Za-z0-9_.-]+$/;
const safe = (part: string) => SAFE.test(part) && part !== "." && part !== "..";

/** Where a recorded answer lives: the worker's argus/export/paths.py names files by the same rule. */
export function bundleFile(path: string, query: string): string {
  const segments = path.replace(/^\/+|\/+$/g, "").split("/");
  if (!segments.every(safe)) throw new Error(`not a path a bundle can hold: ${path}`);
  const name = segments.join("/");
  if (!query) return `${name}.json`;
  const pairs = query.split("&").map((pair) => {
    const at = pair.indexOf("=");
    const key = at < 0 ? "" : pair.slice(0, at);
    const value = at < 0 ? "" : decodeURIComponent(pair.slice(at + 1));
    if (at < 0 || !safe(key) || !safe(value)) throw new Error(`not a query a bundle can hold: ${pair}`);
    return [key, value] as const;
  });
  pairs.sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
  return `${name}__${pairs.map(([k, v]) => `${k}=${v}`).join("&")}.json`;
}

const OPEN_PREFIXES = ["/replay/", "/bundles/", "/_next/", "/__nextjs"];
const OPEN_PATHS = new Set(["/replay", "/icon.svg", "/apple-icon.png", "/favicon.ico"]);

/** What a visitor may reach in replay mode; proxy.ts sends everything else to /replay. */
export function isReplayPath(pathname: string): boolean {
  return OPEN_PATHS.has(pathname) || OPEN_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

let active: BundleManifest | null = null;

/** The bundle the open replay page reads from (one run per page). */
export function setActiveBundle(manifest: BundleManifest | null): void {
  active = manifest;
}

export function activeBundle(): BundleManifest | null {
  return active;
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`${url} is missing from the replay`);
  return (await response.json()) as T;
}

export async function openBundle(runId: string): Promise<BundleManifest> {
  if (!safe(runId)) throw new Error(`not a run id: ${runId}`);
  const manifest = await fetchJson<BundleManifest>(`/bundles/${runId}/manifest.json`);
  setActiveBundle(manifest);
  return manifest;
}

export function getReplayIndex(): Promise<BundleIndex> {
  return fetchJson<BundleIndex>("/bundles/index.json");
}

/** A thinned bundle keeps some frames; every frame id points at the kept frame shown in its place. */
export function replayFrameUrl(manifest: BundleManifest, frameId: string): string {
  return `/bundles/${manifest.run_id}/frames/${manifest.frame_map[frameId] ?? frameId}.jpg`;
}

/** Regions and outlines are in the original frame's pixels; a bundle's frames may be shrunk (by `frames.scale`). */
export function originalSize(width: number, height: number): { w: number; h: number } {
  const scale = isReplay() ? (active?.frames.scale ?? 1) : 1;
  return { w: Math.round(width * scale), h: Math.round(height * scale) };
}

const DETECTIONS = /^(\/api\/runs\/[^/]+\/frames\/)([^/]+)(\/detections)$/;

/** A frame's outlines are read from the kept frame drawn in its place, so outline and picture always match. */
export function mapFramePath(path: string, manifest: BundleManifest): string {
  const match = DETECTIONS.exec(path);
  if (!match) return path;
  return `${match[1]}${manifest.frame_map[match[2]] ?? match[2]}${match[3]}`;
}
