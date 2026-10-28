import type { DetectionOutline, Experiment, RecipeSummary, RunView, Timeline } from "./types";

// An empty NEXT_PUBLIC_ARGUS_API counts as unset, as it does for the worker's settings.
export function apiBase(): string {
  return process.env.NEXT_PUBLIC_ARGUS_API || "http://localhost:8000";
}

/** status 0 means the worker could not be reached at all. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(status ? `${status}: ${detail}` : detail);
    this.name = "ApiError";
  }
}

// FastAPI sends `detail` as a string for our own errors and as a list of {msg} for validation errors.
function detailOf(body: unknown, fallback: string): string {
  const detail = body && typeof body === "object" && "detail" in body ? body.detail : undefined;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => (item && typeof item === "object" && "msg" in item ? String(item.msg) : "")).join("; ");
  }
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBase()}${path}`, {
      ...init,
      cache: "no-store",
      headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}) },
    });
  } catch {
    throw new ApiError(0, `Couldn't reach the Argus worker at ${apiBase()}`);
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, detailOf(body, response.statusText));
  return body as T;
}

export function getExperiments(): Promise<Experiment[]> {
  return request("/api/experiments");
}

export function getRecipes(): Promise<RecipeSummary[]> {
  return request("/api/recipes");
}

export function createExperiment(title: string, recipeId: string): Promise<Experiment> {
  return request("/api/experiments", { method: "POST", body: JSON.stringify({ title, recipe_id: recipeId }) });
}

export function getExperiment(id: string): Promise<Experiment> {
  return request(`/api/experiments/${encodeURIComponent(id)}`);
}

export function getRuns(experimentId: string): Promise<RunView[]> {
  return request(`/api/experiments/${encodeURIComponent(experimentId)}/runs`);
}

export function getRun(runId: string): Promise<RunView> {
  return request(`/api/runs/${encodeURIComponent(runId)}`);
}

export function getTimeline(runId: string): Promise<Timeline> {
  return request(`/api/runs/${encodeURIComponent(runId)}/timeline`);
}

export function getDetections(runId: string, frameId: string): Promise<DetectionOutline[]> {
  return request(`/api/runs/${encodeURIComponent(runId)}/frames/${encodeURIComponent(frameId)}/detections`);
}

export function stopRun(runId: string): Promise<RunView> {
  return request(`/api/runs/${encodeURIComponent(runId)}/stop`, { method: "POST" });
}

export function frameUrl(runId: string, frameId: string, width?: number): string {
  const path = `/api/runs/${encodeURIComponent(runId)}/frames/${encodeURIComponent(frameId)}.jpg`;
  return `${apiBase()}${path}${width ? `?w=${width}` : ""}`;
}
