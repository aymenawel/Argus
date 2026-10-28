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

export type RunStatus = "running" | "finished" | "stopped";

export type Run = {
  id: string;
  experiment_id: string;
  mode: RunMode;
  status: RunStatus;
  source: { kind: "webcam" | "video"; camera_index: number | null; paths: string[]; start_time: string | null };
  time_scale: number;
  round: number;
  started_at: string;
  ended_at: string | null;
};

export type Vessel = {
  id: string;
  run_id: string;
  label: string;
  role: "control" | "treatment";
  blind_label: string | null;
  condition: { factor: string; value: number | string; unit: string | null } | null;
  roi: [number, number][];
};

export type Calibration = {
  id: string;
  t: number;
  card: "standard" | "compact" | "ruler";
  mm_per_px: number;
  rel_uncertainty: number;
  print_scale: number;
  camera_properties: Record<string, "locked" | "not_locked" | "unknown">;
};

export type RunView = {
  run: Run;
  vessels: Vessel[];
  calibration: Calibration | null;
  spend_usd: number;
  running: boolean;
};

export type FrameRow = { id: string; t: number; analyzed: boolean; quality_flags: string[] };

export type MeasurementRow = {
  id: string;
  vessel_id: string;
  frame_id: string | null;
  t: number;
  metric: string;
  value: number;
  uncertainty: number;
  unit: string;
  method_version?: string;
  display: string; // formatted by the worker, with ±
};

export type RunEventKind =
  | "first"
  | "change"
  | "checkin"
  | "tick"
  | "intervention"
  | "quality"
  | "camera_moved"
  | "no_calibration"
  | "segment_failed"
  | "spend"
  | "interrupted";

export type RunEvent = {
  id: string;
  vessel_id: string | null;
  t_start: number;
  t_end: number | null;
  kind: RunEventKind;
  source: string;
  detail: Record<string, unknown>;
};

export type DetectionOutline = {
  vessel_id: string;
  track_key: string;
  concept: string;
  outline: [number, number][][];
  confidence: number | null;
};

export type RunProgress = {
  stage: "scan" | "segment" | "measure";
  t?: number;
  t_end?: number | null;
  speed?: number;
  done?: number;
  total?: number;
};

export type Timeline = { frames: FrameRow[]; measurements: MeasurementRow[]; events: RunEvent[] };
