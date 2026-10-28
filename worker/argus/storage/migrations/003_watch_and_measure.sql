-- Phase 2 (spec §5): where a run's frames come from, SAM detections, run events and the model-call log.
-- Detections, calibrations and frames are evidence: only a frame's `analyzed` flag and an event's
-- `t_end` (once) may change afterwards.

ALTER TABLE runs ADD COLUMN source TEXT NOT NULL DEFAULT '{"kind":"video"}';
ALTER TABLE runs ADD COLUMN ended_at TEXT;

CREATE TABLE detections (
    id TEXT PRIMARY KEY,
    frame_id TEXT NOT NULL REFERENCES frames(id),
    vessel_id TEXT NOT NULL REFERENCES vessels(id),
    track_key TEXT NOT NULL,
    concept TEXT NOT NULL,
    outline TEXT NOT NULL,
    bbox TEXT NOT NULL,
    area_px INTEGER NOT NULL,
    confidence REAL,
    backend TEXT NOT NULL,
    mask_path TEXT NOT NULL
);
CREATE INDEX detections_frame ON detections(frame_id);

CREATE TABLE events (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    vessel_id TEXT REFERENCES vessels(id),
    t_start REAL NOT NULL,
    t_end REAL,
    kind TEXT NOT NULL,
    source TEXT NOT NULL,
    detail TEXT NOT NULL,
    frame_ids TEXT NOT NULL
);
CREATE INDEX events_run_t ON events(run_id, t_start);

CREATE TABLE model_calls (
    id TEXT PRIMARY KEY,
    run_id TEXT REFERENCES runs(id),
    t REAL,
    function TEXT NOT NULL,
    model TEXT NOT NULL,
    tier TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    cached_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    reasoning_tokens INTEGER NOT NULL,
    images INTEGER NOT NULL,
    frames INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    latency_s REAL NOT NULL,
    cache_key TEXT,
    status TEXT NOT NULL,
    error TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX model_calls_run ON model_calls(run_id);

-- Detections
CREATE TRIGGER detections_no_update BEFORE UPDATE ON detections
BEGIN
    SELECT RAISE(ABORT, 'detections are evidence');
END;
CREATE TRIGGER detections_no_delete BEFORE DELETE ON detections
BEGIN
    SELECT RAISE(ABORT, 'detections are evidence');
END;
CREATE TRIGGER detections_no_replace BEFORE INSERT ON detections
WHEN EXISTS (SELECT 1 FROM detections WHERE id = NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'detections are evidence');
END;

-- Calibrations
CREATE TRIGGER calibrations_no_update BEFORE UPDATE ON calibrations
BEGIN
    SELECT RAISE(ABORT, 'calibrations are evidence');
END;
CREATE TRIGGER calibrations_no_delete BEFORE DELETE ON calibrations
BEGIN
    SELECT RAISE(ABORT, 'calibrations are evidence');
END;
CREATE TRIGGER calibrations_no_replace BEFORE INSERT ON calibrations
WHEN EXISTS (SELECT 1 FROM calibrations WHERE id = NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'calibrations are evidence');
END;

-- Frames: only `analyzed` may change
CREATE TRIGGER frames_evidence BEFORE UPDATE OF id, run_id, t, path, quality_flags ON frames
BEGIN
    SELECT RAISE(ABORT, 'frames are evidence');
END;
CREATE TRIGGER frames_no_delete BEFORE DELETE ON frames
BEGIN
    SELECT RAISE(ABORT, 'frames are evidence');
END;
CREATE TRIGGER frames_no_replace BEFORE INSERT ON frames
WHEN EXISTS (SELECT 1 FROM frames WHERE id = NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'frames are evidence');
END;

-- Events: an open event may be closed once; nothing else changes
CREATE TRIGGER events_close_once BEFORE UPDATE ON events
WHEN OLD.t_end IS NOT NULL OR NEW.t_end IS NULL
    OR NEW.id IS NOT OLD.id OR NEW.run_id IS NOT OLD.run_id OR NEW.vessel_id IS NOT OLD.vessel_id
    OR NEW.t_start IS NOT OLD.t_start OR NEW.kind IS NOT OLD.kind OR NEW.source IS NOT OLD.source
    OR NEW.detail IS NOT OLD.detail OR NEW.frame_ids IS NOT OLD.frame_ids
BEGIN
    SELECT RAISE(ABORT, 'events are evidence');
END;
CREATE TRIGGER events_no_delete BEFORE DELETE ON events
BEGIN
    SELECT RAISE(ABORT, 'events are evidence');
END;
CREATE TRIGGER events_no_replace BEFORE INSERT ON events
WHEN EXISTS (SELECT 1 FROM events WHERE id = NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'events are evidence');
END;

-- Model calls: an append-only log
CREATE TRIGGER model_calls_no_update BEFORE UPDATE ON model_calls
BEGIN
    SELECT RAISE(ABORT, 'model calls are a log');
END;
CREATE TRIGGER model_calls_no_delete BEFORE DELETE ON model_calls
BEGIN
    SELECT RAISE(ABORT, 'model calls are a log');
END;
CREATE TRIGGER model_calls_no_replace BEFORE INSERT ON model_calls
WHEN EXISTS (SELECT 1 FROM model_calls WHERE id = NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'model calls are a log');
END;
