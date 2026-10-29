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
  | "interrupted"
  | "rule";

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

export type Role = "control" | "treatment";

export type Direction = "higher" | "lower";

export type Condition = { factor: string; value: number | string; unit: string | null };

export type RulerInput = { p1: [number, number]; p2: [number, number]; distance_mm: number };

// ---- Notes, verdicts and reviews (worker/argus/api/notes.py) ----

/** Every text field is rendered by the worker: numbers come from refs, never from the model. */
export type NoteBody = {
  observation?: string;
  interpretation?: string;
  hypothesis_status?: VerdictLevel | null;
  confidence?: "low" | "medium" | "high" | null;
  confidence_reason?: string;
  rival_explanations?: string[];
  next_step?: string;
  question_for_researcher?: string;
  written_by?: "model" | "code";
  reason?: string; // why code wrote it
  text?: string; // a researcher's note, as written
};

export type Note = {
  id: string;
  run_id: string;
  t: number;
  t_end: number | null; // a quiet note that went on
  author: "ai" | "researcher";
  level: "event" | "checkpoint" | "insight" | null;
  tag: "observation" | "intervention" | "question" | null;
  body: NoteBody;
  refs: string[];
  evidence: string[];
  check_status: "passed" | "fallback" | "researcher";
  model_call_id: string | null;
};

export type NotesView = { notes: Note[]; rejected: number };

export type Check = { id: string; ok: boolean | null; text: string; refs: string[] };

export type VerdictBody = {
  explanation: string;
  rivals: { name: string; status: string; reason: string }[];
  what_would_change_it: string;
  confidence: "low" | "medium" | "high" | null;
  confidence_reason: string;
  findings: { item: string; problem: string; consequence: string; fix: string }[];
  written_by: "model" | "code";
  critique_dropped: string[];
};

export type Verdict = {
  id: string;
  run_id: string;
  t: number;
  provisional: boolean;
  allowed: VerdictLevel[];
  checks: Check[];
  verdict: VerdictLevel;
  body: VerdictBody;
  draft: Record<string, unknown>;
  critique: Record<string, unknown> | null;
  refs: string[];
  model_call_ids: string[];
  fell_back: boolean;
};

export type ReviewDraft = {
  t: number;
  target_kind: "note" | "verdict" | "rival" | "event";
  target_id: string;
  action: "confirm" | "dismiss" | "correct" | "resolve";
  comment: string;
};

export type Review = ReviewDraft & { id: string; run_id: string };

// ---- Setup and plan (worker/argus/api/setup.py) ----

export type PlanDraft = {
  hypothesis: string;
  prediction: string;
  threshold: string;
  rivals: string[];
  metric: string | null;
  direction: Direction | null;
  min_effect: number | null;
  checkpoint_s: number | null;
  treatment: string | null;
};

export type Plan = PlanDraft & {
  experiment_id: string;
  version: number;
  locked_at: string | null;
  sha256: string | null;
};

export type VesselDraft = {
  label: string;
  role: Role;
  blind_label?: string | null;
  condition: Condition | null;
  roi: [number, number][];
};

export type SetupSource = { kind: "webcam" | "video"; camera_index: number | null; paths: string[] };

export type Setup = {
  source: SetupSource | null;
  time_scale: number;
  vessels: VesselDraft[];
  print_check_mm: number | null;
  ruler: RulerInput | null;
  factor: string | null;
  factor_unit: string | null;
};

/** Muse Spark's draft from the researcher's words; nothing is saved until they accept it. */
export type RecipeDraft = {
  hypothesis: string;
  prediction: string;
  threshold: string;
  metric: string;
  direction: Direction;
  min_effect: number;
  checkpoint_s: number;
  treatment: string;
  factor: string;
  factor_unit: string;
  conditions: { value: string; role: Role }[];
  rivals: string[];
  question_for_researcher: string;
};

export type Preview = {
  frame_jpeg_b64: string;
  calibration: { card: "standard" | "compact" | "ruler"; px_per_mm: number; rel_uncertainty: number } | null;
  quality: { blur: number; flags: string[] };
  vessels: {
    label: string;
    outlines: [number, number][][];
    readings: { metric: string; value: number; unit: string; display: string }[];
  }[];
};

export type RunCreate = {
  mode: "live" | "imported";
  camera_index?: number;
  paths?: string[];
  time_scale?: number;
  start_time?: string;
  vessels?: VesselDraft[]; // left out: the setup's
  print_check_mm?: number;
  ruler?: RulerInput;
};

export type FrameRequest = { camera_index?: number; path?: string; video_s?: number };

export type VesselProposal = { roi: [number, number][]; confidence: number | null };
