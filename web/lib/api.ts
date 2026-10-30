import type {
  Agreement,
  DetectionOutline,
  Experiment,
  FitsView,
  FrameRequest,
  NextRun,
  Note,
  NotesView,
  Plan,
  PlanDraft,
  Preview,
  ReasoningPreference,
  RecipeDetail,
  RecipeDraft,
  RecipeDraftResult,
  RecipeSpec,
  RecipeSummary,
  Review,
  ReviewDraft,
  RunCreate,
  RunView,
  Setup,
  Timeline,
  Tool,
  Verdict,
  VesselProposal,
} from "./types";

// An empty NEXT_PUBLIC_ARGUS_API counts as unset, as it does for the worker's settings.
export function apiBase(): string {
  return process.env.NEXT_PUBLIC_ARGUS_API || "http://localhost:8000";
}

/** status 0 means the worker could not be reached at all. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  // Plain fields, not parameter properties, so the node test runner can load this file.
  constructor(status: number, detail: string) {
    super(status ? `${status}: ${detail}` : detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

// FastAPI sends `detail` as a string for our own errors and as a list of {msg} for validation errors; a refused
// recipe sends its reasons as a list of strings.
export function detailOf(body: unknown, fallback: string): string {
  const detail = body && typeof body === "object" && "detail" in body ? body.detail : undefined;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) =>
        typeof item === "string" ? item : item && typeof item === "object" && "msg" in item ? String(item.msg) : "",
      )
      .join("; ");
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

export function getRecipe(id: string): Promise<RecipeDetail> {
  return request(`/api/recipes/${encodeURIComponent(id)}`);
}

/** From a template by id, or with its own recipe (drafted from the researcher's words) and the plan drafted with it. */
export function createExperiment(
  title: string,
  recipe: string | { recipe: RecipeSpec; plan: PlanDraft },
): Promise<Experiment> {
  const body = typeof recipe === "string" ? { title, recipe_id: recipe } : { title, ...recipe };
  return request("/api/experiments", { method: "POST", body: JSON.stringify(body) });
}

export function getToolbox(): Promise<Tool[]> {
  return request("/api/toolbox");
}

