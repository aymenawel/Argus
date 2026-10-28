// Hand-written mirrors of the worker's models (worker/argus/domain.py, worker/argus/api/app.py)
// until generated types are approved.

export type RunMode = "live" | "imported" | "replay";

export type VerdictLevel = "SUPPORTED" | "NOT_SUPPORTED" | "INCONCLUSIVE" | "TOO_EARLY";

export type ExperimentStatus = "draft" | "locked" | "running" | "finished";

export type Experiment = {
  id: string;
  title: string;
  recipe_id: string;
  recipe_version: number;
  status: ExperimentStatus;
  created_at: string; // ISO 8601, UTC
};

export type RecipeSummary = {
  id: string;
  version: number;
  title: string;
  main_measurement: string;
};
