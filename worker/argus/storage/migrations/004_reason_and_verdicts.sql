-- Phase 3 (spec §5, §7): the structured prediction a verdict is judged against, the setup wizard's draft, and
-- the explanation layer: derived numbers, notes, every note attempt, verdicts and researcher reviews.
-- Derived numbers, note attempts, verdicts and reviews are append-only; a note may only move its end time
-- later, as quiet "no change" notes collapse into one.

ALTER TABLE plans ADD COLUMN metric TEXT;
ALTER TABLE plans ADD COLUMN direction TEXT;
ALTER TABLE plans ADD COLUMN min_effect REAL;
ALTER TABLE plans ADD COLUMN checkpoint_s REAL;
ALTER TABLE plans ADD COLUMN treatment TEXT;

CREATE TABLE setups (
    experiment_id TEXT PRIMARY KEY REFERENCES experiments(id),
    body TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE derived (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    t REAL NOT NULL,
    kind TEXT NOT NULL,
    label TEXT NOT NULL,
    value REAL NOT NULL,
    uncertainty REAL NOT NULL,
    unit TEXT NOT NULL,
    inputs TEXT NOT NULL,
    method_version TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX derived_run_t ON derived(run_id, t);

CREATE TABLE notes (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    t REAL NOT NULL,
    t_end REAL,
    author TEXT NOT NULL,
    level TEXT,
    tag TEXT,
    body TEXT NOT NULL,
    refs TEXT NOT NULL,
    evidence TEXT NOT NULL,
    check_status TEXT NOT NULL,
    model_call_id TEXT REFERENCES model_calls(id),
    created_at TEXT NOT NULL
);
CREATE INDEX notes_run_t ON notes(run_id, t);

CREATE TABLE note_attempts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    t REAL NOT NULL,
    attempt INTEGER NOT NULL,
    raw TEXT NOT NULL,
    reasons TEXT NOT NULL,
    passed INTEGER NOT NULL,
    model_call_id TEXT REFERENCES model_calls(id),
    created_at TEXT NOT NULL
);
CREATE INDEX note_attempts_run_t ON note_attempts(run_id, t);

CREATE TABLE verdicts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    t REAL NOT NULL,
    provisional INTEGER NOT NULL,
    allowed TEXT NOT NULL,
    checks TEXT NOT NULL,
    verdict TEXT NOT NULL,
    body TEXT NOT NULL,
    draft TEXT NOT NULL,
    critique TEXT,
    refs TEXT NOT NULL,
    model_call_ids TEXT NOT NULL,
    fell_back INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX verdicts_run_t ON verdicts(run_id, t);

CREATE TABLE reviews (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    t REAL NOT NULL,
    target_kind TEXT NOT NULL,
    target_id TEXT NOT NULL,
    action TEXT NOT NULL,
    comment TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX reviews_run_t ON reviews(run_id, t);

-- Derived numbers
CREATE TRIGGER derived_no_update BEFORE UPDATE ON derived
BEGIN
    SELECT RAISE(ABORT, 'derived numbers are evidence');
END;
CREATE TRIGGER derived_no_delete BEFORE DELETE ON derived
BEGIN
    SELECT RAISE(ABORT, 'derived numbers are evidence');
END;
CREATE TRIGGER derived_no_replace BEFORE INSERT ON derived
WHEN EXISTS (SELECT 1 FROM derived WHERE id = NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'derived numbers are evidence');
END;

-- Notes: a note's end time may only move later; nothing else changes
CREATE TRIGGER notes_end_later BEFORE UPDATE ON notes
WHEN NEW.t_end IS NULL OR (OLD.t_end IS NOT NULL AND NEW.t_end < OLD.t_end)
    OR NEW.id IS NOT OLD.id OR NEW.run_id IS NOT OLD.run_id OR NEW.t IS NOT OLD.t
    OR NEW.author IS NOT OLD.author OR NEW.level IS NOT OLD.level OR NEW.tag IS NOT OLD.tag
    OR NEW.body IS NOT OLD.body OR NEW.refs IS NOT OLD.refs OR NEW.evidence IS NOT OLD.evidence
    OR NEW.check_status IS NOT OLD.check_status OR NEW.model_call_id IS NOT OLD.model_call_id
    OR NEW.created_at IS NOT OLD.created_at
BEGIN
    SELECT RAISE(ABORT, 'notes are evidence');
END;
CREATE TRIGGER notes_no_delete BEFORE DELETE ON notes
BEGIN
    SELECT RAISE(ABORT, 'notes are evidence');
END;
CREATE TRIGGER notes_no_replace BEFORE INSERT ON notes
WHEN EXISTS (SELECT 1 FROM notes WHERE id = NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'notes are evidence');
END;

-- Note attempts
CREATE TRIGGER note_attempts_no_update BEFORE UPDATE ON note_attempts
BEGIN
    SELECT RAISE(ABORT, 'note attempts are evidence');
END;
CREATE TRIGGER note_attempts_no_delete BEFORE DELETE ON note_attempts
BEGIN
    SELECT RAISE(ABORT, 'note attempts are evidence');
END;
CREATE TRIGGER note_attempts_no_replace BEFORE INSERT ON note_attempts
WHEN EXISTS (SELECT 1 FROM note_attempts WHERE id = NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'note attempts are evidence');
END;

-- Verdicts
CREATE TRIGGER verdicts_no_update BEFORE UPDATE ON verdicts
BEGIN
    SELECT RAISE(ABORT, 'verdicts are evidence');
END;
CREATE TRIGGER verdicts_no_delete BEFORE DELETE ON verdicts
BEGIN
    SELECT RAISE(ABORT, 'verdicts are evidence');
END;
CREATE TRIGGER verdicts_no_replace BEFORE INSERT ON verdicts
WHEN EXISTS (SELECT 1 FROM verdicts WHERE id = NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'verdicts are evidence');
END;

-- Reviews
CREATE TRIGGER reviews_no_update BEFORE UPDATE ON reviews
BEGIN
    SELECT RAISE(ABORT, 'reviews are evidence');
END;
CREATE TRIGGER reviews_no_delete BEFORE DELETE ON reviews
BEGIN
    SELECT RAISE(ABORT, 'reviews are evidence');
END;
CREATE TRIGGER reviews_no_replace BEFORE INSERT ON reviews
WHEN EXISTS (SELECT 1 FROM reviews WHERE id = NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'reviews are evidence');
END;