/** A 422 lists why the words couldn't become a recipe Argus can run; a 503 means reasoning is off. */
export function draftRecipe(words: string): Promise<RecipeDraftResult> {
  return request("/api/experiments/draft", { method: "POST", body: JSON.stringify({ words }) });
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

const experimentPath = (id: string) => `/api/experiments/${encodeURIComponent(id)}`;
const runPath = (id: string) => `/api/runs/${encodeURIComponent(id)}`;
const send = (method: string, body?: unknown): RequestInit => ({
  method,
  ...(body === undefined ? {} : { body: JSON.stringify(body) }),
});

// ---- Notes, verdicts and reviews ----

export function getNotes(runId: string): Promise<NotesView> {
  return request(`${runPath(runId)}/notes`);
}

export function postNote(
  runId: string,
  note: { t: number; tag: NonNullable<Note["tag"]>; text: string },
): Promise<Note> {
  return request(`${runPath(runId)}/notes`, send("POST", note));
}

export function getVerdict(runId: string): Promise<Verdict | null> {
  return request(`${runPath(runId)}/verdict`);
}

/** A 409 says why no verdict can be given now (no locked plan, the spend cap). */
export function askVerdict(runId: string): Promise<Verdict> {
  return request(`${runPath(runId)}/verdict`, send("POST"));
}

/** Null when the run has no labels for this metric (only published data carries them). */
export function getAgreement(runId: string, metric: string): Promise<Agreement | null> {
  return request(`${runPath(runId)}/agreement?metric=${encodeURIComponent(metric)}`);
}

// ---- Results ----

/** Each vessel's readings and fitted curve; the plan's metric unless `metric` is given. */
export function getFits(runId: string, metric?: string): Promise<FitsView> {
  const query = metric ? `?metric=${encodeURIComponent(metric)}` : "";
  return request(`${runPath(runId)}/fits${query}`);
}

/** The latest next-run suggestion for a run, or null. */
export function getNextRun(runId: string): Promise<NextRun | null> {
  return request(`${runPath(runId)}/next-run`);
}

/** A new suggestion: code's numbers, explained by Muse Wonder (409 while the run is still going). */
export function suggestNextRun(runId: string): Promise<NextRun> {
  return request(`${runPath(runId)}/next-run`, send("POST"));
}

// ---- Preferences ----

export function getReasoningPreference(): Promise<ReasoningPreference> {
  return request("/api/preferences/reasoning");
}

/** A 422 says which key is missing from the worker's .env. */
export function putReasoningPreference(provider: ReasoningPreference["provider"]): Promise<ReasoningPreference> {
  return request("/api/preferences/reasoning", send("PUT", { provider }));
}

export function getReviews(runId: string): Promise<Review[]> {
  return request(`${runPath(runId)}/reviews`);
}

export function postReview(runId: string, review: ReviewDraft): Promise<Review> {
  return request(`${runPath(runId)}/reviews`, send("POST", review));
}

// ---- Setup, plan and start ----

export function getExperimentRecipe(experimentId: string): Promise<RecipeSpec> {
  return request(`${experimentPath(experimentId)}/recipe`);
}

/** What the wizard offers for the experiment's recipe, its own or a template. */
export function getExperimentRecipeDetail(experimentId: string): Promise<RecipeDetail> {
  return request(`${experimentPath(experimentId)}/recipe/detail`);
}

/** A 409 once the plan is locked: the recipe is frozen with it. */
export function putExperimentRecipe(experimentId: string, recipe: RecipeSpec): Promise<RecipeSpec> {
  return request(`${experimentPath(experimentId)}/recipe`, send("PUT", recipe));
}

export function getSetup(experimentId: string): Promise<Setup> {
  return request(`${experimentPath(experimentId)}/setup`);
}

export function putSetup(experimentId: string, setup: Setup): Promise<Setup> {
  return request(`${experimentPath(experimentId)}/setup`, send("PUT", setup));
}

export function describe(experimentId: string, words: string): Promise<RecipeDraft> {
  return request(`${experimentPath(experimentId)}/describe`, send("POST", { words }));
}

export function preview(experimentId: string, frame: FrameRequest): Promise<Preview> {
  return request(`${experimentPath(experimentId)}/preview`, send("POST", frame));
}

export function getPlans(experimentId: string): Promise<Plan[]> {
  return request(`${experimentPath(experimentId)}/plan`);
}

export function putPlan(experimentId: string, plan: PlanDraft): Promise<Plan> {
  return request(`${experimentPath(experimentId)}/plan`, send("PUT", plan));
}

export function lockPlan(experimentId: string): Promise<Plan> {
  return request(`${experimentPath(experimentId)}/plan/lock`, send("POST"));
}

export function startRun(experimentId: string, body: RunCreate): Promise<RunView> {
  return request(`${experimentPath(experimentId)}/runs`, send("POST", body));
}

// ---- Cameras and vessel detection ----

export function getCameras(): Promise<{ index: number }[]> {
  return request("/api/cameras");
}

export function cameraStreamUrl(index: number): string {
  return `${apiBase()}/api/cameras/${index}/stream.mjpg`;
}

export function detectVessels(
  experimentId: string,
  body: FrameRequest & { concept: string },
): Promise<VesselProposal[]> {
  return request(`${experimentPath(experimentId)}/vessels/detect`, send("POST", body));
}

/** A plain frame from the source as an object URL (revoke it when it's replaced): no segmentation, no cost. */
export async function frameFromSource(experimentId: string, frame: FrameRequest): Promise<string> {
  let response: Response;
  try {
    response = await fetch(`${apiBase()}${experimentPath(experimentId)}/frame`, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(frame),
    });
  } catch {
    throw new ApiError(0, `Couldn't reach the Argus worker at ${apiBase()}`);
  }
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    throw new ApiError(response.status, detailOf(body, response.statusText));
  }
  return URL.createObjectURL(await response.blob());
}
