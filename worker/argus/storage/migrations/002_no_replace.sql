-- REPLACE deletes the old row without firing delete triggers (unless recursive_triggers is on), so the
-- update and delete guards in 001 could be sidestepped. These guards run before the insert, on any connection.

CREATE TRIGGER measurements_no_replace BEFORE INSERT ON measurements
WHEN EXISTS (SELECT 1 FROM measurements WHERE id = NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'measurements are evidence');
END;

CREATE TRIGGER plans_locked_no_replace BEFORE INSERT ON plans
WHEN EXISTS (
    SELECT 1 FROM plans
    WHERE experiment_id = NEW.experiment_id AND version = NEW.version AND locked_at IS NOT NULL
)
BEGIN
    SELECT RAISE(ABORT, 'locked plan');
END;

CREATE TRIGGER plans_locked_no_delete BEFORE DELETE ON plans WHEN OLD.locked_at IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'locked plan');
END;
