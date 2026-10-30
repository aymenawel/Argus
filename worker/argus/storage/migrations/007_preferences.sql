-- The app's own preferences (D-77), such as where everyday model calls run. Not evidence: a preference may change,
-- and every model call records the model that answered it.

CREATE TABLE preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
