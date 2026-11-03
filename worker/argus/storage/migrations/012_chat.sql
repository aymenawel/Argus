-- Ask Argus (D-97): a researcher's question about the moment on screen and Argus's checked answer. Evidence like
-- notes: a new question is a new row, never an edit.

CREATE TABLE chat_messages (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    t REAL NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    body TEXT NOT NULL,
    check_status TEXT NOT NULL CHECK (check_status IN ('passed', 'fallback')),
    model_call_id TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX chat_messages_run_t ON chat_messages(run_id, t);

CREATE TRIGGER chat_messages_no_update BEFORE UPDATE ON chat_messages
BEGIN
    SELECT RAISE(ABORT, 'chat messages are evidence');
END;
CREATE TRIGGER chat_messages_no_delete BEFORE DELETE ON chat_messages
BEGIN
    SELECT RAISE(ABORT, 'chat messages are evidence');
END;
CREATE TRIGGER chat_messages_no_replace BEFORE INSERT ON chat_messages
WHEN EXISTS (SELECT 1 FROM chat_messages WHERE id = NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'chat messages are evidence');
END;
