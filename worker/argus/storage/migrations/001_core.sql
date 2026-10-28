-- Core tables (spec §5). Measurements and locked plans are evidence: triggers refuse to change them.

CREATE TABLE experiments (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    recipe_id TEXT NOT NULL,
    recipe_version INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE plans (
    experiment_id TEXT NOT NULL REFERENCES experiments(id),
    version INTEGER NOT NULL,
    hypothesis TEXT NOT NULL,
    prediction TEXT NOT NULL,
    threshold TEXT NOT NULL,
    rivals TEXT NOT NULL,
    locked_at TEXT,
    sha256 TEXT,
    PRIMARY KEY (experiment_id, version)
);

CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments(id),
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    time_scale REAL NOT NULL,
    round INTEGER NOT NULL,
    started_at TEXT NOT NULL
);

CREATE TABLE vessels (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    label TEXT NOT NULL,
    blind_label TEXT,
    role TEXT NOT NULL,
    condition TEXT,
    roi TEXT NOT NULL
);

CREATE TABLE calibrations (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    t REAL NOT NULL,
    card TEXT,
    homography TEXT,
    mm_per_px REAL,
    rel_uncertainty REAL,
    print_scale REAL NOT NULL DEFAULT 1.0,
    colour_reference TEXT,
    camera_properties TEXT
);

CREATE TABLE frames (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    t REAL NOT NULL,
    path TEXT NOT NULL,
    quality_flags TEXT NOT NULL,
    analyzed INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX frames_run_t ON frames(run_id, t);

CREATE TABLE measurements (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    vessel_id TEXT NOT NULL REFERENCES vessels(id),
    frame_id TEXT REFERENCES frames(id),
    t REAL NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    uncertainty REAL NOT NULL,
    unit TEXT NOT NULL,
    method_version TEXT NOT NULL
);
CREATE INDEX measurements_run_t ON measurements(run_id, t);

CREATE TABLE audit_chain (
    run_id TEXT NOT NULL REFERENCES runs(id),
    batch_index INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    measurement_ids TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (run_id, batch_index)
);

CREATE TRIGGER measurements_no_update BEFORE UPDATE ON measurements
BEGIN
    SELECT RAISE(ABORT, 'measurements are evidence');
END;

CREATE TRIGGER measurements_no_delete BEFORE DELETE ON measurements
BEGIN
    SELECT RAISE(ABORT, 'measurements are evidence');
END;

CREATE TRIGGER plans_locked BEFORE UPDATE ON plans WHEN OLD.locked_at IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'locked plan');
END;
