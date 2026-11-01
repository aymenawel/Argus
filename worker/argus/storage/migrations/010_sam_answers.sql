-- Fix 1 (D-90): every answer SAM gave per frame, vessel and concept, empty answers included, so how often it found
-- an object is counted from records. Evidence: never changed or removed.

CREATE TABLE sam_answers (
    run_id TEXT NOT NULL REFERENCES runs(id),
    frame_id TEXT NOT NULL REFERENCES frames(id),
    vessel_id TEXT NOT NULL REFERENCES vessels(id),
    concept TEXT NOT NULL,
    found INTEGER NOT NULL CHECK (found >= 0),
    PRIMARY KEY (frame_id, vessel_id, concept)
);
CREATE INDEX sam_answers_run ON sam_answers(run_id);

CREATE TRIGGER sam_answers_no_update BEFORE UPDATE ON sam_answers
BEGIN
    SELECT RAISE(ABORT, 'SAM answers are evidence');
END;
CREATE TRIGGER sam_answers_no_delete BEFORE DELETE ON sam_answers
BEGIN
    SELECT RAISE(ABORT, 'SAM answers are evidence');
END;
CREATE TRIGGER sam_answers_no_replace BEFORE INSERT ON sam_answers
WHEN EXISTS (
    SELECT 1 FROM sam_answers WHERE frame_id = NEW.frame_id AND vessel_id = NEW.vessel_id AND concept = NEW.concept
)
BEGIN
    SELECT RAISE(ABORT, 'SAM answers are evidence');
END;
