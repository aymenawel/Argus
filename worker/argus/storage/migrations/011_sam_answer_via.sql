-- Fix 2 (D-93): how each answer found the object. 'name': SAM asked by the concept's name (every answer before this);
-- 'pointed': SAM pointed at what changed since the start, after an empty answer by name; 'code': the change itself
-- outlined by code, after SAM found nothing even pointed. Still evidence: the triggers of 010 hold.
ALTER TABLE sam_answers ADD COLUMN via TEXT NOT NULL DEFAULT 'name' CHECK (via IN ('name', 'pointed', 'code'));
