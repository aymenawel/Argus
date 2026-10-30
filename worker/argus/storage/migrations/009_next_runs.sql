-- Phase 4 (D-80): the next-run suggestion. Code's numbers (replicates, run length, levels), the model's reasons and
-- the refs and model calls behind them. Append-only like verdicts: a new suggestion is a new row.

CREATE TABLE next_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    t REAL NOT NULL,
    numbers TEXT NOT NULL,
    body TEXT NOT NULL,
    refs TEXT NOT NULL,
    model_call_ids TEXT NOT NULL,
    fell_back INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX next_runs_run_t ON next_runs(run_id, t);

CREATE TRIGGER next_runs_no_update BEFORE UPDATE ON next_runs
BEGIN
    SELECT RAISE(ABORT, 'next-run suggestions are evidence');
END;
CREATE TRIGGER next_runs_no_delete BEFORE DELETE ON next_runs
BEGIN
    SELECT RAISE(ABORT, 'next-run suggestions are evidence');
END;
CREATE TRIGGER next_runs_no_replace BEFORE INSERT ON next_runs
WHEN EXISTS (SELECT 1 FROM next_runs WHERE id = NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'next-run suggestions are evidence');
END;
