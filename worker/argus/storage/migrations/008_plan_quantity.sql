-- What a plan predicts (D-78): a level (unset), a half-way time or a rate. Unset keeps old plans' hashes.

ALTER TABLE plans ADD COLUMN quantity TEXT;
