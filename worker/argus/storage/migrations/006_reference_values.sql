-- A published dataset's own values (its human labels), stored beside Argus's measurements and never mixed with them:
-- the agreement compares the two (D-71). Rows never change once written.

CREATE TABLE reference_values (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    vessel_id TEXT NOT NULL REFERENCES vessels(id),
    t REAL NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    source TEXT NOT NULL
);
CREATE INDEX reference_values_run_metric ON reference_values(run_id, metric, vessel_id, t);

CREATE TRIGGER reference_values_no_update BEFORE UPDATE ON reference_values
BEGIN
    SELECT RAISE(ABORT, 'reference values are evidence');
END;
CREATE TRIGGER reference_values_no_delete BEFORE DELETE ON reference_values
BEGIN
    SELECT RAISE(ABORT, 'reference values are evidence');
END;
